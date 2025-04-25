from __future__ import with_statement
import os, re, sys
from datetime import datetime

from lib.util import newFixedThreadPool, syncPrintQ, printException, printExceptionCause, numCPUs, Task, ParallelTasks
from lib.registration import saveMatrices, loadMatrices
from lib.io import loadFilePaths, readFIBSEMHeader, readFIBSEMdat, readFIBSEM, imageInfo, ensureDirsExist, SectionCellLoader
from lib.img import lazyCachedCellImg
from lib.ui import wrap, wrap8bit
from lib.loop import createBiConsumerTypeSet
from lib.montage2d_table import makeMontageTable

from java.util import ArrayList, Vector, HashSet
from java.lang import Double, Exception, Throwable
from java.util.concurrent import Callable
from java.io import File
from ij.process import ShortProcessor, ByteProcessor
from ij.gui import ShapeRoi, PointRoi, Roi, GenericDialog
from ij.io import OpenDialog, FileSaver
from ij import ImagePlus, IJ
from net.imglib2.img.array import ArrayImgs
try:
  from net.imglib2.algorithm.phasecorrelation import PhaseCorrelation2
except:
  print "MISSING: class PhaseCorrelation2, from the BigStitcher update site."
from net.imglib2.type import Type
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.type.numeric.complex import ComplexFloatType
from net.imglib2.type.numeric.integer import UnsignedShortType, UnsignedByteType, GenericByteType
from net.imglib2.type import PrimitiveType
from net.imglib2.img.array import ArrayImgFactory
from net.imglib2.img.cell import Cell, CellImg
from net.imglib2.cache import CacheLoader
from net.imglib2.view import Views
from net.imglib2.util import Intervals
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.algorithm.math import ImgMath
from net.imglib2.loops import LoopBuilder
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
  paramsSIFT.minOctaveSize = min(sp.getWidth(), sp.getHeight()) if 0 == paramsSIFT.minOctaveSize else paramsSIFT.minOctaveSize
  paramsSIFT.maxOctaveSize = max(sp.getWidth(), sp.getHeight()) if 0 == paramsSIFT.maxOctaveSize else paramsSIFT.maxOctaveSize
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
    return pointmatches, 0

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
    return ArrayList(), 0 # empty
  
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
  return pointmatches, len(inliers)

# Load images
def load(filepath, params_pixels):
  """ Return an ImagePlus """
  if filepath.endswith(".dat"):
    asFloatFn = params_pixels.get("loadAsFloatFn", None)
    if asFloatFn and asFloatFn(filepath):
      # Slower but can open with floats
      return readFIBSEM(filepath, openAsFloat=True, channel_index=0)
    else:
      return readFIBSEMdat(filepath, channel_index=0, asImagePlus=True)[0]
  return IJ.openImage(filepath)

def loadShortProcessors(tilePaths, params_pixels, asDict=False):
  for filepath in tilePaths:
    syncPrintQ("#%s#" % filepath)
  if asDict:
    return {filepath: load(filepath, params_pixels).getProcessor()
            for filepath in tilePaths}
  return [load(filepath, params_pixels).getProcessor()
          for filepath in tilePaths]


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
  if params_pixels["invert"]:
    sp.invert()
  if params_pixels["CLAHE_params"]:
    blockRadius, n_bins, slope = params_pixels["CLAHE_params"]
    CLAHE.run(ImagePlus("", sp), blockRadius, n_bins, slope, None)
  return sp



