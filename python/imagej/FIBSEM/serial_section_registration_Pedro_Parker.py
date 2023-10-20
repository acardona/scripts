from __future__ import with_statement
import sys, os
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.registration import saveMatrices, loadMatrices
from lib.serial2Dregistration import ensureSIFTFeatures
from lib.io import loadFilePaths, readFIBSEMHeader, readFIBSEMdat, lazyCachedCellImg
from lib.util import newFixedThreadPool
from lib.ui import wrap
from collections import defaultdict
from mpicbg.imagefeatures import FloatArray2DSIFT
from mpicbg.ij import SIFT # see https://github.com/axtimwalde/mpicbg/blob/master/mpicbg/src/main/java/mpicbg/ij/SIFT.java
from mpicbg.ij.clahe import FastFlat as CLAHE
from java.util import ArrayList
from java.util.concurrent import Callable
from java.lang import Double
from mpicbg.models import ErrorStatistic, TranslationModel2D, TransformMesh, PointMatch, NotEnoughDataPointsException, Tile, TileConfiguration
from jarray import zeros, array
from net.imglib2 import FinalInterval
from net.imglib2.img.array import ArrayImgs
from net.imglib2.algorithm.math import ImgMath
from net.imglib2.type import PrimitiveType
from net.imglib2.cache import CacheLoader
from net.imglib2.type.numeric.integer import UnsignedShortType
from net.imglib2.img.cell import Cell
from ij.gui import Roi
from ij.process import ShortProcessor
from itertools import izip


# Folders
srcDir = "/home/albert/zstore1/FIBSEM/Pedro_parker/"
tgtDir = "/home/albert/zstore1/FIBSEM/Pedro_parker/registration-Albert/"
csvDir = "/home/albert/zstore1/FIBSEM/Pedro_parker/registration-Albert/csv/"

# TODO ensure tgtDir and csvDir exist

offset = 60 # pixels # TODO not in use: needed? The left margin of each image is severely elastically deformed. Does it matter for SIFT?
overlap = 124 # pixels

section_width = 26000 # pixels, after section-wise montaging
section_height = 26000


# Parameters for SIFT features, in case blockmatching fails due to large translation or image dimension mistmatch
paramsSIFT = FloatArray2DSIFT.Param()
paramsSIFT.steps = 1
paramsSIFT.minOctaveSize = 0 # will be updated in a clone
paramsSIFT.maxOctaveSize = 0 # will be updated in a clone
paramsSIFT.initialSigma = 1.6 # default 1.6
paramsSIFT.fdSize = 8 # default is 4
paramsSIFT.fdBins = 8 # default is 8
    

# Find all .dat files, as a sorted list
filepaths = loadFilePaths(srcDir, ".dat", csvDir, "imagefilepaths")


# Group files by section, as there could be multiple image tiles per section
groups = defaultdict(list)
for filepath in filepaths:
  path, filename = os.path.split(filepath)
  # filepath looks like: /home/albert/zstore1/FIBSEM/Pedro_parker/M07/D13/Merlin-FIBdeSEMAna_23-07-13_083741_0-0-0.dat
  sectionName = filename[0:-9]
  groups[sectionName].append(filepath)

for groupName_, tilePaths_ in groups.iteritems():
  if 1 == len(tilePaths_) or 4 == len(tilePaths_):
    pass
  else:
    print "WARNING:", groupName_, "has", len(tilePaths_), "tiles"
  

