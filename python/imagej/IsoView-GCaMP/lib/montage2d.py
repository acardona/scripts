from __future__ import with_statement
import os, re

from lib.util import newFixedThreadPool, syncPrintQ, printException, printExceptionCause
from lib.registration import saveMatrices, loadMatrices
from lib.io import loadFilePaths, readFIBSEMHeader, readFIBSEMdat, lazyCachedCellImg
from lib.ui import wrap, addWindowListener
from lib.serial2Dregistration import ensureSIFTFeatures, makeImg

from java.util import ArrayList, Vector, HashSet
from java.lang import Double, Exception, Throwable
from java.util.concurrent import Callable
from java.io import File
from ij.process import ShortProcessor, ByteProcessor
from ij.gui import ShapeRoi, PointRoi, Roi
from ij import ImagePlus
from net.imglib2.img.array import ArrayImgs
try:
  from net.imglib2.algorithm.phasecorrelation import PhaseCorrelation2
except:
  print "MISSING: class PhaseCorrelation2, from the BigStitcher update site."
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.type.numeric.complex import ComplexFloatType
from net.imglib2.type.numeric.integer import UnsignedShortType, UnsignedByteType
from net.imglib2.type import PrimitiveType
from net.imglib2.img.array import ArrayImgFactory
from net.imglib2.img.cell import Cell, CellImg
from net.imglib2.cache import CacheLoader
from net.imglib2.view import Views
from net.imglib2.util import Intervals
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.algorithm.math import ImgMath
from mpicbg.models import ErrorStatistic, TranslationModel2D, TransformMesh, PointMatch, Point, NotEnoughDataPointsException, Tile, TileConfiguration, TileUtil
from mpicbg.ij.clahe import FastFlat as CLAHE
from mpicbg.ij import SIFT # see https://github.com/axtimwalde/mpicbg/blob/master/mpicbg/src/main/java/mpicbg/ij/SIFT.java
from mpicbg.imagefeatures import FloatArray2DSIFT
from mpicbg.imglib.type.numeric.complex import ComplexFloatType

from functools import partial
from collections import defaultdict
from itertools import izip
from jarray import zeros, array



def getFeatures(sp, roi, paramsSIFT, debug=False):
  sp.setRoi(roi)
  sp = sp.crop()
  paramsSIFT = paramsSIFT.clone()
  paramsSIFT.minOctaveSize = min(sp.getWidth(), sp.getHeight())
  paramsSIFT.maxOctaveSize = max(sp.getWidth(), sp.getHeight())
  ijSIFT = SIFT(FloatArray2DSIFT(paramsSIFT))
  features = ArrayList() # of Feature instances
  ijSIFT.extractFeatures(sp, features)
  
  if debug:
    ip = sp.duplicate()
    proi = PointRoi()
    for p in features:
      proi.addPoint(p.location[0], p.location[1])
    imp = ImagePlus("", ip)
    imp.setRoi(proi)
    imp.show()
  
  return features


    
