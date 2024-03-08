import os

from util import newFixedThreadPool, syncPrintQ, printException
from registration import saveMatrices, loadMatrices
from lib.io import loadFilePaths, readFIBSEMHeader, readFIBSEMdat, lazyCachedCellImg
from lib.ui import wrap, addWindowListener
from lib.serial2Dregistration import ensureSIFTFeatures, makeImg

from java.util import ArrayList
from java.lang import Double, Exception
from java.util.concurrent import Callable
from ij.process import ShortProcessor, ByteProcessor
from ij.gui import ShapeRoi, PointRoi, Roi
from ij import ImagePlus
from net.imglib2.img.array import ArrayImgs
from net.imglib2.algorithm.phasecorrelation import PhaseCorrelation2
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.type.numeric.complex import ComplexFloatType
from net.imglib2.type.numeric.integer import UnsignedShortType, UnsignedByteType
from net.imglib2.type import PrimitiveType
from net.imglib2.img.array import ArrayImgFactory
from net.imglib2.img.cell import Cell
from net.imglib2.cache import CacheLoader
from net.imglib2.view import Views
from net.imglib2.util import Intervals
from net.imglib2.img.display.imagej import ImageJFunctions as IL
#from net.imglib2.algorithm.math import ImgMath
from mpicbg.models import ErrorStatistic, TranslationModel2D, TransformMesh, PointMatch, Point, NotEnoughDataPointsException, Tile, TileConfiguration
from mpicbg.ij.clahe import FastFlat as CLAHE
from mpicbg.ij import SIFT # see https://github.com/axtimwalde/mpicbg/blob/master/mpicbg/src/main/java/mpicbg/ij/SIFT.java
from mpicbg.imagefeatures import FloatArray2DSIFT
from mpicbg.imglib.type.numeric.complex import ComplexFloatType

from functools import partial
from collections import defaultdict
from itertools import izip
from jarray import zeros, array

# TODO: generalise to NxM montages and even arbitrary montages