class MontageSlice2x2(Callable):
  def __init__(self, groupName, tilePaths, paramsSIFT, csvDir):
    # EXPECTS 4 filepaths with filenames ending in ["_0-0-0.dat", "_0-0-1.dat", "_0-1-0.dat", "_0-1-1.dat"]
    # ASSUMES all tiles have the same dimensions
    self.groupName = groupName
    self.tilePaths = list(sorted(tilePaths))
    self.paramsSIFT = paramsSIFT
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
    
  def getFeatures(self, sp, roi):
    sp.setRoi(roi)
    sp = sp.crop()
    paramsSIFT = self.paramsSIFT.clone()
    paramsSIFT.minOctaveSize = min(sp.getWidth(), sp.getHeight())
    paramsSIFT.maxOctaveSize = max(sp.getWidth(), sp.getHeight())
    ijSIFT = SIFT(FloatArray2DSIFT(paramsSIFT))
    features = ArrayList() # of Feature instances
    ijSIFT.extractFeatures(sp, features)
    return features
    
  def getPointMatches(self, sp0, roi0, sp1, roi1):
    features0 = self.getFeatures(sp0, roi0)
    features1 = self.getFeatures(sp1, roi1)
    model = TranslationModel2D()
    pointmatches = FloatArray2DSIFT.createMatches(features0,
                                                  features1,
                                                  self.params.get("max_sd", 1.5), # max_sd: maximal difference in size (ratio max/min)
                                                  model,
                                                  self.params.get("max_id", Double.MAX_VALUE), # max_id: maximal distance in image space
                                                  self.params.get("rod", 0.9)) # rod: ratio of best vs second best
    return pointmatches

  def connectTiles(self, sps, tiles, i, j, roi0, roi1):
    pointmatches = self.getPointMatches(sps[i], roi0, sps[j], roi1)
    tiles[i].connect(tiles[j], pointmatches) # reciprocal connection
    
  def loadShortProcessors(self):
    for filepath in self.tilePaths:
      print "#%s#" % filepath
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
    
    # Define 4 ROIs:
    # left-right
    roiLeft = Roi(width - overlap, 0, overlap, height) # right edge, for tile 0-0-0  (and 0-1-0)
    roiRight = Roi(0, 0, overlap, height)              # left edge,  for tile 0-0-1  (and 0-1-1)
    # top-bottom
    roiTop = Roi(0, height - overlap, width, overlap) # bottom edge, for tile 0-0-0  (and 0-0-1)
    roiBottom = Roi(0, 0, width, overlap)             # top edge,    for tile 0-1-0  (and 0-1-1)
    
    # Declare tile links
    tc = TileConfiguration()
    tiles = [Tile(TranslationModel2D()) for _ in self.tilePaths]
    tc.addTiles(tiles)
    self.connectTiles(sps, tiles, 0, 1, roiLeft, roiRight)
    self.connectTiles(sps, tiles, 2, 3, roiLeft, roiRight)
    self.connectTiles(sps, tiles, 0, 2, roiTop, roiBottom)
    self.connectTiles(sps, tiles, 1, 3, roiTop, roiBottom)
    tc.fixTile(tiles[0]) # top left tile
    
    # Optimise tile positions
    maxAllowedError = self.paramsTileConfiguration["maxAllowedError"]
    maxPlateauwidth = self.paramsTileConfiguration["maxPlateauwidth"]
    maxIterations   = self.paramsTileConfiguration["maxIterations"]
    damp            = self.paramsTileConfiguration["damp"]
    tc.optimizeSilently(ErrorStatistic(maxPlateauwidth + 1), maxAllowedError, maxIterations, maxPlateauwidth, damp)
    
    # Save transformation matrices
    matrices = []
    corrections = [[0, 0], # top-left tile is fixed
                   [width - overlap, 0], # top-right tile
                   [0, height - overlap], # bottom-left tile
                   [width - overlap, height - overlap]] # bottom-right tile
    for i, tile in enumerate(tiles):
      a = zeros(6, 'd')
      tile.getModel().toArray(a)
      matrices.append(array([a[0], a[2], a[4] + corrections[i][0], a[1], a[3], a[5] + corrections[i][1]], 'd'))
    saveMatrices(self.groupName, matrices, self.csvDir)
    return matrices
  
  def call(self):
    return self.getMatrices()

  def montagedImg(self, width, height):
    """ Return an ArrayImg representing the montage
        width, height: dimensions of the canvas onto which to insert the tiles.
    """
    matrices = self.getMatrices()
    sps = self.loadShortProcessors()
    impMontage = ShortProcessor(width, height)
    # Start pasting from the end, to bury the bad left edges
    for sp, matrix in reversed(zip(sps, matrices)):
      impMontage.insert(sp, int(matrix[2] + 0.5), int(matrix[5] + 0.5)) # indices 2 and 5 are the X, Y translation
    
    return ArrayImgs.unsignedShorts(impMontage.getPixels(), width, height)