def getPointMatches(sp0, roi0, sp1, roi1, offset,
                    paramsSIFT, paramsRANSAC, params, mode="SIFT"):
  """
  Start off with PhaseCorrelation, fall back to SIFT if needed.
  Or start right away with SIFT when mode="SIFT"
  """
  # Ignoring PhaseCorrelation for now
  if "PhaseCorrelation" == mode:
    sp0.setRoi(roi0)
    spA = sp0.crop()
    sp1.setRoi(roi1)
    spB = sp1.crop()
    spA_img = ArrayImgs.unsignedShorts(spA.getPixels(), spA.getWidth(), spA.getHeight())
    spB_img = ArrayImgs.unsignedShorts(spB.getPixels(), spB.getWidth(), spB.getHeight())
    # Thread pool
    exe = newFixedThreadPool(n_threads=1, name="phase-correlation")
    try:
      # PCM: phase correlation matrix
      pcm = PhaseCorrelation2.calculatePCM(spA_img,
                                           spB_img,
                                           ArrayImgFactory(FloatType()),
                                           FloatType(),
                                           ArrayImgFactory(ComplexFloatType()),
                                           ComplexFloatType(),
                                           exe)
      # Number of phase correlation peaks to check with cross-correlation
      nHighestPeaks = 10
      # Minimum image overlap to consider, in pixels
      minOverlap = min(spA.getWidth(), spA.getHeight()) / 3
      # Returns an instance of PhaseCorrelationPeak2
      peak = PhaseCorrelation2.getShift(pcm, spA_img, spB_img, nHighestPeaks,
                                        minOverlap, True, True, exe)
      # Construct a single PointMatch using the computed best x,y shift
      shift = peak.getSubpixelShift()  
      dx = shift.getFloatPosition(0)
      dy = shift.getFloatPosition(1)
      if 0.0 == dx and 0.0 == dy:
        # The shift can't be zero
        # Fall back to SIFT
        syncPrintQ("shift is zero, fall back to SIFT")
        mode = "SIFT"
      else:
        pointmatches = ArrayList()
        pointmatches.add(PointMatch(Point([0.0, 0.0]), Point([dx, dy])))
    except Exception, e:
      # No peaks found
      syncPrintQ("No peaks found, fallback to SIFT")
      printException()
      mode = "SIFT"
    finally:
      exe.shutdown()

  model = TranslationModel2D() # suffices locally
  
  if "SIFT" == mode:
    syncPrintQ("PointMatches by SIFT")
    features0 = getFeatures(sp0, roi0, paramsSIFT)
    features1 = getFeatures(sp1, roi1, paramsSIFT)
    pointmatches = FloatArray2DSIFT.createMatches(features0,
                                                  features1,
                                                  params.get("max_sd", 1.5), # max_sd: maximal difference in size (ratio max/min)
                                                  model,
                                                  params.get("max_id", Double.MAX_VALUE), # max_id: maximal distance in image space
                                                  params.get("rod", 0.9)) # rod: ratio of best vs second best
  if 0 == pointmatches.size():
    return pointmatches

  # Filter matches by geometric consensus
  inliers = ArrayList()
  iterations = paramsRANSAC.get("iterations", 1000)
  maxEpsilon = paramsRANSAC.get("maxEpsilon", 25) # pixels
  minInlierRatio = paramsRANSAC.get("minInlierRatio", 0.01) # 1%
  modelFound = model.filterRansac(pointmatches, inliers, iterations, maxEpsilon, minInlierRatio)
  if modelFound:
    syncPrintQ("Found model with %i inliers" % inliers.size())
    pointmatches = inliers
  else:
    syncPrintQ("model NOT FOUND")
    return ArrayList() # empty
  
  # Correct pointmatches position: roi0 is on the right or the bottom of the image
  bounds = roi0.getBounds()
  x0 = bounds.x
  y0 = bounds.y
  for pm in pointmatches:
    # Correct points on left image for ROI being on its right margin
    p1 = pm.getP1()
    l1 = p1.getL()
    l1[0] += x0
    l1[1] += y0
    #w1 = p1.getW()
    #w1[0] += x0
    #w1[1] += y0
    # Correcting for the ~60 to ~100 px on the left margin that are non-linearly deformed
    p2 = pm.getP2()
    l2 = p2.getL()
    l2[0] += offset
    #w2 = p2.getW()
    #w2[0] += offset
  #
  return pointmatches


def loadShortProcessors(tilePaths, asDict=False):
  for filepath in tilePaths:
    syncPrintQ("#%s#" % filepath)
  # Load images
  if asDict:
    return {filepath: readFIBSEMdat(filepath, channel_index=0, asImagePlus=True)[0].getProcessor()
            for filepath in tilePaths}
  return [readFIBSEMdat(filepath, channel_index=0, asImagePlus=True)[0].getProcessor() for filepath in tilePaths]
  
def yieldShortProcessors(tilePaths, reverse=False):
  ls = tilePaths if not reverse else reversed(tilePaths)
  for filepath in ls:
    syncPrintQ("#%s#" % filepath)
    yield readFIBSEMdat(filepath, channel_index=0, asImagePlus=True)[0].getProcessor()