class MontageSlice2x2(Callable):
  def __init__(self, groupName, tilePaths, overlap, nominal_overlap, offset, paramsSIFT, paramsRANSAC, csvDir):
    """
    groupName:
    tilePaths:
    overlap: the amount of pixels that two adjacent tiles should share
    offset: how many pixels to ignore starting from x=0, given that the left edge of a FIBSEM image is non-linearly stretched and with low signal to noise.
    paramsSIFT:
    paramsRANSAC:
    csvDir: where to store the CSV files, one per montage
    """
    # EXPECTS 4 filepaths with filenames ending in ["_0-0-0.dat", "_0-0-1.dat", "_0-1-0.dat", "_0-1-1.dat"]
    # ASSUMES all tiles have the same dimensions
    self.groupName = groupName
    self.tilePaths = list(sorted(tilePaths))
    self.overlap = overlap
    self.nominal_overlap = nominal_overlap
    self.offset = offset
    self.paramsSIFT = paramsSIFT
    self.paramsRANSAC = paramsRANSAC
    self.csvDir = csvDir
    self.params = {"max_sd": 1.5, # max_sd: maximal difference in size (ratio max/min)
                   "max_id": Double.MAX_VALUE, # max_id: maximal distance in image space
                   "rod": 0.9} # rod: ratio of best vs second best
    self.paramsTileConfiguration = {
      "maxAllowedError": 0, # Saalfeld recommends 0
      "maxPlateauwidth": 200, # Like in TrakEM2
      "maxIterations": 1000, # Saalfeld recommends 1000 -- here, 2 iterations (!!) shows the lowest mean and max error for dataset FIBSEM_L1116
      "damp": 1.0, # Saalfeld recommends 1.0, which means no damp
    }
    
  def getFeatures(self, sp, roi, debug=False):
    sp.setRoi(roi)
    sp = sp.crop()
    paramsSIFT = self.paramsSIFT.clone()
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
    
  def getPointMatches(self, sp0, roi0, sp1, roi1, offset, mode="SIFT"):
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
      features0 = self.getFeatures(sp0, roi0)
      features1 = self.getFeatures(sp1, roi1)
      pointmatches = FloatArray2DSIFT.createMatches(features0,
                                                    features1,
                                                    self.params.get("max_sd", 1.5), # max_sd: maximal difference in size (ratio max/min)
                                                    model,
                                                    self.params.get("max_id", Double.MAX_VALUE), # max_id: maximal distance in image space
                                                    self.params.get("rod", 0.9)) # rod: ratio of best vs second best
    if 0 == pointmatches.size():
      return pointmatches

    # Filter matches by geometric consensus
    inliers = ArrayList()
    iterations = self.paramsRANSAC.get("iterations", 1000)
    maxEpsilon = self.paramsRANSAC.get("maxEpsilon", 25) # pixels
    minInlierRatio = self.paramsRANSAC.get("minInlierRatio", 0.01) # 1%
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

  def connectTiles(self, sps, tiles, i, j, roi0, roi1, offset):
    pointmatches = self.getPointMatches(sps[i], roi0, sps[j], roi1, offset)
    if pointmatches.size() > 0:
      tiles[i].connect(tiles[j], pointmatches) # reciprocal connection
      return True
    # Else
    syncPrintQ("Disconnected tile! No pointmatches found for %i vs %i of section %s" % (i, j, self.groupName))
    return False
    
  def loadShortProcessors(self):
    for filepath in self.tilePaths:
      syncPrintQ("#%s#" % filepath)
    # Load images (TODO: should use FIBSEM_Reader instead)
    return [readFIBSEMdat(filepath, channel_index=0, asImagePlus=True)[0].getProcessor() for filepath in self.tilePaths]

  def getMatrices(self):
    # For each section to montage, for each image tile,
    # extract features from the appropriate ROI along the overlapping edges
    
    # Check if matrices exist already:
    matrices = loadMatrices(self.groupName, self.csvDir)
    if matrices is not None:
      return matrices
    
    sps = self.loadShortProcessors()
      
    # Assumes images have the same dimensions
    width = sps[0].getWidth()
    height = sps[1].getHeight()
    
    # Define 4 ROIs: (x, y, width, height)
    # left-right
    roiEast = Roi(width - self.overlap, 0, self.overlap, height) # right edge, for tile 0-0-0  (and 0-1-0)
    roiWest = Roi(self.offset, 0, self.overlap, height)          # left edge,  for tile 0-0-1  (and 0-1-1)
    # top-bottom
    roiSouth = Roi(0, height - self.overlap, width, self.overlap) # bottom edge, for tile 0-0-0  (and 0-0-1)
    roiNorth = Roi(0, 0, width, self.overlap)                     # top edge,    for tile 0-1-0  (and 0-1-1)
    
    # Declare tile links
    tc = TileConfiguration()
    tiles = [Tile(TranslationModel2D()) for _ in self.tilePaths]
    tc.addTiles(tiles)
    # ASSUMES that sps is a list of sorted tiles, as [0-0 top left, 0-1 top right, 1-0 bottom left, 1-1 bottom right]
    a = self.connectTiles(sps, tiles, 0, 1, roiEast, roiWest, self.offset)
    b = self.connectTiles(sps, tiles, 2, 3, roiEast, roiWest, self.offset)
    c = self.connectTiles(sps, tiles, 0, 2, roiSouth, roiNorth, 0)
    d = self.connectTiles(sps, tiles, 1, 3, roiSouth, roiNorth, 0)
    tc.fixTile(tiles[0]) # top left tile
    
    if not a and not b and not c and not d:
      syncPrintQ("All tiles failed to connect for section %s " % (self.groupName))
      # TODO: either montage them manually, or try to montage by using cross-section correspondances.
      # Store the expected tile positions given the nominal_overlap
      matrices = [array([1.0, 0.0, 0.0,
                         0.0, 1.0, 0.0], 'd'),
                  array([1.0, 0.0, width - self.nominal_overlap,
                         0.0, 1.0, 0.0], 'd'),
                  array([1.0, 0.0, 0.0,
                         0.0, 1.0, height - self.nominal_overlap], 'd'),
                  array([1.0, 0.0, width - self.nominal_overlap,
                         0.0, 1.0, height - self.nominal_overlap], 'd')]
      saveMatrices(self.groupName, matrices, self.csvDir)
      return matrices
    
    # Optimise tile positions
    maxAllowedError = self.paramsTileConfiguration["maxAllowedError"]
    maxPlateauwidth = self.paramsTileConfiguration["maxPlateauwidth"]
    maxIterations   = self.paramsTileConfiguration["maxIterations"]
    damp            = self.paramsTileConfiguration["damp"]
    tc.optimize(ErrorStatistic(maxPlateauwidth + 1), maxAllowedError, maxIterations, maxPlateauwidth, damp)
    
    # Save transformation matrices
    matrices = []
    for tile in tiles:
      a = zeros(6, 'd')
      tile.getModel().toArray(a)
      matrices.append(array([a[0], a[2], a[4], a[1], a[3], a[5]], 'd'))
    saveMatrices(self.groupName, matrices, self.csvDir)
    return matrices
  
  def call(self):
    return self.getMatrices()

  def montagedImg(self, width, height, section_matrix, invert=False, CLAHE_params=None):
    """ Return an ArrayImg representing the montage
        width, height: dimensions of the canvas onto which to insert the tiles.
        section_matrix: if there is a transform to apply section-wide, to the whole montage.
                        Here, only the translation is applied, ultimately as integers.
    """
    matrices = self.getMatrices()
    dx, dy = (section_matrix[2], section_matrix[5]) if section_matrix else (0, 0)
    sps = self.loadShortProcessors()
    spMontage = ShortProcessor(width, height)
    # Start pasting from the end, to bury the bad left edges
    for sp, matrix in reversed(zip(sps, matrices)):
      spMontage.insert(process(sp, invert=invert, CLAHE_params=CLAHE_params),  # TODO don't process separately, see above
                       int(matrix[2] + dx + 0.5),
                       int(matrix[5] + dy + 0.5)) # indices 2 and 5 are the X, Y translation
    
    return ArrayImgs.unsignedShorts(spMontage.getPixels(), width, height)
    
    
    
  def montagedImg8bit(self, width, height, section_matrix, invert=False, CLAHE_params=None):
    """ Return an ArrayImg representing the montage
        width, height: dimensions of the canvas onto which to insert the tiles.
        section_matrix: if there is a transform to apply section-wide, to the whole montage.
                        Here, only the translation is applied, ultimately as integers.
    """
    matrices = self.getMatrices()
    dx, dy = (section_matrix[2], section_matrix[5]) if section_matrix else (0, 0)
    sps = self.loadShortProcessors()
    spMontage = ShortProcessor(width, height)
    rois = []
    # Start pasting from the end, to bury the bad left edges
    for sp, matrix in reversed(zip(sps, matrices)):
      x = int(matrix[2] + dx + 0.5) # indices 2 and 5 are the X, Y translation
      y = int(matrix[5] + dy + 0.5)
      spMontage.insert(sp, x, y)
      rois.append(Roi(x, y, sp.getWidth(), sp.getHeight()))
    sps = None
    bpMontage = processTo8bit(spMontage, invert=invert, CLAHE_params=CLAHE_params)
    if invert:
      # paint white background as black
      # (Can't invert earlier as the min, max wouldn't match, leading to uneven illumunation across tiles)
      sp = ShapeRoi(rois[0])
      for roi in rois[1:]:
        sp = sp.or(ShapeRoi(roi))
      bpMontage.setValue(0) # black
      bpMontage.fill(sp.getInverse(ImagePlus("", bpMontage))) # fill the inverse of the tiles areas
    
    return ArrayImgs.unsignedBytes(bpMontage.getPixels(), width, height)


