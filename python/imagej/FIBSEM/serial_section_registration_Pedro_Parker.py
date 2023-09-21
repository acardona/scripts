import sys, os
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.serial2Dregistration import ensureSIFTFeatures
from lib.io import findFilePaths, readFIBSEMHeader, readFIBSEMdat, lazyCachedCellImg
from lib.util import newFixedThreadPool
from lib.ui import wrap
from collections import defaultdict
from mpicbg.imagefeatures import FloatArray2DSIFT
from mpicbg.ij import SIFT # see https://github.com/axtimwalde/mpicbg/blob/master/mpicbg/src/main/java/mpicbg/ij/SIFT.java
from mpicbg.ij.clahe import FastFlat as CLAHE
from java.util import ArrayList
from java.util.concurrent import Callable
from mpicbg.models import ErrorStatistic, TranslationModel2D, TransformMesh, PointMatch, NotEnoughDataPointsException, Tile, TileConfiguration
from jarray import zeros
from net.imglib2 import FinalInterval
from net.imglib2.img.array import ArrayImgs
from net.imglib2.algorithm.math import ImgMath
from net.imglib2.type import PrimitiveType


# Folders
srcDir = "/home/albert/zstore1/FIBSEM/Pedro_parker/"
tgtDir = "/home/albert/zstore1/FIBSEM/Pedro_parker/registration/"
csvDir = "/home/albert/zstore1/FIBSEM/Pedro_parker/registration/csv/"

# TODO ensure tgtDir and csvDir exist

offset = 60 # pixels # TODO not in use: needed? The left margin of each image is severely elastically deformed. Does it matter for SIFT?
overlap = 124 # pixels

section_width = 13000 # pixels, after section-wise montaging
section_height = 13000


# Parameters for SIFT features, in case blockmatching fails due to large translation or image dimension mistmatch
paramsSIFT = FloatArray2DSIFT.Param()
paramsSIFT.steps = 1
paramsSIFT.minOctaveSize = 0 # will be updated in a clone
paramsSIFT.maxOctaveSize = 0 # will be updated in a clone
paramsSIFT.initialSigma = 1.6 # default 1.6
paramsSIFT.fdSize = 8 # default is 4
paramsSIFT.fdBins = 8 # default is 8


# Find all .dat files, as a sorted list
filepaths = findFilePaths(srcDir, ".dat")

# Group files by section, as there could be multiple image tiles per section
groups = defaultdict(list)
for filepath in filepaths:
  path, filename = os.path.split(filepath)
  # filepath looks like: /home/albert/zstore1/FIBSEM/Pedro_parker/M07/D13/Merlin-FIBdeSEMAna_23-07-13_083741_0-0-0.dat
  sectionName = filename[0:-9]
  groups[sectionName].append(filepath)

for groupName, tilePaths in groups.iteritems():
  if 1 == len(tilePaths) or 4 == len(titePaths):
    pass
  else:
    print "WARNING:", groupName, "has", len(tilePaths), "tiles"
  