def processTo8bit(sp, params_pixels):
  """ WARNING will alter sp.
  
  sp: the ShortProcessor to process.
  params_pixels is a dictionary with:
    invert: whether to invert the image.
    CLAHE_params: defaults to None, otherwise a list of 3 values: the blockRadius, the number of histogram bins, and the slope. Sensible values are 200, 255, 2.0.
    contrast: a pair of values defining the thresholds in pixel counts for finding the minimum and the maximum.
    roi: None, or a function to create a rectangular ROI from an ImageProcessor argument to use for finding the minimum and the maximum.
  """
  # Find min and max of the image yet to be inverted
  sp.findMinAndMax()
  maximum = sp.getMax() # even though this is really the min, 16-bit images get inverted within their display range
                        # so after .invert() this will be the max.
                        # If it was done after .invert(), the black border would be 65535 and that max is the wrong one.
  # First invert
  if params_pixels["invert"]:
    sp.invert()
  # Second determine and set display range
  # Find first histogram bin that has a count higher than 500
  roiFn = params_pixels.get("roiFn", None)
  if roiFn:
    sp.setRoi(roiFn(sp))
  h = sp.getHistogram() # of the whole image or of the ROI only if present
  if roiFn:
    sp.resetRoi() # cleanup
    
  minimum = 0
  left_count, right_count = params_pixels.get("contrast", (500, 1000))
  for i, count in enumerate(h):
    if 0 == i:
      continue # ignore zero
    if count > left_count:
      minimum = i
      break
  for i in xrange(maximum -1, 0, -1): # ignore max so "maximum -1" is the first index to consider
    if h[i] > right_count:
      maximum = i
      break
  #print minimum, maximum
  # CLAHE runs within the min-max range, so set it first
  sp.setMinAndMax(minimum, maximum)
  # Third run CLAHE (runs equally well on 16-bit as on 8-bit, within +1/-1 difference in pixel values)
  # But running it before the mapping to 8-bit eases a lot the conversion to 8-bit because it spreads the histogram
  if params_pixels.get("CLAHE_params", None):
    blockRadius, n_bins, slope = params_pixels["CLAHE_params"]
    CLAHE.run(ImagePlus("", sp), blockRadius, n_bins, slope, None)
  # Fourth convert to 8-bit
  bp = sp.convertToByte(True) # sets the display range into stone
  sp = None
  return bp



def process(sp, params_pixels):
  if params_pixels("invert"):
    sp.invert()
  if params_pixels("CLAHE_params"):
    blockRadius, n_bins, slope = params_pixels("CLAHE_params")
    CLAHE.run(ImagePlus("", sp), blockRadius, n_bins, slope, None)
  return sp