def processTo8bit(sp, invert=False, CLAHE_params=None):
  """ WARNING will alter sp. """
  # Find min and max of the image yet to be inverted
  sp.findMinAndMax()
  maximum = sp.getMax() # even though this is really the min, 16-bit images get inverted within their display range
                        # so after .invert() this will be the max.
                        # If it was done after .invert(), the black border would be 65535 and that max is the wrong one.
  # First invert
  if invert:
    sp.invert()
  # Second determine and set display range
  #sp.findMinAndMax()
  sp.setMinAndMax(0, maximum)
  # Third convert to 8-bit
  bp = sp.convertToByte(True) # sets the display range into stone
  sp = None
  # Fourth run CLAHE (runs equally well on 16-bit as on 8-bit, within +1/-1 difference in pixel values)
  if CLAHE_params:
    blockRadius, n_bins, slope = CLAHE_params
    CLAHE.run(ImagePlus("", bp), blockRadius, n_bins, slope, None)
  return bp



def process(sp, invert=False, CLAHE_params=None):
  if invert:
    sp.invert()
  if CLAHE_params:
    blockRadius, n_bins, slope = CLAHE_params
    CLAHE.run(ImagePlus("", sp), blockRadius, n_bins, slope, None)
  return sp

class SectionLoader(CacheLoader):
  """
  A CacheLoader where each cell is a section made from loading and transforming multiple tiles or just one tile
  """
  def __init__(self, dimensions, groupNames, tileGroups, overlap, nominal_overlap, offset, paramsSIFT, paramsRANSAC,
               csvDir, matrices=None, invert=False, CLAHE_params=None, as8bit=False):
    """
    csvDir: the directory specifying the montages, one matrices file per section.
    """
    self.dimensions = dimensions # a list of [width, height] for the canvas onto which draw the image tiles
    self.groupNames = groupNames # list of names of each group, used to find its montage CSV if any
    self.tileGroups = tileGroups # a list of lists of file paths to .dat files, one per section
    self.overlap = overlap
    self.offset = offset
    self.paramsSIFT = paramsSIFT
    self.paramsRANSAC = paramsRANSAC
    self.csvDir = csvDir
    self.as8bit = as8bit
    self.matrices = matrices # for alignment in Z
    if self.matrices and len(self.groupNames) != len(self.matrices):
      raise Exception("Lengths of groupNames and rows in the matrices file don't match!")
    self.invert = invert
    self.CLAHE_params = CLAHE_params
  
  def get(self, index):
    groupName = self.groupNames[index]
    tilePaths = self.tileGroups[index]
    matrix = self.matrices[index] if self.matrices else None
    #
    if 4 == len(tilePaths):
      m2x2 = MontageSlice2x2(groupName, tilePaths, self.overlap, self.nominal_overlap, self.offset,
                             self.paramsSIFT, self.paramsRANSAC, self.csvDir)
      if self.as8bit:
        aimg = m2x2.montagedImg8bit(self.dimensions[0], self.dimensions[1],
                                    matrix, invert=self.invert, CLAHE_params=self.CLAHE_params)
      else:
        aimg = m2x2.montagedImg(self.dimensions[0], self.dimensions[1],
                                matrix, invert=self.invert, CLAHE_params=self.CLAHE_params)
    elif 1 == len(tilePaths):
      imp = readFIBSEMdat(tilePaths[0], channel_index=0, asImagePlus=True)[0]
      if self.as8bit:
        ipTile = processTo8bit(imp.getProcessor(), invert=self.invert, CLAHE_params=self.CLAHE_params)
        ip = ByteProcessor(self.dimensions[0], self.dimensions[1])
      else:
        ipTile = imp.getProcessor()
        ip = ShortProcessor(self.dimensions[0], self.dimensions[1])
      dx, dy = (matrix[2], matrix[5]) if matrix else (0, 0)
      ip.insert(ipTile,
                int(dx + 0.5),
                int(dy + 0.5))
      fn = ArrayImgs.unsignedBytes if self.as8bit else ArrayImgs.unsignedShorts
      aimg = fn(ip.getPixels(), self.dimensions)
      imp.flush()
      imp = None
      ip = None
    else:
      # return empty Cell
      syncPrintQ("WARNING: number of tiles isn't 4 or 1")
      fn = ArrayImgs.unsignedBytes if self.as8bit else ArrayImgs.unsignedShorts
      aimg = fn(self.dimensions) # TODO this should be a constant DataAccess

    return Cell(self.dimensions + [1], # cell dimensions
                [0, 0, index], # position in the grid: 0, 0, 0, Z-index
                aimg.update(None)) # get the underlying DataAccess


