# Albert Cardona 2019-05-31
#
# A series of scripts to register FIBSEM serial sections.
# ASSUMES there is only one single image per section.
# ASSUMES all images have the same dimensions and pixel type.
# 
# This program is similar to the plugin Register Virtual Stack Slices
# but uses more efficient and densely distributed features,
# and also matches sections beyond the direct adjacent for best stability
# as demonstrated for elastic registration in Saalfeld et al. 2012 Nat Methods.
# 
# The program also offers functions to export for CATMAID.
#
# 1. Extract blockmatching features for every section.
# 2. Register each section to its adjacent, 2nd adjacent, 3rd adjacent ...
# 3. Jointly optimize the pose of every section.
# 4. Export volume for CATMAID.

import os, sys, traceback
sys.path.append("/groups/cardona/home/cardonaa/lab/scripts/python/imagej/IsoView-GCaMP/")
from os.path import basename
from mpicbg.ij.blockmatching import BlockMatching
from mpicbg.models import ErrorStatistic, TranslationModel2D, TransformMesh, PointMatch, NotEnoughDataPointsException, Tile, TileConfiguration
from mpicbg.imagefeatures import FloatArray2DSIFT
from mpicbg.ij.util import Filter, Util
from mpicbg.ij import SIFT
from java.util import ArrayList
from java.lang import Double
from lib.io import readUnsignedShorts, read2DImageROI
from lib.util import SoftMemoize, newFixedThreadPool, Task, ParallelTasks, numCPUs, nativeArray, syncPrint, LRUCache
from lib.features import savePointMatches, loadPointMatches
from lib.registration import loadMatrices, saveMatrices
from lib.ui import showStack, wrap
from net.imglib2.type.numeric.integer import UnsignedShortType
from net.imglib2.view import Views
from ij.process import FloatProcessor
from ij import IJ
from net.imglib2.img.io.proxyaccess import ShortAccessProxy
from net.imglib2.img.cell import LazyCellImg, Cell, CellGrid
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.array import ArrayImgs
from net.imglib2.img import ImgView
from net.imglib2.util import ImgUtil, Intervals
from net.imglib2.realtransform import RealViews, AffineTransform2D
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2 import FinalInterval
from java.awt.event import KeyAdapter, KeyEvent
from java.lang.ref import SoftReference
from jarray import zeros
from java.util import Collections

srcDir = "/groups/cardona/cardonalab/FIBSEM_L1116/" # MUST have an ending slash
tgtDir = "/groups/cardona/cardonalab/Albert/FIBSEM_L1116/"

filepaths = [os.path.join(srcDir, filepath)
             for filepath in sorted(os.listdir(srcDir))
             if filepath.endswith("InLens_raw.tif")]

# Image properties: ASSUMES all images have the same properties
dimensions = [16875, 18125]
interval = None #[[4096, 4096],
                # [12288 -1, 12288 -1]] # to open only that, or None
pixelType = UnsignedShortType
proxyType = ShortAccessProxy
header = 0

# Parameters for blockmatching
params = {
 'scale': 0.1, # 10%
 'meshResolution': 10, # 10 x 10 points = 100 point matches maximum
 'minR': 0.1, # min PMCC (Pearson product-moment correlation coefficient)
 'rod': 0.9, # max second best r / best r
 'maxCurvature': 1000.0, # default is 10
 'searchRadius': 100, # a low value: we expect little translation
 'blockRadius': 200 # small, yet enough
}

# Parameters for computing the transformation models
paramsTileConfiguration = {
  "n_adjacent": 3, # minimum of 1; Number of adjacent sections to pair up
  "maxAllowedError": 0, # Saalfeld recommends 0
  "maxPlateauwidth": 200, # Like in TrakEM2
  "maxIterations": 1000, # Saalfeld recommends 1000
  "damp": 1.0, # Saalfeld recommends 1.0, which means no damp
}

# Parameters for SIFT features, in case blockmatching fails due to large translation
paramsSIFT = FloatArray2DSIFT.Param()
paramsSIFT.fdSize = 8 # default is 4
paramsSIFT.fdBins = 8 # default is 8
paramsSIFT.maxOctaveSize = int(max(1024, dimensions[0] * params["scale"]))
paramsSIFT.steps = 3
paramsSIFT.minOctaveSize = int(paramsSIFT.maxOctaveSize / pow(2, paramsSIFT.steps))
paramsSIFT.initialSigma = 1.6 # default 1.6