class MontageSlice(Callable):
  def __init__(self, groupName, tilePaths, overlap, nominal_overlap, offset,
               paramsSIFT, paramsRANSAC, paramsTileConfiguration, params_pixels,
               csvDir, failed):
    """
    Generic montager, reads out i,j position from the file name.
    """
    # EXPECTS filepaths with filenames ending in ["_0-0-0.dat", "_0-0-1.dat", "_0-1-0.dat", "_0-1-1.dat" ... ], where the last number indicates the column, and the second-to-last the row.
    # ASSUMES all tiles have the same dimensions
    self.groupName = groupName
    
    # Sort tilePaths by using their basenames only, since files in the repaired directory would sort differently
    paths = {os.path.basename(p)[:p.rfind(".")]: p for p in tilePaths} # keys are base file names without extension or folders
    self.tilePaths = [paths[p] for p in sorted(paths.keys())]
    
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
    self.params_pixels = params_pixels

    # Determine rows and columns
    self.rows = defaultdict(partial(defaultdict, str))
    pattern = re.compile("^\d+-(\d+)-(\d+)\..*$") # any extension
    for filepath in self.tilePaths:
      # Parse i, j coordinates from the e.g., ".*_0-0-0.dat" filename
      i_row, i_col = map(int, re.match(pattern, filepath[filepath.rfind('_')+1:]).groups())
      self.rows[i_row][i_col] = filepath


  def connectTiles(self, filepath1, filepath2, sps, tiles, roi0, roi1, offset):
    pointmatches, n_inliers = getPointMatches(sps[filepath1], roi0, sps[filepath2], roi1, offset,
                                              self.paramsSIFT, self.paramsRANSAC, self.params)
    if pointmatches.size() > 0:
      tiles[filepath1].connect(tiles[filepath2], pointmatches) # reciprocal connection
      return len(pointmatches), n_inliers
    # Else
    syncPrintQ("No pointmatches found for %s vs %s of section %s" % (filepath1, filepath2, self.groupName))
    return len(pointmatches), n_inliers


  def getMatrices(self, sps=None):
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

    sps = dict(zip(self.tilePaths, sps)) if sps is not None else loadShortProcessors(self.tilePaths, self.params_pixels, asDict=True)

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
    pairs = []
    for i, row in self.rows.items():
      for j, filepath2 in row.items():
        # Link each tile with the tile on its left and on top, if any
        if i > 0:
          # Link with tile above
          filepath1 = self.rows[i-1][j]
          if not filepath1: # an empty string
            continue # tile is missing from the montage
          n_pointmatches, n_inliers = self.connectTiles(filepath1, filepath2, sps, tiles, roiSouth, roiNorth, 0)
          booleans.append(n_pointmaches > 0)
          pairs.append([("%i-%i vs %i-%i" % (i-1, j, i, j)), n_pointmatches, n_inliers])
        if j > 0:
          # Link with tile to the left
          filepath1 = self.rows[i][j-1]
          if not filepath1: # an empty string
            continue # tile is missing from the montage
          n_pointmatches, n_inliers = self.connectTiles(filepath1, filepath2, sps, tiles, roiEast, roiWest, self.offset)
          booleans.append(n_pointmatches > 0)
          pairs.append([("%i-%i vs %i-%i" % (i, j-1, i, j)), n_pointmatches, n_inliers])

    # Record the number of pointmatches and of inliers for each pair of tiles
    with open(os.path.join(self.csvDir, self.groupName + ".montage_stats.csv"), 'w') as f:
      f.write("tile_pair, n_pointmatches, n_inliers\n")
      for pair in pairs:
        f.write(", ".join(str(v) for v in pair))
        f.write("\n")
      # Ensure it's written
      f.flush()
      os.fsync(f.fileno())

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

  def montagedImg(self, width, height, section_matrix, sdx=0, sdy=0):
    """ Return an ArrayImg representing the montage
        width, height: dimensions of the canvas onto which to insert the tiles.
        section_matrix: if there is a transform to apply section-wide, to the whole montage.
                        Here, only the translation is applied, ultimately as integers.
    """
    # Load the ShortProcessors once, if matrices need to be computed
    sps = loadShortProcessors(self.tilePaths, self.params_pixels)
    matrices = self.getMatrices(sps=sps)
    dx, dy = (section_matrix[2], section_matrix[5]) if section_matrix else (0, 0)
    spMontage = ShortProcessor(width, height)
    # Start pasting from the end, to bury the bad left edges
    for sp, matrix in reversed(zip(sps, matrices)):
      spMontage.insert(process(sp, self.params_pixels),  # TODO don't process separately, see above
                       int(sdx + matrix[2] + dx + 0.5),
                       int(sdy + matrix[5] + dy + 0.5)) # indices 2 and 5 are the X, Y translation
    
    return ArrayImgs.unsignedShorts(spMontage.getPixels(), width, height)



  def montagedImg8bit(self, width, height, section_matrix, sdx=0, sdy=0):
    """ Return an ArrayImg representing the montage
        width, height: dimensions of the canvas onto which to insert the tiles.
        section_matrix: if there is a transform to apply section-wide, to the whole montage.
                        Here, only the translation is applied, ultimately as integers.
    """
    # Load the ShortProcessors once, if matrices need to be computed
    sps = loadShortProcessors(self.tilePaths, self.params_pixels)
    matrices = self.getMatrices(sps=sps)
    # TODO if scale and shear values aren't 1.0, 0.0 then apply an affine transform.
    dx, dy = (section_matrix[2], section_matrix[5]) if section_matrix else (0, 0)
    spMontage = ShortProcessor(width, height)
    rois = []
    # If a file is in the repaired dir and it ends in TIFF, paint it first:
    # a crude way of signaling that the file was repaired and it's potentially incomplete,
    # particularly near the edges where it overlaps with other tiles.
    for filepath, sp, matrix in reversed(zip(self.tilePaths, sps, matrices)):
      if not (filepath.find("/repaired/") > 0 and filepath.endswith("tif")):
        continue
      # Paint repaired file that was saved as TIFF
      x = int(sdx + matrix[2] + dx + 0.5) # indices 2 and 5 are the X, Y translation
      y = int(sdy + matrix[5] + dy + 0.5)
      spMontage.insert(sp, x, y)
      rois.append(Roi(x, y, sp.getWidth(), sp.getHeight()))
    
    # Start pasting from the end, to bury the bad left edges
    for filepath, sp, matrix in reversed(zip(self.tilePaths, sps, matrices)):
      if filepath.find("/repaired/") > 0 and filepath.endswith("tif"):
        continue # already painted
      x = int(sdx + matrix[2] + dx + 0.5) # indices 2 and 5 are the X, Y translation
      y = int(sdy + matrix[5] + dy + 0.5)
      spMontage.insert(sp, x, y)
      rois.append(Roi(x, y, sp.getWidth(), sp.getHeight()))
    sps = None
    bpMontage = processTo8bit(spMontage, self.params_pixels)
    spMontage = None
    if self.params_pixels["invert"]:
      # paint white background as black
      # (Can't invert earlier as the min, max wouldn't match, leading to uneven illumination across tiles)
      sp = ShapeRoi(rois[0])
      for roi in rois[1:]:
        sp = sp.or(ShapeRoi(roi))
      bpMontage.setValue(0) # black
      bpMontage.fill(sp.getInverse(ImagePlus("", bpMontage))) # fill the inverse of the tiles areas
    
    return ArrayImgs.unsignedBytes(bpMontage.getPixels(), width, height)