class MontageSlice(Callable):
  def __init__(self, groupName, tilePaths, overlap, nominal_overlap, offset, paramsSIFT, paramsRANSAC, paramsTileConfiguration, csvDir, failed):
    """
    Generic montager, reads out i,j position from the file name.
    """
    # EXPECTS filepaths with filenames ending in ["_0-0-0.dat", "_0-0-1.dat", "_0-1-0.dat", "_0-1-1.dat" ... ], where the last number indicates the column, and the second-to-last the row.
    # ASSUMES all tiles have the same dimensions
    self.groupName = groupName
    self.tilePaths = list(sorted(tilePaths))
    self.overlap = overlap
    self.nominal_overlap = nominal_overlap
    self.offset = offset
    self.paramsSIFT = paramsSIFT
    self.paramsRANSAC = paramsRANSAC
    self.csvDir = csvDir
    self.failed = failed
    self.params = {"max_sd": 1.5, # max_sd: maximal difference in size (ratio max/min)
                   "max_id": Double.MAX_VALUE, # max_id: maximal distance in image space
                   "rod": 0.9} # rod: ratio of best vs second best
    self.paramsTileConfiguration = paramsTileConfiguration

    # Determine rows and columns
    self.rows = defaultdict(partial(defaultdict, str))
    pattern = re.compile("^\d+-(\d+)-(\d+)\.dat$")
    for filepath in self.tilePaths:
      # Parse i, j coordinates from the e.g., ".*_0-0-0.dat" filename
      i_row, i_col = map(int, re.match(pattern, filepath[filepath.rfind('_')+1:]).groups())
      self.rows[i_row][i_col] = filepath


  def connectTiles(self, filepath1, filepath2, sps, tiles, roi0, roi1, offset):
    pointmatches = getPointMatches(sps[filepath1], roi0, sps[filepath2], roi1, offset,
                                   self.paramsSIFT, self.paramsRANSAC, self.params)
    if pointmatches.size() > 0:
      tiles[filepath1].connect(tiles[filepath2], pointmatches) # reciprocal connection
      return True
    # Else
    syncPrintQ("No pointmatches found for %s vs %s of section %s" % (filepath1, filepath2, self.groupName))
    return False


  def getMatrices(self):
    # Extract features from the appropriate ROI along the overlapping edges
    
    # Check if matrices exist already:
    matrices = loadMatrices(self.groupName, self.csvDir)
    if matrices is not None:
      return matrices

    # Predefine the tiles
    tc = TileConfiguration()
    tiles = {filepath: Tile(TranslationModel2D()) for filepath in self.tilePaths}
    tc.addTiles(tiles.values())

    # Fix top-left tile at 0,0 position
    tc.fixTile(tiles[self.rows[0][0]])

    sps = loadShortProcessors(self.tilePaths, asDict=True)

    # Assumes images have the same dimensions
    width = sps[self.tilePaths[0]].getWidth()
    height = sps[self.tilePaths[0]].getHeight()

    # Define 4 ROIs: (x, y, width, height)
    # left-right
    roiEast = Roi(width - self.overlap, 0, self.overlap, height) # right edge, for tile 0-0-0  (and 0-1-0)
    roiWest = Roi(self.offset, 0, self.overlap, height)          # left edge,  for tile 0-0-1  (and 0-1-1)
    # top-bottom
    roiSouth = Roi(0, height - self.overlap, width, self.overlap) # bottom edge, for tile 0-0-0  (and 0-0-1)
    roiNorth = Roi(0, 0, width, self.overlap)                     # top edge,    for tile 0-1-0  (and 0-1-1)

    # Link the tiles by image registration
    booleans = []
    for i, row in self.rows.items():
      for j, filepath2 in row.items():
        # Link each tile with the tile on its left and on top, if any
        if i > 0:
          # Link with tile above
          filepath1 = self.rows[i-1][j]
          if not filepath1: # an empty string
            continue # tile is missing from the montage
          booleans.append(self.connectTiles(filepath1, filepath2, sps, tiles, roiSouth, roiNorth, 0))
        if j > 0:
          # Link with tile to the left
          filepath1 = self.rows[i][j-1]
          if not filepath1: # an empty string
            continue # tile is missing from the montage
          booleans.append(self.connectTiles(filepath1, filepath2, sps, tiles, roiEast, roiWest, self.offset))

    if not any(booleans):
      syncPrintQ("All tiles failed to connect for section %s " % (self.groupName))
      self.failed.add(self.groupName)
      return self.defaultPositions(width, height)

    try:
      # Optimise tile positions
      maxAllowedError = self.paramsTileConfiguration["maxAllowedError"]
      maxPlateauwidth = self.paramsTileConfiguration["maxPlateauwidth"]
      maxIterations   = self.paramsTileConfiguration["maxIterations"]
      damp            = self.paramsTileConfiguration["damp"]
      nThreads        = self.paramsTileConfiguration.get("nThreadsOptimizer", 1)
      #tc.optimize(ErrorStatistic(maxPlateauwidth + 1), maxAllowedError, maxIterations, maxPlateauwidth, damp)
      TileUtil.optimizeConcurrently(ErrorStatistic(maxPlateauwidth + 1), maxAllowedError, maxIterations, maxPlateauwidth, damp, tc, HashSet(tiles.values()), tc.getFixedTiles(), nThreads)
    
      # Save transformation matrices
      matrices = []
      for filepath in self.tilePaths:
        tile = tiles[filepath]
        a = zeros(6, 'd')
        tile.getModel().toArray(a)
        matrices.append(array([a[0], a[2], a[4], a[1], a[3], a[5]], 'd'))
      saveMatrices(self.groupName, matrices, self.csvDir)
      return matrices
    #except NotEnoughDataPointsException as e: # Never catches it because jython wraps exceptions
    #  syncPrintQ("Failed to find a model for %s: NotEnoughDataPointsException" % (self.groupName, str(e)))
    except Throwable as t:
      printExceptionCause(e=t,
                          printFn=syncPrintQ,
                          msg="Failed to find a model for %s"  % self.groupName,
                          trace=False)

    # Else: either some tiles failed to connect or there was a NotEnoughDataPointsException
    self.failed.add(self.groupName)
    return self.defaultPositions(width, height)

  def defaultPositions(self, width, height):
    # TODO: either montage them manually, or try to montage by using cross-section correspondances.
    # Return the expected tile positions given the nominal_overlap
    matrices = []
    for j, row in self.rows.items():
      for i, filepath2 in row.items():
        matrices.append(array([1.0, 0.0, i * (width - self.nominal_overlap),
                               0.0, 1.0, j * (height - self.nominal_overlap)], 'd'))
    saveMatrices(self.groupName, matrices, self.csvDir)
    return matrices


  def call(self):
    return self.getMatrices()

  def montagedImg(self, width, height, section_matrix, params_pixels, sdx=0, sdy=0):
    """ Return an ArrayImg representing the montage
        width, height: dimensions of the canvas onto which to insert the tiles.
        section_matrix: if there is a transform to apply section-wide, to the whole montage.
                        Here, only the translation is applied, ultimately as integers.
    """
    matrices = self.getMatrices()
    dx, dy = (section_matrix[2], section_matrix[5]) if section_matrix else (0, 0)
    spMontage = ShortProcessor(width, height)
    # Start pasting from the end, to bury the bad left edges
    for sp, matrix in izip(yieldShortProcessors(self.tilePaths, reverse=True), reversed(matrices)):
      spMontage.insert(process(sp, params_pixels),  # TODO don't process separately, see above
                       int(sdx + matrix[2] + dx + 0.5),
                       int(sdy + matrix[5] + dy + 0.5)) # indices 2 and 5 are the X, Y translation
    
    return ArrayImgs.unsignedShorts(spMontage.getPixels(), width, height)



  def montagedImg8bit(self, width, height, section_matrix, params_pixels, sdx=0, sdy=0):
    """ Return an ArrayImg representing the montage
        width, height: dimensions of the canvas onto which to insert the tiles.
        section_matrix: if there is a transform to apply section-wide, to the whole montage.
                        Here, only the translation is applied, ultimately as integers.
    """
    matrices = self.getMatrices()
    dx, dy = (section_matrix[2], section_matrix[5]) if section_matrix else (0, 0)
    spMontage = ShortProcessor(width, height)
    rois = []
    # Start pasting from the end, to bury the bad left edges
    for sp, matrix in izip(yieldShortProcessors(self.tilePaths, reverse=True), reversed(matrices)):
      x = int(sdx + matrix[2] + dx + 0.5) # indices 2 and 5 are the X, Y translation
      y = int(sdy + matrix[5] + dy + 0.5)
      spMontage.insert(sp, x, y)
      rois.append(Roi(x, y, sp.getWidth(), sp.getHeight()))
    sps = None
    bpMontage = processTo8bit(spMontage, params_pixels)
    spMontage = None
    if params_pixels["invert"]:
      # paint white background as black
      # (Can't invert earlier as the min, max wouldn't match, leading to uneven illumination across tiles)
      sp = ShapeRoi(rois[0])
      for roi in rois[1:]:
        sp = sp.or(ShapeRoi(roi))
      bpMontage.setValue(0) # black
      bpMontage.fill(sp.getInverse(ImagePlus("", bpMontage))) # fill the inverse of the tiles areas
    
    return ArrayImgs.unsignedBytes(bpMontage.getPixels(), width, height)