# Ensure target directories exist
if not os.path.exists(tgtDir):
  os.mkdir(tgtDir)

csvDir = os.path.join(tgtDir, "csvs")

if not os.path.exists(csvDir):
  os.mkdir(csvDir)

def loadImp(filepath):
  # Images are TIFF with bit pack compression: can't byte-read array
  syncPrint("Loading image " + filepath)
  return IJ.openImage(filepath)

def loadFloatProcessor(filepath, scale=True):
  try:
    fp = loadImp(filepath).getProcessor().convertToFloatProcessor()
    # Preprocess images: Gaussian-blur to scale down, then normalize contrast
    if scale:
      fp = Filter.createDownsampled(fp, params["scale"], 0.5, 1.6)
      Util.normalizeContrast(fp)
    return fp
  except:
    syncPrint(sys.exc_info())

loadImpMem = SoftMemoize(loadImp, maxsize=128)
loadFPMem = SoftMemoize(loadFloatProcessor, maxsize=64)


def extractBlockMatches(filepath1, filepath2, params, csvDir, exeload, load=loadFPMem):
  """
  filepath1: the file path to an image of a section.
  filepath2: the file path to an image of another section.
  params: dictionary of parameters necessary for BlockMatching.
  exeload: an ExecutorService for parallel loading of image files.
  load: a function that knows how to load the image from the filepath.
  """

  # Skip if pointmatches CSV file exists already:
  csvpath = os.path.join(csvDir, basename(filepath1) + '.' + basename(filepath2) + ".pointmatches.csv")
  if os.path.exists(csvpath):
    return

  try:

    # Load files in parallel
    futures = [exeload.submit(Task(load, filepath1)),
               exeload.submit(Task(load, filepath2))]
  
    # Define points from the mesh
    sourcePoints = ArrayList()
    mesh = TransformMesh(params["meshResolution"], dimensions[0], dimensions[1])
    PointMatch.sourcePoints( mesh.getVA().keySet(), sourcePoints )
    # List to fill
    sourceMatches = ArrayList() # of PointMatch from filepath1 to filepath2

    syncPrint("Extracting block matches for \n S: " + filepath1 + "\n T: " + filepath2 + "\n  with " + str(sourcePoints.size()) + " mesh sourcePoints.")

    BlockMatching.matchByMaximalPMCCFromPreScaledImages(
              futures[0].get(), # FloatProcessor
              futures[1].get(), # FloatProcessor
              params["scale"], # float
              params["blockRadius"], # X
              params["blockRadius"], # Y
              params["searchRadius"], # X
              params["searchRadius"], # Y
              params["minR"], # float
              params["rod"], # float
              params["maxCurvature"], # float
              sourcePoints,
              sourceMatches)

    # At least some should match to accept the translation
    if len(sourceMatches) < max(20, len(sourcePoints) / 5) / 2:
      syncPrint("Found only %i blockmatching pointmatches (from %i source points)" % (len(sourceMatches), len(sourcePoints)))
      syncPrint("... therefore invoking SIFT pointmatching for:\n  S: " + basename(filepath1) + "\n  T: " + basename(filepath2))
      # Can fail if there is a shift larger than the searchRadius
      # Try SIFT features, which are location independent
      #
      # Images are now scaled: load originals
      futures = [exeload.submit(Task(loadFloatProcessor, filepath1, scale=False)),
                 exeload.submit(Task(loadFloatProcessor, filepath2, scale=False))]
      ijSIFT = SIFT(FloatArray2DSIFT(paramsSIFT))
      features1 = ArrayList() # of Point instances
      ijSIFT.extractFeatures(futures[0].get(), features1)
      features2 = ArrayList() # of Point instances
      ijSIFT.extractFeatures(futures[1].get(), features2)
      # Vector of PointMatch instances
      sourceMatches = FloatArray2DSIFT.createMatches(features1,
                                                     features2,
                                                     1.5, # max_sd
                                                     TranslationModel2D(),
                                                     Double.MAX_VALUE,
                                                     params["rod"]) # rod: ratio of best vs second best

    # Store pointmatches
    savePointMatches(os.path.basename(filepath1),
                     os.path.basename(filepath2),
                     sourceMatches,
                     csvDir,
                     params)
  except:
    syncPrint(sys.exc_info())
    syncPrint("".join(traceback.format_exception()), out="stderr")