def singleTile(tilePath, width, height, params_pixels, sdx=0, sdy=0, matrix=None, center=False):
  imp = load(tilePath, params_pixels)
  as8bit = params_pixels.get("as8bit", True)
  if as8bit:
    ipTile = processTo8bit(imp.getProcessor(), params_pixels)
    ip = ByteProcessor(width, height)
  else:
    ipTile = process(imp.getProcessor(), params_pixels)
    ip = ShortProcessor(width, height)
  if matrix:
    dx, dy = (matrix[2], matrix[5])
  elif params_pixels.has_key('single_tile_position'):
    dx, dy = params_pixels['single_tile_position']
  elif params_pixels.has_key('single_tile_position_fn'):
    dx, dy = params_pixels['single_tile_position_fn'](tilePath, imp)
  elif center:
    # WARNING this can be a breaking change
    dx, dy = int((width - imp.getWidth()) / 2), int((height - imp.getHeight()) / 2)
  else:
    dx, dy = (0, 0)
  ip.insert(ipTile,
            int(sdx + dx + 0.5),
            int(sdy + dy + 0.5))
  fn = ArrayImgs.unsignedBytes if as8bit else ArrayImgs.unsignedShorts
  aimg = fn(ip.getPixels(), [width, height])
  imp.flush()
  return aimg, ImagePlus("", ip)


class SectionLoader(CacheLoader):
  """
  A CacheLoader where each cell is a section made from loading and transforming multiple tiles or just one tile
  """
  def __init__(self, dimensions, groupNames, tileGroups, overlap, nominal_overlap, offset,
               paramsSIFT, paramsRANSAC, paramsTileConfiguration, csvDir, params_pixels,
               section_offsets=None, # A function that given an index returns a tuple of two integers
               matrices=None,
               crop_ROI=None):
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
    self.crop_ROI = crop_ROI # an ij.roi.Roi instance or any object with a getBounds() that returns a java.awt.Rectangle
    if self.matrices and len(self.groupNames) != len(self.matrices):
      raise Exception("Lengths of groupNames and rows in the matrices file don't match!")
  
  def get(self, index):
    groupName = self.groupNames[index]
    tilePaths = self.tileGroups[index]
    matrix = self.matrices[index] if self.matrices else None
    sdx, sdy = self.section_offsets(index) if self.section_offsets else (0, 0)
    as8bit = self.params_pixels["as8bit"]
    if self.crop_ROI is not None:
      bounds = self.crop_ROI.getBounds() # a java.awt.Rectangle
      width, height = bounds.width, bounds.height
      sdx += -bounds.x
      sdy += -bounds.y
    else:
      width, height = self.dimensions
    #
    if len(tilePaths) > 1:
      m = MontageSlice(groupName, tilePaths, self.overlap, self.nominal_overlap, self.offset,
                       self.paramsSIFT, self.paramsRANSAC, self.paramsTileConfiguration, self.params_pixels,
                       self.csvDir, Vector())
      if as8bit:
        aimg = m.montagedImg8bit(width, height,
                                 matrix,
                                 sdx=sdx, sdy=sdy)
      else:
        aimg = m.montagedImg(width, height,
                             matrix,
                             sdx=sdx, sdy=sdy)        
    elif 1 == len(tilePaths):
      aimg, imp = singleTile(tilePaths[0], width, height, self.params_pixels, sdx=sdx, sdy=sdy, matrix=matrix)
    else:
      # return empty Cell
      syncPrintQ("WARNING: number of tiles isn't 4 or 1")
      fn = ArrayImgs.unsignedBytes if as8bit else ArrayImgs.unsignedShorts
      aimg = fn([width, height]) # TODO this should be a constant DataAccess

    return Cell(self.dimensions + [1], # cell dimensions
                [0, 0, index], # position in the grid: 0, 0, 0, Z-index
                aimg.update(None)) # get the underlying DataAccess