class SectionLoader(CacheLoader):
  """
  A CacheLoader where each cell is a section made from loading and transforming multiple tiles or just one tile
  """
  def __init__(self, dimensions, groupNames, tileGroups, overlap, nominal_overlap, offset,
               paramsSIFT, paramsRANSAC, paramsTileConfiguration, csvDir, params_pixels,
               section_offsets=None, # A function that given an index returns a tuple of two integers
               matrices=None):
    """
    csvDir: the directory specifying the montages, one matrices file per section.
    """
    self.dimensions = dimensions # a list of [width, height] for the canvas onto which draw the image tiles
    self.groupNames = groupNames # list of names of each group, used to find its montage CSV if any
    self.tileGroups = tileGroups # a list of lists of file paths to .dat files, one per section
    self.overlap = overlap
    self.nominal_overlap = nominal_overlap
    self.offset = offset
    self.paramsSIFT = paramsSIFT
    self.paramsRANSAC = paramsRANSAC
    self.paramsTileConfiguration = paramsTileConfiguration
    self.csvDir = csvDir
    self.params_pixels = params_pixels
    self.section_offsets = section_offsets
    self.matrices = matrices # for alignment in Z
    if self.matrices and len(self.groupNames) != len(self.matrices):
      raise Exception("Lengths of groupNames and rows in the matrices file don't match!")
  
  def get(self, index):
    groupName = self.groupNames[index]
    tilePaths = self.tileGroups[index]
    matrix = self.matrices[index] if self.matrices else None
    sdx, sdy = self.section_offsets(index) if self.section_offsets else (0, 0)
    as8bit = self.params_pixels["as8bit"]
    #
    if len(tilePaths) > 1:
      m = MontageSlice(groupName, tilePaths, self.overlap, self.nominal_overlap, self.offset,
                       self.paramsSIFT, self.paramsRANSAC, self.paramsTileConfiguration,
                       self.csvDir, Vector())
      if as8bit:
        aimg = m.montagedImg8bit(self.dimensions[0], self.dimensions[1],
                                 matrix, self.params_pixels,
                                 sdx=sdx, sdy=sdy)
      else:
        aimg = m.montagedImg(self.dimensions[0], self.dimensions[1],
                             matrix, self.params_pixels,
                             sdx=sdx, sdy=sdy)
    elif 1 == len(tilePaths):
      imp = readFIBSEMdat(tilePaths[0], channel_index=0, asImagePlus=True)[0]
      if as8bit:
        ipTile = processTo8bit(imp.getProcessor(), self.params_pixels)
        ip = ByteProcessor(self.dimensions[0], self.dimensions[1])
      else:
        ipTile = process(imp.getProcessor(), self.params_pixels)
        ip = ShortProcessor(self.dimensions[0], self.dimensions[1])
      dx, dy = (matrix[2], matrix[5]) if matrix else (0, 0)
      ip.insert(ipTile,
                int(sdx + dx + 0.5),
                int(sdy + dy + 0.5))
      fn = ArrayImgs.unsignedBytes if as8bit else ArrayImgs.unsignedShorts
      aimg = fn(ip.getPixels(), self.dimensions)
      imp.flush()
      imp = None
      ip = None
    else:
      # return empty Cell
      syncPrintQ("WARNING: number of tiles isn't 4 or 1")
      fn = ArrayImgs.unsignedBytes if as8bit else ArrayImgs.unsignedShorts
      aimg = fn(self.dimensions) # TODO this should be a constant DataAccess

    return Cell(self.dimensions + [1], # cell dimensions
                [0, 0, index], # position in the grid: 0, 0, 0, Z-index
                aimg.update(None)) # get the underlying DataAccess