class SectionLoader(CacheLoader):
  """
  A CacheLoader where each cell is a section made from loading and transforming multiple tiles or just one tile
  """
  def __init__(self, dimensions, groupNames, tileGroups, paramsSIFT, csvDir):
    """
    """
    self.dimensions = dimensions # a list of [width, height] for the canvas onto which draw the image tiles
    self.groupNames = groupNames # list of names of each group, used to find its montage CSV if any
    self.tileGroups = tileGroups # a list of lists of file paths to .dat files, one per section
    self.paramsSIFT = paramsSIFT
    self.csvDir = csvDir
  
  def get(self, index):
    groupName = self.groupNames[index]
    tilePaths = self.tileGroups[index]
    if 4 == len(tilePaths):
      img = MontageSlice2x2(groupName, tilePaths, paramsSIFT, csvDir).montagedImg(*self.dimensions)
    elif 1 == len(group):
      img = readFIBSEMdat(tilePaths[0], channel_index=0, asImagePlus=False)[0]
    else:
      # return empty Cell
      print "WARNING: number of tiles isn't 4 or 1"
      return Cell(self.dimensions + [1],
                  [0, 0, index],
                  ArrayImgs.unsignedShorts(self.dimensions).update(None)) # TODO this should be a constant DataAccess
      
    if self.dimensions[0] == img.dimension(0) and self.dimensions[1] == img.dimension(1):
      aimg = img
    else:
      # copy it onto a new canvas
      aimg = ArrayImgs.unsignedShorts(self.dimensions)
      ImgMath.compute(ImgMath.img(img)).into(aimg)
  
    return Cell(self.dimensions + [1], # cell dimensions
                [0] * aimg.numDimensions() + [index], # position in the grid: 0, 0, 0, Z-index
                aimg.update(None)) # get the underlying DataAccess


def ensureMontages2x2(groupNames, tileGroups, overlap, offset, paramsSIFT, csvDir):
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
  exe = newFixedThreadPool()
  try:

    futures = []

    # Iterate all sections in order and generate the transformation matrices defining a montage for each section
    for groupName, tilePaths in izip(groupNames, tileGroups):
      # EXPECTING 2x2 tiles or 1
      if 4 == len(tilePaths):
        # Montage the tiles: compute a matrix detailing a TranslationModel2D for each tile
        futures.append(exe.submit(MontageSlice2x2(groupName, tilePaths, paramsSIFT, csvDir)))
      elif 1 == len(tilePaths):
        pass
      else:
        print "UNEXPECTED number of tiles in section named", groupName, ":", len(tilePaths)

    # Await them all
    for future in futures:
      future.get()
  finally:
    exe.shutdown()


# Sort groups by key
keys = groups.keys()
groupNames = []
tileGroups = []
for groupName in sorted(groups):
  groupNames.append(groupName)
  tileGroups.append(groups[groupName])


# DEBUG: just one section
groupNames = [groupNames[1000]]
tileGroups = [tileGroups[1000]]


# Montage all sections
ensureMontages2x2(groupNames, tileGroups, overlap, offset, paramsSIFT, csvDir)

# Define a virtual CellImg expressing all the montages, one per section

dimensions = [section_width, section_height]
volume_dimensions = dimensions + [len(groupNames)]
cell_dimensions = dimensions + [1]
pixelType = UnsignedShortType
primitiveType = PrimitiveType.SHORT

volumeImg = lazyCachedCellImg(SectionLoader(dimensions, groupNames, tileGroups, paramsSIFT, csvDir),
                              volume_dimensions,
                              cell_dimensions,
                              pixelType,
                              primitiveType)

# Show the montages as a series of slices in a stack
imp = wrap(volumeImg)
imp.show()

# TODO: align sections with blockmatching