class MontageAndSave(Callable):
  """ Generate the matrices for the montage, specifying the translation of each tile,
      and also save a scaled down version of the image into the scaled-montages folder.
  """
  def __init__(self, *args):
    self.args = args
  
  def call(self):
    try:
      return self.callImpl()
    except:
      printException()
      
  def montageAndSnapshot(self, groupName):
    syncPrintQ("Generating montage for " + groupName)
    args = self.args[:11]
    ms = MontageSlice(*args)
    params_pixels = self.args[8]
    section_width, section_height = self.args[11:13]
    ip = None
    # Generate the matrices and an image of the montage.
    # The call to montagedImg or montagedImg8bit will generate and store the montage matrices.
    if params_pixels.get("as8bit", True):
      img = ms.montagedImg8bit(section_width, section_height, None, sdx=0, sdy=0)
      ip = ByteProcessor(section_width, section_height, img.update(None).getCurrentStorageArray(), None)
    else:
      img = ms.montagedImg(section_width, section_height, None, sdx=0, sdy=0)
      ip = ShortProcessor(section_width, section_height, img.update(None).getCurrentStorageArray(), None)
    return ImagePlus(groupName, ip)
  
  def callImpl(self):
    groupName = self.args[0]
    tilePaths = self.args[1]
    montageDir = self.args[9]
    scaled_image_path = montageDir + "scaled-montages/" + groupName + ".tif"
    # Check if scaled image exists
    if os.path.exists(scaled_image_path):
      if len(tilePaths) > 1:
        # Check if the matrices file exists
        matrices = loadMatrices(groupName, montageDir)
        if matrices is not None:
          #syncPrintQ("Montage OK for " + groupName)
          return True
      else: # just one tile
        return True
    # Else, generate both, overwriting the image.
    # If the matrices exists but the scaled image doesn't, the matrices will simply be loaded, not computed.
    params_pixels = self.args[8]
    section_width, section_height = self.args[11:13]
    if len(tilePaths) > 1:
      imp = self.montageAndSnapshot(groupName)
    else:
      aimg, imp = singleTile(tilePaths[0], section_width, section_height, params_pixels, sdx=0, sdy=0, matrix=None)
    # Save the image, scaled if required
    k = params_pixels.get("interim_scale", 1.0)
    if k < 1.0:
      imp = imp.resize(int(section_width * k + 0.5), int(section_height * k + 0.5), "bilinear")
    FileSaver(imp).saveAsTiff(scaled_image_path)
    return True