def ensureMontages(groupNames, tileGroups, overlap, nominal_overlap, offset, paramsSIFT, paramsRANSAC, paramsTileConfiguration, csvDir, nThreads):
  """
  Extract features and a matrix describing a TranslationModel2D for all tiles that need montaging.
  The overlap between tiles is defined by overlap.
  The offset is for ignoring that many pixels from the left edge, which are artifactually
  non-linearly compressed and stretched in FIBSEM images. 
  
  groupNames: a list of names, with the common part of the filename of all tiles in a section.
  tileGroups: a list of lists of tile filenames.
          In other words, these two lists are correlated, and each entry represents a section with 1 or 4 image tiles in it.
  overlap: the amount of pixels of overlap between two tiles.
  offset: the amount of pixels to ignore from the left edge of an image tile.
  paramsSIFT: for montaging using scale invariant feature transform (SIFT).
  csvDir: where to save the matrix CSV files, one per montage and section.
  """
  exe = newFixedThreadPool(nThreads)
  try:

    futures = []
    failed = Vector() # synchronized access

    # Iterate all sections in order and generate the transformation matrices defining a montage for each section
    for groupName, tilePaths in izip(groupNames, tileGroups):
      if len(tilePaths) > 1:
        # Montage the tiles: compute a matrix detailing a TranslationModel2D for each tile
        futures.append(exe.submit(MontageSlice(groupName, tilePaths, overlap, nominal_overlap, offset, paramsSIFT, paramsRANSAC, paramsTileConfiguration, csvDir, failed)))

    # Await them all
    for future in futures:
      future.get()

    # Print failed montages
    syncPrintQ("Montages that failed:\n%s" % "\n".join(map(str, failed)))

  finally:
    exe.shutdown()