def ensureMontages2x2(groupNames, tileGroups, overlap, nominal_overlap, offset, paramsSIFT, paramsRANSAC, csvDir, nThreads):
  """
  Extract features and a matrix describing a TranslationModel2D for all tiles that need montaging.
  Each group must consist of 1 tile (no montage needed) or 4 tiles, which are assumed to be placed
  in a barely overlapping 2 x 2 configuration.
  The overlap between tiles is defined by overlap.
  The offset is for ignoring that many pixels from the left edge, which are artifactually
  non-linearly compressed and stretched in FIBSEM images. 
  
  groupNames: a list of names, with the common part of the filename of all tiles in a section.
  tileGroups: a list of lists of tile filenames.
          In other words, these two lists are correlated, and each entry represents a section with 1 or 4 image tiles in it.
  overlap: the amount of pixels of overlap between two tiles in the 2x2 grid.
  offset: the amount of pixels to ignore from the left edge of an image tile.
  paramsSIFT: for montaging using scale invariant feature transform (SIFT).
  csvDir: where to save the matrix CSV files, one per montage and section.
  """
  exe = newFixedThreadPool(nThreads)
  try:

    futures = []

    # Iterate all sections in order and generate the transformation matrices defining a montage for each section
    for groupName, tilePaths in izip(groupNames, tileGroups):
      # EXPECTING 2x2 tiles or 1
      if 4 == len(tilePaths):
        # Montage the tiles: compute a matrix detailing a TranslationModel2D for each tile
        futures.append(exe.submit(MontageSlice2x2(groupName, tilePaths, overlap, nominal_overlap, offset, paramsSIFT, paramsRANSAC, csvDir)))
      elif 1 == len(tilePaths):
        pass
      else:
        syncPrintQ("UNEXPECTED number of tiles in section named %s: %i" % (groupName, len(tilePaths)))

    # Await them all
    for future in futures:
      future.get()
  finally:
    exe.shutdown()