def ensureMontagesAndScaledImage(groupNames, tileGroups, overlap, nominal_overlap, offset,
                                 paramsSIFT, paramsRANSAC, paramsTileConfiguration, montageDir, nThreads,
                                 section_width, section_height, params_pixels):
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
  montageDir: where to save the matrix CSV files, one per montage and section.
  
  Will save a possibly scaled-down image of the montage as a TIFF file under csvDir/scaled-montages/
  """
  exe = newFixedThreadPool(nThreads)
  try:
    futures = []
    failed = Vector() # synchronized access
    
    # Folder for storing scaled-down versions of each montaged version
    ensureDirsExist(os.path.join(montageDir, "scaled-montages"))

    # Iterate all sections in order and generate the transformation matrices defining a montage for each section
    for groupName, tilePaths in izip(groupNames, tileGroups):
      # Montage the tiles: compute a matrix detailing a TranslationModel2D for each tile
      futures.append(exe.submit(MontageAndSave(groupName, tilePaths, overlap, nominal_overlap, offset,
                                               paramsSIFT, paramsRANSAC, paramsTileConfiguration, params_pixels, montageDir, failed,
                                               section_width, section_height)))

    # Await them all
    for future in futures:
      future.get()

    if len(failed) > 0:
      # Print failed montages
      syncPrintQ("Montages that failed:\n%s" % "\n".join(map(str, failed)))
      # Save failed montages to disk
      with open(os.path.join(montageDir, "failed_montages_" + datetime.now().strftime("%Y-%m-%d_%Hh-%Mm-%Ss") + ".csv"), 'w') as f:
        f.write("\n".join(map(str, failed)))
        # Ensure it's written
        f.flush()
        os.fsync(f.fileno())
    else:
      syncPrintQ("No montages known to have failed.")

  finally:
    exe.shutdown()




def ensureMontages(groupNames, tileGroups, overlap, nominal_overlap, offset,
                   paramsSIFT, paramsRANSAC, paramsTileConfiguration, params_pixels, csvDir, nThreads):
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
        futures.append(exe.submit(MontageSlice(groupName, tilePaths, overlap, nominal_overlap, offset,
                                               paramsSIFT, paramsRANSAC, paramsTileConfiguration, params_pixels, csvDir, failed)))

    # Await them all
    for future in futures:
      future.get()

    if len(failed) > 0:
      # Print failed montages
      syncPrintQ("Montages that failed:\n%s" % "\n".join(map(str, failed)))
      # Save failed montages to disk
      with open(os.path.join(csvDir, "failed_montages_" + datetime.now().strftime("%Y-%m-%d_%Hh-%Mm-%Ss") + ".csv"), 'w') as f:
        f.write("\n".join(map(str, failed)))
        # Ensure it's written
        f.flush()
        os.fsync(f.fileno())
    else:
      syncPrintQ("No montages known to have failed.")

  finally:
    exe.shutdown()


class CheckSectionFiles(Callable):
  def __init__(self, groupName_, tilePaths_, check, alternative_dir,
               ignore_images, alternative_filenames, replace_images):
    self.groupName_ = groupName_
    self.tilePaths_ = tilePaths_
    self.check = check
    self.alternative_dir = alternative_dir
    self.ignore_images = ignore_images
    self.alternative_filenames = alternative_filenames
    self.replace_images = replace_images
    
  def call(self):
    """
    Ensure tilePaths are sorted, in place,
    and check that tiles are of the same dimensions and file size within each section.
    Return self.groupName_ if it is to be removed, otherwise return None.
    """
    # For tiles with a filename containing their position in a grid, like 0-0-0
    pattern = re.compile("^\d+-(\d+)-(\d+)\..*$") # any extension
    
    def coordsFn(filepath):
      # Parse the row and col from the e.g., 0-0-0 string in the file name
      row, col = re.match(pattern, filepath[filepath.rfind('_')+1:]).groups()
      return int(row) * 10 + int(col) # Assumes no more than 9 rows or cols

    self.tilePaths_.sort(key=coordsFn) # in place

    # Replace and remove filepaths as needed
    if self.alternative_dir or len(self.ignore_images) > 0:
      drop = []
      for i, tilePath in enumerate(self.tilePaths_):
        filename = os.path.basename(tilePath)
        # Check if tilePath is to be ignored and remove it from the group
        if filename in self.ignore_images:
          drop.append(i)
        # Check if tilePath has to be replaced
        elif filename in self.alternative_filenames:
          tilePaths_[i] = os.path.join(alternative_dir, filename)
          syncPrintQ("Replaced filepath for %s :\n%s\n" % (filename, tilePaths_[i]))
        elif filename in self.replace_images:
          tilePaths_[i] = os.path.join(self.alternative_dir, self.replace_images[filename])
          syncPrintQ("Replaced filepath for %s :\n%s\n" % (filename, tilePaths_[i]))
      # Remove from group any tilePath to ignore
      for i in drop:
        syncPrintQ("Will ignore image %s" % self.tilePaths_[i])
        del self.tilePaths_[i]
      # If no tiles left, remove section
      if 0 == len(self.tilePaths_):
        # Return the name of the section to be removed, and to be added to to_remove
        return self.groupName_

    if self.check:
      return self.checkFileProperties()
    # All good with the section
    return None
   

  def checkFileProperties(self):
    # Check that all tiles have the same dimensions (can't check for same file size due to possible replacements)
    widths = []
    heights = []
    #fileSizes = []  # can't compare file sizes: some my have been replaced by TIFF files etc. and differ while having the same width and height
    drop = set()
    for i, tilePath in enumerate(self.tilePaths_):
      try:
        if tilePath.endswith(".dat"):
          header = readFIBSEMHeader(tilePath)
          if header is None:
              drop.add(i)
              syncPrintQ("%s HEADER: %s" % (self.groupName_, str(type(header))))
          else:
            widths.append(header.xRes)
            heights.append(header.yRes)
            #fileSizes.append(os.stat(tilePath).st_size)
            #syncPrintQ("tilePath: %s\ndimensions: %i, %i" % (tilePath, header.xRes, header.yRes))
        else:
          # Not a .DAT file
          info = imageInfo(tilePath)
          widths.append(info["width"])
          heights.append(info["height"])
          # ignore file sizes
      except:
        syncPrintQ("Failed to read header or file size for:\n" + tilePath, copy_to_stdout=True)
        drop.add(i)
    # End of for loop
    
    if not (1 == len(set(widths)) and 1 == len(set(heights))): # and 1 == len(set(fileSizes)):
      syncPrintQ("Inconsistent tile dimensions of file sizes in section:\n%s\n%s" %(self.groupName_, "\n".join(map(str, izip(widths, heights)))), copy_to_stdout=True)
      # Return the groupName_ so that this section can be added to to_remove and then deleted
      return self.groupName_

    # If all tiles were removed, then:
    if len(drop) == len(self.tilePaths_):
      syncPrintQ("All tiles dropped for section: %s" % self.groupName_, copy_to_stdout=True)
      # Return the groupName_ so that this section can be added to to_remove and then deleted
      return self.groupName_
    
    # Keep the section: there is at least one readable tile file, and when more than one, all have the same dimensions
    return None
    


def makeMontageGroups(filepaths, to_remove, check, alternative_dir=None, ignore_images=set(), writeDir=None, replace_images={}):
  """
  Does not assume anything regarding the number of tiles per montage.
  
  Parameters:
  filepaths: list of all file paths to all image tiles
  to_remove: a set of sections to ignore because they have data inconsistency problems like missing tiles or truncated tiles
  check: whether to check the header and file sizes for issues.
  alternative_dir: if a file fails to open, try to find it in this directory.
  ignore_images: a set of image filenames to ignore and leave out of the montages.
  replace_images: if the image filename is in, use the provided alternative which is under the alternative_dir.

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

  n_threads = max(1, numCPUs() -1)
  w = ParallelTasks("checkSectionFiles", n_threads=n_threads)
  try:
    # Note CheckSectionFiles will modify each tilePaths_ for each section in place.
    for groupName_ in w.chunkConsume(n_threads * 2,
                                     (CheckSectionFiles(groupName_, tilePaths_, check, alternative_dir,
                                                       ignore_images, alternative_filenames, replace_images)
                                      for groupName_, tilePaths_ in groups.iteritems())):
      if groupName_:
        # If not None then remove it
        to_remove.add(groupName_)
        del groups[groupName_]
        syncPrintQ("Will ignore section: " + groupName_, copy_to_stdout=True)
  finally:
    w.destroy()    

  for groupName_ in to_remove:
    if groupName_ in groups:
      del groups[groupName_]
    else:
      syncPrintQ("Unexpectedly %s is not in groups." % groupName_)
    syncPrintQ("Will ignore section: " + groupName_, copy_to_stdout=True)
  
  if check:
    syncPrintQ("Invalid sections: %i" % len(to_remove))
  else:
    syncPrintQ("Check was NOT done to detect invalid sections.")
    

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
        # Ensure it's written
        fh.flush()
        os.fsync(fh.fileno())

  return groupNames, tileGroups