def makeMontageGroups(filepaths, to_remove, check, alternative_dir=None, ignore_images=set(), writeDir=None):
  """
  Does not assume anything regarding the number of tiles per montage.
  
  Parameters:
  filepaths: list of all file paths to all image tiles
  to_remove: a set of sections to ignore because they have data inconsistency problems like missing tiles or truncated tiles
  check: whether to check the header and file sizes for issues.
  alternative_dir: if a file fails to open, try to find it in this directory.
  ignore_images: a set of image filenames to ignore and leave out of the montages.
  
  Returns groupNames, tileGroups
  """
  # Group files by section, as there could be multiple image tiles per section
  groups = defaultdict(list)
  for filepath in filepaths:
    path, filename = os.path.split(filepath)
    # filepath looks like: /home/albert/zstore1/FIBSEM/Pedro_parker/M07/D13/Merlin-FIBdeSEMAna_23-07-13_083741_0-0-0.dat
    sectionName = filename[0:-9]
    groups[sectionName].append(filepath)

  # Find files under alternative_dir
  alternative_filenames = set()
  if alternative_dir:
    alt = File(alternative_dir)
    if alt.exists() and alt.isDirectory():
      alternative_filenames = set(alt.list()) # all filenames
  for af in alternative_filenames:
      syncPrintQ("Available alternative: %s" % af)

  # Ensure tilePaths are sorted,
  # and check that tiles are of the same dimensions and file size within each section:
  for groupName_, tilePaths_ in groups.iteritems():
    tilePaths_.sort() # in place

    # Replace and remove filepaths as needed
    if alternative_dir or len(ignore_images) > 0:
      drop = []
      for i, tilePath in enumerate(tilePaths_):
        filename = os.path.basename(tilePath)
        # Check if tilePath is to be ignored and remove it from the group
        if filename in ignore_images:
          drop.append(i)
        # Check if tilePath has to be replaced
        if filename in alternative_filenames:
          tilePaths_[i] = os.path.join(alternative_dir, filename)
          syncPrintQ("Replaced filepath for %s :\n%s\n" % (filename, tilePaths_[i]))
      # Remove from group any tilePath to ignore
      for i in drop:
        syncPrintQ("Will ignore image %s" % tilePaths_[i])
        del tilePaths_[i]
      # If no tiles left, remove section
      if 0 == len(tilePaths_):
        to_remove.add(groupName_)

    if not check:
      continue

    # Check that all tiles have the same dimensions and the same file size
    widths = []
    heights = []
    fileSizes = []
    drop = set()
    for i, tilePath in enumerate(tilePaths_):
      try:
        header = readFIBSEMHeader(tilePath)
        if header is None:
            drop.add(i)
            syncPrintQ("%s HEADER: %s" % (groupName_, str(type(header))))
        else:
          widths.append(header.xRes)
          heights.append(header.yRes)
          fileSizes.append(os.stat(tilePath).st_size)
          #syncPrintQ("tilePath: %s\ndimensions: %i, %i" % (tilePath, header.xRes, header.yRes))
      except:
        syncPrintQ("Failed to read header or file size for:\n" + tilePath, copy_to_stdout=True)
        drop.add(i)
      if 1 == len(set(widths)) and 1 == len(set(heights)) and 1 == len(set(fileSizes)):
        # all tiles are the same
        pass
      else:
        to_remove.add(groupName_)
        syncPrintQ("Inconsistent tile dimensions of file sizes in section:\n%s\n%s" %(groupName_, "\n".join(map(str, izip(widths, heights)))), copy_to_stdout=True)

    # If all tiles were removed, then:
    if len(drop) == len(tilePaths_):
      to_remove.add(groupName_)

  for groupName_ in to_remove:
    del groups[groupName_]
    syncPrintQ("Will ignore section: " + groupName_, copy_to_stdout=True)
  
  syncPrintQ("Invalid sections: %i" % len(to_remove))

  # Sort groups by key
  keys = groups.keys()
  keys.sort()
  groupNames = []
  tileGroups = []
  for groupName in keys:
    groupNames.append(groupName)
    tileGroups.append(groups[groupName])

  if writeDir:
    path = os.path.join(writeDir, "groupNames")
    if not os.path.exists(path):
      with open(path, 'w') as fh:
        fh.write("\n".join("%s = [%s]" % (groupName, ", ".join(groups[groupName])) for groupName in groupNames))

  return groupNames, tileGroups



# Define a virtual CellImg expressing all the montages, one per section
def makeVolume(groupNames, tileGroups, section_width, section_height, overlap, nominal_overlap, offset,
               paramsSIFT, paramsRANSAC, paramsTileConfiguration, csvDir, params_pixels,
               show=True, matrices=None, section_offsets=None, title=None, cache_size=64):
  dimensions = [section_width, section_height]
  volume_dimensions = dimensions + [len(groupNames)]
  cell_dimensions = dimensions + [1]
  pixelType = UnsignedByteType # UnsignedShortType
  primitiveType = PrimitiveType.BYTE #.SHORT
  
  volumeImg = lazyCachedCellImg(SectionLoader(dimensions, groupNames, tileGroups, overlap, nominal_overlap, offset,
                                              paramsSIFT, paramsRANSAC, paramsTileConfiguration, csvDir, params_pixels,
                                              matrices=matrices,
                                              section_offsets=section_offsets),
                                volume_dimensions,
                                cell_dimensions,
                                pixelType,
                                primitiveType,
                                maxRefs=cache_size)  # number of threads times number of sections to compare against plus some padding

  # Show the montages as a series of slices in a stack
  if show:
    imp = wrap(volumeImg)
    if title:
      imp.setTitle(title)
    imp.show()
    # Label each slice with the groupName
    stack = imp.getStack()
    for i, groupName in enumerate(groupNames):
      #syncPrintQ("%i: %s" % (i, groupName))
      stack.setSliceLabel(groupName, i+1) # 1-based
  
  return volumeImg