def makeMontageGroups(filepaths, to_remove, check):
  """
  ASSUMES montages are 2x2 or just 1 tile
  
  Parameters:
  filepaths: list of all file paths to all image tiles
  to_remove: a set of sections to ignore because they have data inconsistency problems like missing tiles or truncated tiles
  
  Returns groupNames, tileGroups
  """
  # Group files by section, as there could be multiple image tiles per section
  groups = defaultdict(list)
  for filepath in filepaths:
    path, filename = os.path.split(filepath)
    # filepath looks like: /home/albert/zstore1/FIBSEM/Pedro_parker/M07/D13/Merlin-FIBdeSEMAna_23-07-13_083741_0-0-0.dat
    sectionName = filename[0:-9]
    groups[sectionName].append(filepath)

  # Ensure tilePaths are sorted, and check there's 1 or 4 tiles per group
  # and check that tiles are of the same dimensions and file size within each section:
  for groupName_, tilePaths_ in groups.iteritems():
    tilePaths_.sort() # in place
    if 1 == len(tilePaths_) or 4 == len(tilePaths_):
      if not check:
        continue
      # Check that all tiles have the same dimensions and the same file size
      widths = []
      heights = []
      fileSizes = []
      for tilePath in tilePaths_:
        try:
          header = readFIBSEMHeader(tilePath)
          if header is None:
            to_remove.add(groupName_)
            print "HEADER: ", type(header)
          else:
            widths.append(header.xRes)
            heights.append(header.yRes)
            fileSizes.append(os.stat(tilePath).st_size)
          #syncPrintQ("tilePath: %s\ndimensions: %i, %i" % (tilePath, header.xRes, header.yRes))
        except:
          syncPrintQ("Failed to read header or file size for:\n" + tilePath, copy_to_stdout=True)
        if 1 == len(set(widths)) and 1 == len(set(heights)) and 1 == len(set(fileSizes)):
          # all tiles are the same
          pass
        else:
          to_remove.add(groupName_)
          syncPrintQ("Inconsistent tile dimensions of file sizes in section:\n%s\n%s" %(groupName_, "\n".join(map(str, izip(widths, heights)))), copy_to_stdout=True)
    else:
      syncPrintQ("WARNING:" + groupName_ + " has " + str(len(tilePaths_)) + " tiles", copy_to_stdout=True)
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

  return groupNames, tileGroups