# Define a virtual CellImg expressing all the montages, one per section
def makeVolume(groupNames, tileGroups, section_width, section_height, overlap, nominal_overlap, offset,
               paramsSIFT, paramsRANSAC, paramsTileConfiguration, csvDir, params_pixels,
               show=True, matrices=None, section_offsets=None, title=None, cache_size=64,
               showTable=True, crop_ROI=None):
  if crop_ROI:
    bounds = crop_ROI.getBounds() # a java.awt.Rectangle
    dimensions = [bounds.width, bounds.height]
  else:
    dimensions = [section_width, section_height]
  volume_dimensions = dimensions + [len(groupNames)]
  cell_dimensions = dimensions + [1]
  pixelType = UnsignedByteType # UnsignedShortType
  primitiveType = PrimitiveType.BYTE #.SHORT
  
  volumeImg = lazyCachedCellImg(SectionLoader(dimensions, groupNames, tileGroups, overlap, nominal_overlap, offset,
                                              paramsSIFT, paramsRANSAC, paramsTileConfiguration, csvDir, params_pixels,
                                              matrices=matrices,
                                              section_offsets=section_offsets,
                                              crop_ROI=crop_ROI),
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
    # Show a JTable for opening raw images and slice ranges
    if showTable:
      table = makeMontageTable(groupNames, tileGroups, imp, volumeImg, csvDir, show=True)
  
  return volumeImg



def makeSliceLoader(groupNames, volumeImg):
  """
    groupNames: a list of lists, each defining a section with one or more tiles
    volumeImg: a CellImg
  """
  # Will use groupNames as filepaths, and a load function that will return hyperslices of volumeImg
  indices = {groupName: i for i, groupName in enumerate(groupNames)}
  copier = createBiConsumerTypeSet(GenericByteType) # GenericByteType has the "set(Type)" method 

  def sliceLoader(volumeImg, indices, groupName):
    # Each slice is already an ArrayImg: get the DataAccess of the Cell at index, which is a 2D image
    if isinstance(volumeImg, CellImg):
      cell = volumeImg.getCells().randomAccess().setPositionAndGet([0, 0, indices[groupName]])
      pixels = cell.getData().getCurrentStorageArray()
      return ImagePlus(groupName, ByteProcessor(volumeImg.dimension(0), volumeImg.dimension(1), pixels, None))
    else:
      # copy
      img2d = Views.hyperSlice(volumeImg, 2, indices[groupName])
      aimg = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(img2d))
      #syncPrintQ(str(img2d) + " " + str(img2d.dimension(0)) + "." + str(img2d.dimension(1))
      #           + "\n" + str(Intervals.dimensionsAsLongArray(img2d)))
      #ImgMath.compute(ImgMath.img(img2d)).into(aimg)
      LoopBuilder.setImages(img2d, aimg) \
                 .multiThreaded(False) \
                 .forEachPixel(copier)
      return ImagePlus(groupName, ByteProcessor(aimg.dimension(0), aimg.dimension(1), aimg.update(None).getCurrentStorageArray(), None))
    
  
  # Return a 1-argument function that takes the groupName as its sole argument
  return partial(sliceLoader, volumeImg, indices)