def makeSliceLoader(groupNames, volumeImg):
  """
    groupNames: a list of lists, each defining a section with one or more tiles
    volumeImg: a CellImg
  """
  # Will use groupNames as filepaths, and a load function that will return hyperslices of volumeImg
  indices = {groupName: i for i, groupName in enumerate(groupNames)}

  def sliceLoader(volumeImg, indices, groupName):
    # Works, but copies it over
    #img2d = Views.hyperSlice(volumeImg, 2, indices[groupName])
    #aimg = ArrayImgs.unsignedShorts(Intervals.dimensionsAsLongArray(img2d))
    #ImgMath.compute(ImgMath.img(img2d)).into(aimg)
    #imp = ImagePlus(groupName, ShortProcessor(aimg.dimension(0), aimg.dimension(1), aimg.update(None).getCurrentStorageArray(), None))
    # Process for BlockMatching and SIFT across sections
    #imp.getProcessor().invert()
    #CLAHE.run(imp, 200, 256, 3.0, None)
    # Instead:
    # Each slice is already an ArrayImg: get the DataAccess of the Cell at index, which is a 2D image
    # ... and it's already processed for invert and CLAHE, and cached.
    cell = volumeImg.getCells().randomAccess().setPositionAndGet([0, 0, indices[groupName]])
    pixels = cell.getData().getCurrentStorageArray()
    return ImagePlus(groupName, ByteProcessor(volumeImg.dimension(0), volumeImg.dimension(1), pixels, None))
  
  # Return a 1-argument function that takes the groupName as its sole argument
  return partial(sliceLoader, volumeImg, indices)


def fuseMatrices(matricesSIFT, matricesBM):
  # fuse the matrices: concatenate the translation transforms
  # WARNING the SIFT+RANSAC registration will have been expressed as integers, which is what the blockmatching saw, so correct for that
  matrices = []
  for m1, m2 in izip(matricesSIFT, matricesBM):
    # The SIFT alignment will have been expressed as integers, so correct for that
    matrices.append(array([1, 0, int(m1[2] + 0.5) + m2[2], 0, 1, int(m1[5] + 0.5) + m2[5]], 'd'))

def fuseTranslationMatrices(matrices1, matrices2):
  return [array([1, 0, m1[2] + m2[2],
                 0, 1, m1[5] + m2[5]], 'd')
          for m1, m2 in izip(matrices1, matrices2)]


def showAlignedImg(img, cropInterval, groupNames, properties, matrices, rotate=None, title_addendum=""):
  """
  rotate: "right" or "left" or "180" or None
  """
  # Show the volume using ImgLib2 interpretation of matrices, with subpixel alignment
  def loadImg(img, index):
    if isinstance(img, CellImg):
      cell = img.getCells().randomAccess().setPositionAndGet([0, 0, index])
      pixels = cell.getData().getCurrentStorageArray()
      return ArrayImgs.unsignedBytes(pixels, [img.dimension(0), img.dimension(1)])
    else:
      img2d = Views.hyperSlice(img, 2, index)
      aimg = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(img2d))
      ImgMath.compute(ImgMath.img(img2d)).into(aimg)
      return aimg
      
  
  cellImg, cellGet = makeImg(range(len(groupNames)), properties["pixelType"],
                             partial(loadImg, img), properties["img_dimensions"],
                             matrices, cropInterval, properties.get('preload', 0))


  if "right" == rotate or "left" == rotate:
    # By 90 or -90 degrees
    a, b = (0, 1) if "right" == rotate else (1, 0) # left
    img = Views.rotate(cellImg, a, b) # the 0 and 1 are the two axis (dimensions) of reference, e.g., pux X (the 0) into Y (the 1).
  elif "180" == rotate:
    # Rotate twice to the right
    img = Views.rotate(Views.rotate(cellImg, 0, 1), 0, 1)
  else:
    img = cellImg

  imp = IL.wrap(img, properties.get("name", "") + " aligned subpixel" + title_addendum)
  imp.show()
  # Ensure cleanup of threads upon closing the window
  addWindowListener(imp.getWindow(), lambda event: cellGet.destroy())
  
  return img, imp
  