def pointmatchingTasks(filepaths, csvDir, params, n_adjacent, exeload):
  for i in xrange(len(filepaths) - n_adjacent):
    for inc in xrange(1, n_adjacent + 1):
      syncPrint("Preparing extractBlockMatches for: \n  1: %s\n  2: %s" % (filepaths[i], filepaths[i+inc]))
      yield Task(extractBlockMatches, filepaths[i], filepaths[i + inc], params, csvDir, exeload)


def ensurePointMatches(filepaths, csvDir, params, n_adjacent):
  """ If a pointmatches csv file doesn't exist, will create it. """
  w = ParallelTasks("ensurePointMatches", exe=newFixedThreadPool(4))
  exeload = newFixedThreadPool()
  try:
    count = 1
    for result in w.chunkConsume(numCPUs() * 2, pointmatchingTasks(filepaths, csvDir, params, n_adjacent, exeload)):
      syncPrint("Completed %i/%i" % (count, len(filepaths) * n_adjacent))
      count += 1
    syncPrint("Awaiting all remaining pointmatching tasks to finish.")
    w.awaitAll()
    syncPrint("Finished all pointmatching tasks.")
  except:
    print sys.exc_info()
  finally:
    exeload.shutdown()
    w.destroy()

# When done, optimize tile pose globally
def makeLinkedTiles(filepaths, csvDir, params, n_adjacent):
  ensurePointMatches(filepaths, csvDir, params, n_adjacent)
  tiles = [Tile(TranslationModel2D()) for _ in filepaths]
  for i in xrange(len(filepaths) - n_adjacent):
    for inc in xrange(1, n_adjacent + 1):
      pointmatches = loadPointMatches(os.path.basename(filepaths[i]),
                                      os.path.basename(filepaths[i + inc]),
                                      csvDir,
                                      params)
      tiles[i].connect(tiles[i + inc], pointmatches) # reciprocal connection
  return tiles


def align(filepaths, csvDir, params, paramsTileConfiguration):
  name = "matrices"
  matrices = loadMatrices(name, csvDir)
  if matrices:
    return matrices
  
  # Optimize
  tiles = makeLinkedTiles(filepaths, csvDir, params, paramsTileConfiguration["n_adjacent"])
  tc = TileConfiguration()
  tc.addTiles(tiles)
  tc.fixTile(tiles[len(tiles) / 2]) # middle tile
  
  maxAllowedError = paramsTileConfiguration["maxAllowedError"]
  maxPlateauwidth = paramsTileConfiguration["maxPlateauwidth"]
  maxIterations = paramsTileConfiguration["maxIterations"]
  damp = paramsTileConfiguration["damp"]
  tc.optimizeSilentlyConcurrent(ErrorStatistic(maxPlateauwidth + 1), maxAllowedError,
                                maxIterations, maxPlateauwidth, damp)

  # TODO problem: can fail when there are 0 inliers

  # Return model matrices as double[] arrays with 6 values
  matrices = []
  for tile in tiles:
    a = nativeArray('d', [2, 3])
    tile.getModel().toMatrix(a) # Can't use model.toArray: different order of elements
    matrices.append(a[0] + a[1]) # Concat: flatten to 1-dimensional array

  saveMatrices(name, matrices, csvDir) # TODO check: saving correctly, now that it's 2D?
  
  return matrices