def fuseMatrices(matricesSIFT, matricesBM):
  # fuse the matrices: concatenate the translation transforms
  # WARNING the SIFT+RANSAC registration will have been expressed as integers, which is what the blockmatching saw, so correct for that
  matrices = []
  for m1, m2 in izip(matricesSIFT, matricesBM):
    # The SIFT alignment will have been expressed as integers, so correct for that
    matrices.append(array([1, 0, int(m1[2] + 0.5) + m2[2], 0, 1, int(m1[5] + 0.5) + m2[5]], 'd'))


def fuseTranslationMatrices(matricesList):
  # matricesList is a list of lists of arrays computed with a TranslationModel2D
  return [array([1, 0, sum(m[2] for m in ms),
                 0, 1, sum(m[5] for m in ms)], 'd')
          for ms in izip(*matricesList)]


def runMontaging(name, srcDir, tgtDir, montageDir, repairedDir,
                 offset, overlap, nominal_overlap,
                 section_width, section_height,
                 first_section, last_section, replace_sections,
                 params_pixels, paramsSIFT, paramsRANSAC, paramsTileConf,
                 to_remove, ignore_images, replace_images,
                 showTable=True, show=True):
  """
  Main entry point.
  """
  
  if name is None or 0 == len(name):
    print "Enter the 'name' of the volume: the folder name containing .dat files."
    return
  
  ensureDirsExist(tgtDir, montageDir, repairedDir)
  
  # Find all .dat files, as a sorted list
  # NOTE will be cached into a text file
  filepaths, filepaths_cached = loadFilePaths(srcDir, ".dat", montageDir, "imagefilepaths")
  
  # Determine whether to run an expensive, comprehensive file check for all image tiles
  # that also checks for consistency of tile dimensions within each section
  check = not os.path.exists(os.path.join(montageDir, "check"))

  # Sorted group names, one per section
  groupNames, tileGroups = makeMontageGroups(filepaths, to_remove, check,
                                             alternative_dir=repairedDir,
                                             ignore_images=ignore_images,
                                             replace_images=replace_images,
                                             writeDir=montageDir)

  if check:
    # Mark that a comprehensive file check has successfully completed by writing a marker file
    File(os.path.join(montageDir, "check")).createNewFile()  # a new empty file to serve as marker  

  # Define the range of sections to montage
  groupNames = groupNames[first_section:last_section]
  tileGroups = tileGroups[first_section:last_section]

  # Substitute sections with problems for other, adjacent sections
  for bad, good in replace_sections.iteritems():
    groupNames[bad] = groupNames[good]
    tileGroups[bad] = tileGroups[good]

  # How many sections to montage in parallel
  nThreadsMontaging = max(1, int(numCPUs() / (paramsTileConf["nThreadsOptimizer"] / 2)))

  # Print groups to a CSV file if it's the first time
  if not filepaths_cached:
    rows = ["section index (1-based),groupName,number of tiles"]
    for i, (groupName, tilePaths) in enumerate(izip(groupNames, tileGroups)):
      rows.append("%i,%s,%i" % (i+1, groupName, len(tilePaths)))
    with open(os.path.join(montageDir, "sections-list.csv"), 'w') as f:
      f.write("\n".join(rows))
      # Ensure it's written
      f.flush()
      os.fsync(f.fileno())

  syncPrintQ("Number of sections found valid: %i" % len(groupNames))

  # Old approach:

  # Montage all sections
  #ensureMontages(groupNames, tileGroups, overlap, nominal_overlap, offset,
  #               paramsSIFT, paramsRANSAC, paramsTileConf, montageDir, nThreadsMontaging,
  #               params_pixels)

  # Prepare an image volume where each section is a Cell with an ArrayImg showing a montage or a single image, and preprocessed (invert + CLAHE)
  # NOTE: it's 8-bit
  #volumeImgMontaged = makeVolume(groupNames, tileGroups, section_width, section_height, overlap, nominal_overlap, offset,
  #                               paramsSIFT, paramsRANSAC, paramsTileConf, montageDir, params_pixels,
  #                               show=True, matrices=None, section_offsets=sectionOffsets, title="%s - montages" % name)

  # New approach:
  
  # Montage all sections and save an image of each montage under montageDir/scaled-montages/
  ensureMontagesAndScaledImage(groupNames, tileGroups, overlap, nominal_overlap, offset,
                               paramsSIFT, paramsRANSAC, paramsTileConf, montageDir, nThreadsMontaging,
                               section_width, section_height, params_pixels)

  # Open a virtual image of the whole scaled-montages folder
  scaled_filepaths = [os.path.join(montageDir, "scaled-montages/" + groupName + ".tif") for groupName in groupNames]
  
  if params_pixels.get("as8bit", True):
    pixelType = UnsignedByteType
    primitiveType = PrimitiveType.BYTE
    asArrayImg = lambda index, imp: ArrayImgs.unsignedBytes(imp.getProcessor().getPixels(), imp.getWidth(), imp.getHeight())
  else:
    pixelType = UnsignedShortType
    primitiveType = PrimitiveType.SHORT
    asArrayImg = lambda index, imp: ArrayImgs.unsignedShorts(imp.getProcessor().getPixels(), imp.getWidth(), imp.getHeight())
  
  k = params_pixels.get("interim_scale", 1.0)
  width =  int(section_width  * k + 0.5)
  height = int(section_height * k + 0.5)
    
  volumeImgMontagedScaled = lazyCachedCellImg(SectionCellLoader(scaled_filepaths, asArrayImg),
                                              [width, height, len(groupNames)],
                                              [width, height, 1],
                                              pixelType, primitiveType, maxRefs=0)
  
  if show:
    # Display as an ImageJ stack
    #imp = wrap(volumeImgMontagedScaled)
    #imp.setTitle(name + " - montage")
    #imp.show()
  
    # With a virtual stack where slice labels work
    imp = wrap8bit(volumeImgMontagedScaled, name + " - montage %f" % k, labelsFn=lambda n: groupNames[n-1])
    imp.show()
  
  # Show a JTable for opening raw images and slice ranges
  if showTable:
    table = makeMontageTable(groupNames, tileGroups, imp, volumeImgMontagedScaled, montageDir, show=True)
  
  return volumeImgMontagedScaled, groupNames, tileGroups