class MontageSlice2x2(Callable):
  def __init__(self, name, tilePaths, paramsSIFT, csvDir):
    # EXPECTS 4 filepaths with filenames ending in ["_0-0-0.dat", "_0-0-1.dat", "_0-1-0.dat", "_0-1-1.dat"]
    # ASSUMES all tiles have the same dimensions
    self.name = name
    self.tilePaths = list(sorted(tilePaths))
    self.paramsSIFT = paramsSIFT
    self.csvDir = csvDir
    self.params = {"max_sd": 1.5, # max_sd: maximal difference in size (ratio max/min)
                   "max_id": Double.MAX_VALUE), # max_id: maximal distance in image space
                   "rod": 0.9} # rod: ratio of best vs second best
    self.paramsTileConfiguration = {
      "maxAllowedError": 0, # Saalfeld recommends 0
      "maxPlateauwidth": 200, # Like in TrakEM2
      "maxIterations": 1000, # Saalfeld recommends 1000 -- here, 2 iterations (!!) shows the lowest mean and max error for dataset FIBSEM_L1116
      "damp": 1.0, # Saalfeld recommends 1.0, which means no damp
    }
    
  def getFeatures(self, sp, roi):
    sp.setRoi(roi)
    crop = sp.crop()
    paramsSIFT = paramsSIFT.clone()
    paramsSIFT.minOctaveSize = min(sp.getWidth(), sp.getHeight())
    paramsSIFT.maxOctaveSize = max(sp.getWidth(), sp.getHeight())
    ijSIFT = SIFT(FloatArray2DSIFT(paramsSIFT))
    features = ArrayList() # of Feature instances
    ijSIFT.extractFeatures(ip, features)
    return features
    
  def getPointMatches(self, sp0, roi0, sp1, roi1):
    features0 = self.getFeatures(sp0, roi0)
    features1 = self.getFeatures(sp1, roi1)
    model = TranslationModel2D()
    pointMatches = FloatArray2DSIFT.createMatches(features0,
                                                  features1,
                                                  self.params.get("max_sd", 1.5), # max_sd: maximal difference in size (ratio max/min)
                                                  model,
                                                  self.params.get("max_id", Double.MAX_VALUE), # max_id: maximal distance in image space
                                                  self.params.get("rod", 0.9)) # rod: ratio of best vs second best
    return pointmatches

  def connectTiles(self, sps, tiles, i, j, roi0, roi1):
    pointmatches = getPointMatches(sps[i], roi0, sps[j], roi1)
    tiles[i].connect(tiles[j], pointmatches) # reciprocal connection
    
  def loadShortProcessors(self):
    # Load images (TODO: should use FIBSEM_Reader instead)
    return [readFIBSEMdat(filepath, channel_index=0, asImagePlus=True)[0].getProcessor() for filepath in self.tilePaths]

  def getMatrices(self):
    # For each section to montage, for each image tile,
    # extract features from the appropriate ROI along the overlapping edges
    
    # Check if matrices exist already:
    matrices = loadMatrices(self.name, self.csvDir)
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
    tiles = [Tile(TranslationModel2D()) for _ in self.filePaths]
    tc.addTiles(tiles)
    connectTiles(sps, tiles, 0, 1, roiLeft, roiRight)
    connectTiles(sps, tiles, 2, 3, roiLeft, roiRight)
    connectTiles(sps, tiles, 0, 2, roiTop, roiBottom)
    connectTiles(sps, tiles, 1, 3, roiTop, roiBottom)
    tc.fixTile(tiles[0]) # top left tile
    
    # Optimise tile positions
    maxAllowedError = self.paramsTileConfiguration["maxAllowedError"]
    maxPlateauwidth = self.paramsTileConfiguration["maxPlateauwidth"]
    maxIterations   = self.paramsTileConfiguration["maxIterations"]
    damp            = self.paramsTileConfiguration["damp"]
    tc.optimizeSilently(ErrorStatistic(maxPlateauwidth + 1), maxAllowedError, maxIterations, maxPlateauwidth, damp)
    
    # Save transformation matrices
    matrices = []
    for tile in tiles:
      a = zeros(6, 'd')
      tile.getModel().toArray(a)
      matrices.append(array([a[0], a[2], a[4], a[1], a[3], a[5]], 'd'))
    saveMatrices(self.name, matrices, self.csvDir)
    return matrices
  
  def call(self):
    return getMatrices()

  def montagedImg(self, width, height):
    """ Return an ArrayImg representing the montage
        width, height: dimensions of the canvas onto which to insert the tiles.
    """
    matrices = getMatrices()
    sps = self.loadShortProcessors()
    impMontage = ShortProcessor(width, height, None)
    # Start pasting from the end, to bury the bad left edges
    for sp, matrix in reverse(zip(sps, matrices)):
      impMontage.insert(sp, int(matrix[2] + 0.5), int(matrix[5] + 0.5)) # indices 2 and 5 are the X, Y translation
    
    return ArrayImgs.unsignedShorts(impMontage.getPixels(), width, height)


class SectionLoader(CacheLoader):
  """
  A CacheLoader where each cell is a section made from loading and transforming multiple tiles or just one tile
  """
  def __init__(self, dimensions, groups, paramsSIFT, csvDir):
    """
    """
    self.dimensions = dimensions # a list of [width, height] for the canvas onto which draw the image tiles
    self.groups = groups # a list of lists of file paths to .dat files, one per section
    self.paramsSIFT = paramsSIFT
    self.csvDir = csvDir
  
  def get(self, index):
    group = self.groups[index]
    if 4 == len(group):
      img = MontageSlice2x2(groupName, tilePaths, paramsSIFT, csvDir).montagedImg(*self.dimensions)
    elif 1 == len(group):
      img = readFIBSEMdat(group[0], channel_index=0, asImagePlus=False)[0]
      
    if self.dimensions[0] == img.dimension[0] and self.dimensions[1] == img.dimension[1]:
      aimg = img
    else:
      # copy it onto a new canvas
      aimg = ArrayImgs.unsignedShorts(self.dimensions)
      ImgMath.compute(ImgMath.img(img)).into(aimg)
  
    dims = Intervals.dimensionsAsLongArray(aimg)
    return Cell(list(dims) + [1], # cell dimensions
                [0] * aimg.numDimensions() + [index], # position in the grid: 0, 0, 0, Z-index
                aimg.update(None)) # get the underlying DataAccess



# Extract features and a matrix describing a TranslationModel2D for all tiles that need montaging
exe = newFixedThreadPool()

futures = []

# Iterate all sections in order and generate the transformation matrices defining a montage for each section
for groupName in sorted(groups.iterkeys()):
  tilePaths = groups[groupName)
  # EXPECTING 2x2 tiles or 1
  if 4 == len(tilePaths):
    # Montage the tiles: compute a matrix detailing a TranslationModel2D for each tile
    futures.append(MontageSlice2x2(groupName, tilePaths, paramsSIFT, csvDir))
  else if 1 == len(tilePaths):
    futures.append(SingleTileSection(tilePaths[0]))
  else:
    print "UNEXPECTED number of tiles in section named", groupName, ":", len(tilePaths)

# Await them all
for future in futures:
  future.get()


# Define a virtual CellImg expressing all the montages, one per section

dimensions = [section_width, section_height]
volume_dimensions = dimensions + [len(groups)]
cell_dimensions = dimensions + [1]
pixelType = UnsignedShortType
primitiveType = PrimitiveType.SHORT

volumeImg = lazyCachedCellImg(SectionLoader(dimensions, groups, paramsSIFT, csvDir),
                              volume_dimensions,
                              cell_dimensions,
                              pixelType,
                              primitiveType)

# Show the montages as a series of slices in a stack
imp = wrap(volumeImg)
imp.show()