class TranslatedSectionGet(LazyCellImg.Get):
  def __init__(self, filepaths, matrices, cell_dimensions, interval):
    self.filepaths = filepaths
    self.matrices = matrices
    self.cell_dimensions = cell_dimensions # x,y must match dims of interval
    self.interval = interval # when smaller than the image, will crop
    self.cache = self.makeCache()

  def makeCache(self):
    return Collections.synchronizedMap(LRUCache(1000, eldestFn=lambda ref: ref.clear()))

  def translate(self, dx, dy):
    a = zeros(2, 'l')
    self.interval.min(a)
    self.interval = FinalInterval([a[0] + dx, a[1] + dy], [self.cell_dimensions[0] -1, self.cell_dimensions[1] - 1])
    self.cache = self.makeCache()

  def get(self, index):
    ref = self.cache.get(index)
    if ref:
      cell = ref.get()
      if cell:
        return cell
    cell = self.makeCell(index)
    self.cache[index] = SoftReference(cell)
    return cell

  def makeCell(self, index):
    syncPrint("Loading image at index %i or getting it from the cache" % index)
    imp = loadImpMem(self.filepaths[index])
    img = ArrayImgs.unsignedShorts(imp.getProcessor().getPixels(), [imp.getWidth(), imp.getHeight()])
    self.aimg = ArrayImgs.unsignedShorts(Intervals.dimensionsAsLongArray(self.interval))
    matrix = self.matrices[index]
    syncPrint("Matrix:" + str(matrix))
    """
    if matrix[0] == 1.0 and matrix[1] == 0.0 and matrix[3] == 0.0 and matrix[4] == 1.0:
      syncPrint("Translation-only view")
      # Translation-only
      dx, dy = int(matrix[2] + 0.5), int(matrix[5] + 0.5)
      imgT = Views.zeroMin(Views.interval(Views.translate(Views.extendZero(img), [dx, dy]), self.interval))
    else:
      syncPrint("Affine view")
      # Affine
      affine = AffineTransform2D()
      affine.set(matrix)
      imgI = Views.interpolate(Views.extendZero(img), NLinearInterpolatorFactory())
      imgA = RealViews.transform(imgI, affine)
      imgT = Views.zeroMin(Views.interval(imgA, self.interval))
    """
    # Always interpolate:
    syncPrint("Affine view")
    # Affine
    affine = AffineTransform2D()
    affine.set(matrix)
    imgI = Views.interpolate(Views.extendZero(img), NLinearInterpolatorFactory())
    imgA = RealViews.transform(imgI, affine)
    imgT = Views.zeroMin(Views.interval(imgA, self.interval))
    #
    syncPrint("Copying transformed view into ArrayImg")
    ImgUtil.copy(ImgView.wrap(imgT, self.aimg.factory()),
                 self.aimg,
                 max(1, numCPUs() -1))
    syncPrint("Returning Cell")
    return Cell(self.cell_dimensions,
               [0, 0, index],
               self.aimg.update(None))


class SourcePanning(KeyAdapter):
  def __init__(self, cellGet, imp, shift=100, alt=10):
    """
      cellGet: the LazyCellImg.Get onto which to set a translation of the source pixels
      imp: the ImagePlus to update
      shift: defaults to 100, when the shift key is down, move by 100 pixels
      alt: defaults to 10, when the alt key is down, move by 10 pixels
      If both shift and alt are down, move by shift*alt = 1000 pixels by default.
    """
    self.cellGet = cellGet
    self.delta = {KeyEvent.VK_UP: (0, -1),
                  KeyEvent.VK_DOWN: (0, 1),
                  KeyEvent.VK_RIGHT: (1, 0),
                  KeyEvent.VK_LEFT: (-1, 0)}
    self.shift = shift
    self.alt = alt
    self.imp = imp
  def keyPressed(self, event):
    dx, dy = self.delta.get(event.getKeyCode(), (0, 0))
    if dx + dy == 0:
      return
    if event.isShiftDown():
      dx *= self.shift
      dy *= self.shift
    if event.isAltDown():
      dx *= self.alt
      dy *= self.alt
    self.cellGet.translate(dx, dy)
    self.imp.updateAndDraw()
    event.consume()


def viewAligned(filepaths, csvDir, params, paramsTileConfiguration, cropInterval):
  matrices = align(filepaths, csvDir, params, paramsTileConfiguration)
  dims = Intervals.dimensionsAsLongArray(cropInterval)
  voldims = [dims[0],
             dims[1],
             len(filepaths)]
  cell_dimensions = [dims[0],
                     dims[1],
                     1]
  grid = CellGrid(voldims, cell_dimensions)
  cellGet = TranslatedSectionGet(filepaths, matrices, cell_dimensions, cropInterval)
  cellImg = LazyCellImg(grid, pixelType(), cellGet)
  print cellImg
  comp = showStack(cellImg, title=srcDir.split('/')[-2], proper=False)
  # Add the SourcePanning KeyListener as the first one
  canvas = comp.getWindow().getCanvas()
  kls = canvas.getKeyListeners()
  for kl in kls:
    canvas.removeKeyListener(kl)
  canvas.addKeyListener(SourcePanning(cellGet, comp))
  for kl in kls:
    canvas.addKeyListener(kl)



# Show only a cropped middle area
x0 = 3 * dimensions[0] / 8
y0 = 3 * dimensions[1] / 8
x1 = x0 + 2 * dimensions[0] / 8 -1
y1 = y0 + 2 * dimensions[1] / 8 -1
print "Crop to: x=%i y=%i width=%i height=%i" % (x0, y0, x1 - x0 + 1, y1 - y0 + 1)
viewAligned(filepaths, csvDir, params, paramsTileConfiguration,
            FinalInterval([x0, y0], [x1, y1]))