def loadMontagedImg(srcDir, montageDir, repairedDir,
                    to_remove, ignore_images, replace_images,
                    first_section, last_section, replace_sections,
                    section_width, section_height, crop_roi, params_pixels,
                    cache_size=64):
  """ At full resolution, loaded from the original .DAT files.
      Assumes matrices for each section exist, otherwise will fail.
  """
  filepaths, filepaths_cached = loadFilePaths(srcDir, ".dat", montageDir, "imagefilepaths")
  #
  groupNames, tileGroups = makeMontageGroups(filepaths, to_remove, False,
                                             alternative_dir=repairedDir,
                                             ignore_images=ignore_images,
                                             replace_images=replace_images,
                                             writeDir=montageDir)
  # Define the range of sections to montage
  groupNames = groupNames[first_section:last_section]
  tileGroups = tileGroups[first_section:last_section]

  # Substitute sections with problems for other, adjacent sections
  for bad, good in replace_sections.iteritems():
    groupNames[bad] = groupNames[good]
    tileGroups[bad] = tileGroups[good]
  #
  crop_ROI = None
  if crop_roi:
    crop_ROI = Roi(*crop_roi)
  #
  img = makeVolume(groupNames, tileGroups, section_width, section_height, None, None, None,
                   None, None, None, montageDir, params_pixels,
                   show=False, matrices=None, section_offsets=None, title=None, cache_size=cache_size,
                   showTable=False, crop_ROI=crop_ROI)
                   
  return img, groupNames, tileGroups, filepaths