# Define a virtual CellImg expressing all the montages, one per section
def makeVolume(groupNames, tileGroups, section_width, section_height, overlap, offset, paramsSIFT, paramsRANSAC, csvDir,
           show=True, matrices=None, invert=False, CLAHE_params=None, title=None):
  dimensions = [section_width, section_height]
  volume_dimensions = dimensions + [len(groupNames)]
  cell_dimensions = dimensions + [1]
  pixelType = UnsignedByteType # UnsignedShortType
  primitiveType = PrimitiveType.BYTE #.SHORT
  
  volumeImg = lazyCachedCellImg(SectionLoader(dimensions, groupNames, tileGroups, overlap, offset,
                                              paramsSIFT, paramsRANSAC, csvDir,
                                              matrices=matrices,
                                              invert=invert, CLAHE_params=CLAHE_params,
                                              as8bit=True),
                                volume_dimensions,
                                cell_dimensions,
                                pixelType,
                                primitiveType,
                                maxRefs=64)  # number of threads times number of sections to compare against plus some padding

  # Show the montages as a series of slices in a stack
  if show:
    imp = wrap(volumeImg)
    if title:
      imp.setTitle(title)
    imp.show()
  
  return volumeImg


def makeSliceLoader(groupNames, volumeImg):
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
    matrices.append(array([1, 0, int(m1[2] + 0.5) - m2[2], 0, 1, int(m1[5] + 0.5) - m2[5]], 'd'))



def showAlignedImg(volumeImgAlignedBM, rotate=None):
  """
  rotate: "right" or "left" or None
  """
  # Show the volume using ImgLib2 interpretation of matrices, with subpixel alignment
  def loadImg(volumeImgAlignedBM, index):
    cell = volumeImgAlignedBM.getCells().randomAccess().setPositionAndGet([0, 0, index])
    pixels = cell.getData().getCurrentStorageArray()
    return ArrayImgs.unsignedBytes(pixels, [volumeImg.dimension(0), volumeImg.dimension(1)])

  cropInterval = FinalInterval([section_width, section_height])
  cellImg, cellGet = makeImg(range(len(groupNames)), properties["pixelType"],
                             partial(loadImg, volumeImgAlignedBM), properties["img_dimensions"],
                             matricesBM, cropInterval, properties.get('preload', 0))


  if rotate:
    # By 90 or -90 degrees
    a, b = (0, 1) if "right" == rotate else (1, 0)
    img = Views.rotate(cellImg, a, b) # the 0 and 1 are the two axis (dimensions) of reference, e.g., pux X (the 0) into Y (the 1).

  imp = IL.wrap(img, properties.get("name", "") + " aligned subpixel")
  imp.show()
  # Ensure cleanup of threads upon closing the window
  addWindowListener(imp.getWindow(), lambda event: cellGet.destroy())
  
  return img, imp
  