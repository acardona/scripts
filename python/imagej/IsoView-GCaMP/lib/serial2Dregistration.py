# Albert Cardona 2019-05-31
#
# A series of functions to register and visualize FIBSEM serial sections.
# ASSUMES there is only one single image per section.
# ASSUMES all images have the same dimensions and pixel type.
# 
# This program is similar to the plugin Register Virtual Stack Slices
# but uses more efficient and densely distributed features,
# and also matches sections beyond the direct adjacent for best stability
# as demonstrated for elastic registration in Saalfeld et al. 2012 Nat Methods.
# 
# The program also offers functions to export as N5 for Paintera, CATMAID, and others.
#
# 1. Extract blockmatching features for every section.
# 2. Register each section to its adjacent, 2nd adjacent, 3rd adjacent ...
# 3. Jointly optimize the pose of every section.

import os, sys, traceback
from os.path import basename
from mpicbg.ij.blockmatching import BlockMatching
from mpicbg.models import ErrorStatistic, TranslationModel2D, TransformMesh, PointMatch, NotEnoughDataPointsException, Tile, TileConfiguration
from mpicbg.imagefeatures import FloatArray2DSIFT
from mpicbg.ij.util import Filter, Util
from mpicbg.ij import SIFT # see https://github.com/axtimwalde/mpicbg/blob/master/mpicbg/src/main/java/mpicbg/ij/SIFT.java
from mpicbg.ij.clahe import FastFlat as CLAHE
from java.util import ArrayList
from java.lang import Double, System
from net.imglib2.type.numeric.integer import UnsignedShortType
from net.imglib2.view import Views
from ij.process import FloatProcessor
from ij import IJ, ImageListener, ImagePlus
from net.imglib2.img.io.proxyaccess import ShortAccessProxy
from net.imglib2.img.cell import LazyCellImg, Cell, CellGrid
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.array import ArrayImgs
from net.imglib2.img import ImgView
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.util import ImgUtil, Intervals
from net.imglib2.realtransform import RealViews, AffineTransform2D
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2 import FinalInterval
from net.imglib2.type.PrimitiveType import BYTE
from net.imglib2.converter import RealUnsignedByteConverter
from java.awt.event import KeyAdapter, KeyEvent
from jarray import zeros, array
from functools import partial
from java.util.concurrent import Executors, TimeUnit
# From lib
from io import readUnsignedShorts, read2DImageROI, ImageJLoader, lazyCachedCellImg, SectionCellLoader, writeN5, serialize, deserialize
from util import SoftMemoize, newFixedThreadPool, Task, RunTask, TimeItTask, ParallelTasks, numCPUs, nativeArray, syncPrint, syncPrintQ
from features import savePointMatches, loadPointMatches, saveFeatures, loadFeatures
from registration import loadMatrices, saveMatrices
from ui import showStack, wrap
from converter import convert
from pixels import autoAdjust


def loadImp(filepath):
  """ Returns an ImagePlus """
  syncPrintQ("Loading image " + filepath)
  return IJ.openImage(filepath)

def loadUnsignedShort(filepath, invert=True, CLAHE_params=None):
  """ Returns an ImgLib2 ArrayImg """
  imp = loadImp(filepath)
  if invert:
    imp.getProcessor().invert()
  if CLAHE_params is not None:
    blockRadius, n_bins, slope = CLAHE_params
    CLAHE.run(imp, blockRadius, n_bins, slope, None)
  return ArrayImgs.unsignedShorts(imp.getProcessor().getPixels(), [imp.getWidth(), imp.getHeight()])

def loadFloatProcessor(filepath, params, paramsSIFT, scale=True):
  try:
    fp = loadImp(filepath).getProcessor().convertToFloatProcessor()
    # Preprocess images: Gaussian-blur to scale down, then normalize contrast
    if scale:
      fp = Filter.createDownsampled(fp, params["scale"], 0.5, paramsSIFT.initialSigma)
      Util.normalizeContrast(fp) # TODO should be outside the if clause?
    return fp
  except:
    syncPrintQ(sys.exc_info())

  

def setupImageLoader(loader=loadImp):
  """ Specify which function can read the image files into an ImagePlus.
      Defaults to loadImp using ImageJ's IJ.openImage. """
  global loadImp
  loadImp = loader


def extractBlockMatches(filepath1, filepath2, params, paramsSIFT, properties, csvDir, exeload, load):
  """
  filepath1: the file path to an image of a section.
  filepath2: the file path to an image of another section.
  params: dictionary of parameters necessary for BlockMatching.
  exeload: an ExecutorService for parallel loading of image files.
  load: a function that knows how to load the image from the filepath.

  return False if the CSV file already exists, True if it has to be computed.
  """

  # Skip if pointmatches CSV file exists already:
  csvpath = os.path.join(csvDir, basename(filepath1) + '.' + basename(filepath2) + ".pointmatches.csv")
  if os.path.exists(csvpath):
    return False

  try:

    # Load files in parallel
    futures = [exeload.submit(Task(load, filepath1)),
               exeload.submit(Task(load, filepath2))]

    fp1 = futures[0].get() # FloatProcessor, already Gaussian-blurred, contrast-corrected and scaled!
    fp2 = futures[1].get() # FloatProcessor, idem
  
    # Define points from the mesh
    sourcePoints = ArrayList()
    # List to fill
    sourceMatches = ArrayList() # of PointMatch from filepath1 to filepath2

    # Don't use blockmatching if the dimensions are different
    use_blockmatching = fp1.getWidth() == fp2.getWidth() and fp1.getHeight() == fp2.getHeight()

    if use_blockmatching:
      # Fill the sourcePoints
      mesh = TransformMesh(params["meshResolution"], fp1.width, fp1.height)
      PointMatch.sourcePoints( mesh.getVA().keySet(), sourcePoints )
      syncPrintQ("Extracting block matches for \n S: " + filepath1 + "\n T: " + filepath2 + "\n  with " + str(sourcePoints.size()) + " mesh sourcePoints.")
      # Run
      BlockMatching.matchByMaximalPMCCFromPreScaledImages(
                fp1,
                fp2,
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
      syncPrintQ("Found only %i blockmatching pointmatches (from %i source points)" % (len(sourceMatches), len(sourcePoints)))
      syncPrintQ("... therefore invoking SIFT pointmatching for:\n  S: " + basename(filepath1) + "\n  T: " + basename(filepath2))
      # Can fail if there is a shift larger than the searchRadius
      # Try SIFT features, which are location independent
      #
      # Images are now scaled: load originals
      futures = [exeload.submit(Task(loadFloatProcessor, filepath1, params, paramsSIFT, scale=False)),
                 exeload.submit(Task(loadFloatProcessor, filepath2, params, paramsSIFT, scale=False))]

      fp1 = futures[0].get() # FloatProcessor, original
      fp2 = futures[1].get() # FloatProcessor, original

      # Images can be of different size: scale them the same way
      area1 = fp1.width * fp1.height
      area2 = fp2.width * fp2.height
      
      if area1 == area2:
        paramsSIFT1 = paramsSIFT.clone()
        paramsSIFT1.maxOctaveSize = int(max(properties.get("SIFT_max_size", 2048), fp1.width * params["scale"]))
        paramsSIFT1.minOctaveSize = int(paramsSIFT1.maxOctaveSize / pow(2, paramsSIFT1.steps))
        paramsSIFT2 = paramsSIFT1
      else:
        bigger, smaller = (fp1, fp2) if area1 > area2 else (fp2, fp1)
        target_width_bigger = int(max(1024, bigger.width * params["scale"]))
        if 1024 == target_width_bigger:
          target_width_smaller = int(1024 * float(smaller.width) / bigger.width)
        else:
          target_width_smaller = smaller.width * params["scale"]
        #
        paramsSIFT1 = paramsSIFT.clone()
        paramsSIFT1.maxOctaveSize = target_width_bigger
        paramsSIFT1.minOctaveSize = int(paramsSIFT1.maxOctaveSize / pow(2, paramsSIFT1.steps))
        paramsSIFT2 = paramsSIFT.clone()
        paramsSIFT2.maxOctaveSize = target_width_smaller
        paramsSIFT2.minOctaveSize = int(paramsSIFT2.maxOctaveSize / pow(2, paramsSIFT2.steps))
      
      ijSIFT1 = SIFT(FloatArray2DSIFT(paramsSIFT1))
      features1 = ArrayList() # of Point instances
      ijSIFT1.extractFeatures(fp1, features1)

      ijSIFT2 = SIFT(FloatArray2DSIFT(paramsSIFT2))
      features2 = ArrayList() # of Point instances
      ijSIFT2.extractFeatures(fp2, features2)
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

    return True
  except:
    syncPrint(sys.exc_info())
    syncPrint("".join(traceback.format_exception()), out="stderr")


def ensureSIFTFeatures(filepath, paramsSIFT, properties, csvDir, validateOnly=False):
  """
     filepath: to the image from which SIFT features have been or have to be extracted.
     params: dict of registration parameters, including the key "scale".
     paramsSIFT: FloatArray2DSIFT.Params instance.
     csvDir: directory into which serialized features have been or will be saved.
     load: function to load an image as an ImageProcessor from the filepath.
     validateOnly: whether to merely check that the Params match from the deserialized features file.
     
     First check if serialized features exist for the image, and if the Params match.
     Otherwise extract the features and store them serialized.
     Returns the ArrayList of Feature instances.
  """
  path = os.path.join(csvDir, os.path.basename(filepath) + ".SIFT-features.obj")
  # An ArrayList whose last element is a mpicbg.imagefeatures.FloatArray2DSIFT.Param
  # and all other elements are mpicbg.imagefeatures.Feature
  features = deserialize(path) if os.path.exists(path) else None
  if features:
    if features.get(features.size() -1).equals(paramsSIFT):
      if validateOnly:
        return True
      features.remove(features.size() -1) # removes the Params
      syncPrintQ("Loaded %i SIFT features for %s" % (features.size(), os.path.basename(filepath)))
      return features
    else:
      # Remove the file: paramsSIFT have changed
      os.remove(path)
  # Else, extract de novo:
  try:
    # Extract features
    ip = loadImp(filepath).getProcessor()
    paramsSIFT = paramsSIFT.clone()
    ijSIFT = SIFT(FloatArray2DSIFT(paramsSIFT))
    features = ArrayList() # of Feature instances
    ijSIFT.extractFeatures(ip, features)
    features.add(paramsSIFT) # append Params instance at the end for future validation
    serialize(features, path)
    features.remove(features.size() -1) # to return without the Params for immediate use
    syncPrintQ("Extracted %i SIFT features for %s" % (features.size(), os.path.basename(filepath)))
  except:
    e = sys.exc_info()
    System.out.println("".join(traceback.format_exception(e[0], e[1], e[2])))
    syncPrint(e)
  return features


def extractSIFTMatches(filepath1, filepath2, params, paramsSIFT, properties, csvDir):
  # Skip if pointmatches CSV file exists already:
  csvpath = os.path.join(csvDir, basename(filepath1) + '.' + basename(filepath2) + ".pointmatches.csv")
  if os.path.exists(csvpath):
    return False

  try:
    # Load from CSV files or extract features de novo
    features1 = ensureSIFTFeatures(filepath1, paramsSIFT, properties, csvDir)
    features2 = ensureSIFTFeatures(filepath2, paramsSIFT, properties, csvDir)
    syncPrintQ("Loaded %i features for %s\n       %i features for %s" % (features1.size(), os.path.basename(filepath1),
                                                                         features2.size(), os.path.basename(filepath2)))
    # Vector of PointMatch instances
    sourceMatches = FloatArray2DSIFT.createMatches(features1,
                                                   features2,
                                                   1.5, # max_sd
                                                   TranslationModel2D(),
                                                   Double.MAX_VALUE,
                                                   params["rod"]) # rod: ratio of best vs second best
    
    syncPrintQ("Found %i SIFT pointmatches for %s vs %s" % (sourceMatches.size(),
                                                            os.path.basename(filepath1),
                                                            os.path.basename(filepath2)))
    
    # Store pointmatches
    savePointMatches(os.path.basename(filepath1),
                     os.path.basename(filepath2),
                     sourceMatches,
                     csvDir,
                     params)
    return True
  except:
    e = sys.exc_info()
    System.out.println("".join(traceback.format_exception(e[0], e[1], e[2])))
    syncPrint(e)


def pointmatchingTasks(filepaths, csvDir, params, paramsSIFT, n_adjacent, exeload, properties, loadFPMem):
  for i in xrange(len(filepaths) - n_adjacent):
    for inc in xrange(1, n_adjacent + 1):
      #syncPrintQ("Preparing extractBlockMatches for: \n  1: %s\n  2: %s" % (filepaths[i], filepaths[i+inc]))
      yield Task(extractBlockMatches, filepaths[i], filepaths[i + inc], params, paramsSIFT, properties, csvDir, exeload, loadFPMem)


def ensurePointMatches(filepaths, csvDir, params, paramsSIFT, n_adjacent, properties):
  """ If a pointmatches csv file doesn't exist, will create it. """
  w = ParallelTasks("ensurePointMatches", exe=newFixedThreadPool(properties["n_threads"]))
  exeload = newFixedThreadPool()
  try:
    if properties.get("use_SIFT", False):
      syncPrintQ("use_SIFT is True")
      # Pre-extract SIFT features for all images first
      futures = []
      for filepath in filepaths:
        futures.append(exeload.submit(Task(ensureSIFTFeatures, filepath, paramsSIFT, properties, csvDir)))
      for i, fu in enumerate(futures):
        fu.get()
        if 0 == i % properties["n_threads"]:
          syncPrintQ("Completed extracting or validating SIFT features for %i images." % i)
      syncPrintQ("Completed extracting or validating SIFT features for all images.")
      # Compute pointmatches across adjacent sections
      futures = []
      count = 1
      paramsRod = {"rod": params["rod"]} # only this parameter is needed for SIFT pointmatches
      for i in xrange(max(1, len(filepaths) - n_adjacent)):
        for inc in xrange(1, min(n_adjacent + 1, len(filepaths))):
          futures.append(exeload.submit(Task(extractSIFTMatches, filepaths[i], filepaths[i + inc], paramsRod, paramsSIFT, properties, csvDir)))
      for fu in futures:
        fu.get()
        syncPrintQ("Completed %i/%i" % (count, len(filepaths) * n_adjacent))
        count += 1
    else:
      # Use blockmatches
      loadFPMem = SoftMemoize(lambda path: loadFloatProcessor(path, params, paramsSIFT, scale=True), maxsize=properties["n_threads"] + n_adjacent)
      count = 1
      for result in w.chunkConsume(properties["n_threads"], pointmatchingTasks(filepaths, csvDir, params, paramsSIFT, n_adjacent, exeload, properties, loadFPMem)):
        if result: # is False when CSV file already exists
          syncPrintQ("Completed %i/%i" % (count, len(filepaths) * n_adjacent))
        count += 1
      syncPrintQ("Awaiting all remaining pointmatching tasks to finish.")
      w.awaitAll()
    syncPrintQ("Finished all pointmatching tasks.")
  except:
    print sys.exc_info()
  finally:
    exeload.shutdown()
    w.destroy()


def loadPointMatchesPlus(filepaths, i, j, csvDir, params):
  return i, j, loadPointMatches(os.path.basename(filepaths[i]),
                                os.path.basename(filepaths[j]),
                                csvDir,
                                params,
                                verbose=False)

def loadPointMatchesTasks(filepaths, csvDir, params, n_adjacent):
  for i in xrange(len(filepaths) - n_adjacent):
    for inc in xrange(1, n_adjacent + 1):
      yield Task(loadPointMatchesPlus, filepaths, i, i + inc, csvDir, params)

# When done, optimize tile pose globally
def makeLinkedTiles(filepaths, csvDir, params, paramsSIFT, n_adjacent, properties):
  ensurePointMatches(filepaths, csvDir, params, paramsSIFT, n_adjacent, properties)
  try:
    tiles = [Tile(TranslationModel2D()) for _ in filepaths]
    # FAILS when running in parallel, for mysterious reasons related to jython internals, perhaps syncPrint fails
    #w = ParallelTasks("loadPointMatches")
    #for i, j, pointmatches in w.chunkConsume(properties["n_threads"], loadPointMatchesTasks(filepaths, csvDir, params, n_adjacent)):
    syncPrintQ("Loading all pointmatches.")
    for task in loadPointMatchesTasks(filepaths, csvDir, params, n_adjacent):
      i, j, pointmatches = task.call()
      tiles[i].connect(tiles[j], pointmatches) # reciprocal connection
    syncPrintQ("Finished loading all pointmatches.")
    return tiles
  finally:
    #w.destroy()
    pass


def align(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration, properties):
  if not os.path.exists(csvDir):
    os.makedirs(csvDir) # recursively
  name = "matrices"
  matrices = loadMatrices(name, csvDir)
  if matrices:
    return matrices
  
  # Optimize
  tiles = makeLinkedTiles(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration["n_adjacent"], properties)
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
    # BUG in TransformationModel2D.toMatrix   # TODO can be updated now, it's been fixed
    #a = nativeArray('d', [2, 3])
    #tile.getModel().toMatrix(a)
    #matrices.append(a[0] + a[1])
    # Instead:
    a = zeros(6, 'd')
    tile.getModel().toArray(a)
    matrices.append(array([a[0], a[2], a[4], a[1], a[3], a[5]], 'd'))

  saveMatrices(name, matrices, csvDir)
  
  return matrices


class TranslatedSectionGet(LazyCellImg.Get):
  def __init__(self, filepaths, loadImg, matrices, img_dimensions, cell_dimensions, interval, preload=None):
    self.filepaths = filepaths
    self.loadImg = loadImg # function to load images
    self.matrices = matrices
    self.img_dimensions = img_dimensions
    self.cell_dimensions = cell_dimensions # x,y must match dims of interval
    self.interval = interval # when smaller than the image, will crop
    self.cache = SoftMemoize(partial(TranslatedSectionGet.makeCell, self), maxsize=256)
    self.exe = newFixedThreadPool(-1) # BEWARE native memory leak if not closed
    self.preload = preload

  def preloadCells(self, index):
    # Submit jobs to concurrently preload cells ahead into the cache, if not there already
    if self.preload is not None and 0 == index % self.preload:
      # e.g. if index=0 and preload=5, will load [1,2,3,4]
      for i in xrange(index + 1, min(index + self.preload, len(self.filepaths))):
        self.exe.submit(Task(self.cache, i))

  def translate(self, dx, dy):
    a = zeros(2, 'l')
    self.interval.min(a)
    width = self.cell_dimensions[0]
    height = self.cell_dimensions[1]
    x0 = max(0, min(a[0] + dx, self.img_dimensions[0] - width))
    y0 = max(0, min(a[1] + dy, self.img_dimensions[1] - height))
    self.interval = FinalInterval([x0, y0],
                                  [x0 + width -1, y0 + height - 1])
    syncPrintQ(str(Intervals.dimensionsAsLongArray(self.interval)))
    self.cache.clear()

  def get(self, index):
    return self.cache(index) # ENORMOUS Thread contention in accessing every pixel

  def makeCell(self, index):
    self.preloadCells(index) # preload others in the background
    img = self.loadImg(self.filepaths[index])
    affine = AffineTransform2D()
    affine.set(self.matrices[index])
    imgI = Views.interpolate(Views.extendZero(img), NLinearInterpolatorFactory())
    imgA = RealViews.transform(imgI, affine)
    imgT = Views.zeroMin(Views.interval(imgA, self.interval))
    aimg = img.factory().create(self.interval)
    ImgUtil.copy(ImgView.wrap(imgT, aimg.factory()),
                 aimg)
    return Cell(self.cell_dimensions,
               [0, 0, index],
               aimg.update(None))


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
    try:
      dx, dy = self.delta.get(event.getKeyCode(), (0, 0))
      if dx + dy == 0:
        return
      syncPrintQ("Translating source")
      if event.isShiftDown():
        dx *= self.shift
        dy *= self.shift
      if event.isAltDown():
        dx *= self.alt
        dy *= self.alt
      syncPrintQ("... by x=%i, y=%i" % (dx, dy))
      self.cellGet.translate(dx, dy)
      self.imp.updateAndDraw()
      event.consume()
    except:
      syncPrintQ(str(sys.exc_info()))


def makeImg(filepaths, pixelType, loadImg, img_dimensions, matrices, cropInterval, preload):
  dims = Intervals.dimensionsAsLongArray(cropInterval)
  voldims = [dims[0],
             dims[1],
             len(filepaths)]
  cell_dimensions = [dims[0],
                     dims[1],
                     1]
  grid = CellGrid(voldims, cell_dimensions)
  cellGet = TranslatedSectionGet(filepaths, loadImg, matrices, img_dimensions, cell_dimensions,
                                 cropInterval, preload=preload)
  return LazyCellImg(grid, pixelType(), cellGet), cellGet


class OnClosing(ImageListener):
  def __init__(self, imp, cellGet):
    self.imp = imp
    self.cellGet = cellGet
  def imageClosed(self, imp):
    if imp == self.imp:
      self.cellGet.exe.shutdownNow()
  def imageOpened(self, imp):
    pass
  def imageUpdated(self, imp):
    pass

def viewAligned(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration, properties, cropInterval):
  matrices = align(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration, properties)
  def loadImg(filepath):
    return loadUnsignedShort(filepath, invert=properties["invert"], CLAHE_params=properties["CLAHE_params"])
  cellImg, cellGet = makeImg(filepaths, properties["pixelType"], loadImg, properties["img_dimensions"], matrices, cropInterval, 5)
  print cellImg
  comp = showStack(cellImg, title=properties["srcDir"].split('/')[-2], proper=False)
  # Add the SourcePanning KeyListener as the first one
  canvas = comp.getWindow().getCanvas()
  kls = canvas.getKeyListeners()
  for kl in kls:
    canvas.removeKeyListener(kl)
  canvas.addKeyListener(SourcePanning(cellGet, comp))
  for kl in kls:
    canvas.addKeyListener(kl)
  ImagePlus.addImageListener(OnClosing(comp, cellGet))
  return comp


def export8bitN5(filepaths,
                 loadFn,
                 img_dimensions,
                 matrices,
                 name,
                 exportDir,
                 interval,
                 gzip_compression=6,
                 invert=True,
                 CLAHE_params=[400, 256, 3.0],
                 n5_threads=0, # 0 means as many as CPU cores
                 block_size=[128,128,128]):
  """
  Export into an N5 volume, in parallel, in 8-bit.

  filepaths: the ordered list of filepaths, one per serial section.
  loadFn: a function to load a filepath into an ImagePlus.
  name: name to assign to the N5 volume.
  matrices: the list of transformation matrices (each one is an array), one per section
  exportDir: the directory into which to save the N5 volume.
  interval: for cropping.
  gzip_compression: defaults to 6 as suggested by Saalfeld. 0 means no compression.
  invert:  Defaults to True (necessary for FIBSEM). Whether to invert the images upon loading.
  CLAHE_params: defaults to [400, 256, 3.0]. If not None, the a list of the 3 parameters needed for a CLAHE filter to apply to each image.
  n5_threads: defaults to 0, meaning as many as CPU cores.
  block_size: defaults to 128x128x128 px. A list of 3 integer numbers, the dimensions of each individual block.
  """

  dims = Intervals.dimensionsAsLongArray(interval)
  voldims = [dims[0],
             dims[1],
             len(filepaths)]
  cell_dimensions = [dims[0],
                     dims[1],
                     1]

  def asNormalizedUnsignedByteArrayImg(interval, invert, blockRadius, n_bins, slope, matrices, index, imp):
    sp = imp.getProcessor() # ShortProcessor
    # Crop to interval if needed
    x = interval.min(0)
    y = interval.min(1)
    width  = interval.max(0) - interval.min(0) + 1
    height = interval.max(1) - interval.min(1) + 1
    if 0 != x or 0 != y or sp.getWidth() != width or sp.getHeight() != height:
      sp.setRoi(x, y, width, height)
      sp = sp.crop()
    
    if invert:
      sp.invert()
    
    CLAHE.run(ImagePlus("", sp), blockRadius, n_bins, slope, None) # far less memory requirements than NormalizeLocalContrast, and faster.
    minimum, maximum = autoAdjust(sp)

    # Transform and convert image to 8-bit, mapping to display range
    img = ArrayImgs.unsignedShorts(sp.getPixels(), [sp.getWidth(), sp.getHeight()])
    sp = None
    imp = None
    affine = AffineTransform2D()
    affine.set(matrices[index])
    imgI = Views.interpolate(Views.extendZero(img), NLinearInterpolatorFactory())
    imgA = RealViews.transform(imgI, affine)
    imgT = Views.zeroMin(Views.interval(imgA, img))
    imgMinMax = convert(imgT, RealUnsignedByteConverter(minimum, maximum), UnsignedByteType)
    aimg = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(img))
    ImgUtil.copy(ImgView.wrap(imgMinMax, aimg.factory()), aimg)
    img = imgI = imgA = imgT = imgMinMax = None
    return aimg
    

  blockRadius, n_bins, slope = CLAHE_params

  # A CacheLoader that interprets the list of filepaths as a 3D volume: a stack of 2D slices
  loader = SectionCellLoader(filepaths, 
                             asArrayImg=partial(asNormalizedUnsignedByteArrayImg,
                                                interval, invert, blockRadius, n_bins, slope, matrices),
                             loadFn=loadFn)

  # How to preload block_size[2] files at a time? Or at least as many as numCPUs()?
  # One possibility is to query the SoftRefLoaderCache.map for its entries, using a ScheduledExecutorService,
  # and preload sections ahead for the whole blockSize[2] dimension.


  cachedCellImg = lazyCachedCellImg(loader, voldims, cell_dimensions, UnsignedByteType, BYTE)

  exe_preloader = newFixedThreadPool(n_threads=min(block_size[2], n5_threads if n5_threads > 0 else numCPUs()), name="preloader")

  def preload(cachedCellImg, loader, block_size, filepaths, exe):
    """
    Find which is the last cell index in the cache, identify to which block
    (given the blockSize[2] AKA Z dimension) that index belongs to,
    and concurrently load all cells (sections) that the Z dimension of the blockSize will need.
    If they are already loaded, these operations are insignificant.
    """
    try:
      # The SoftRefLoaderCache.map is a ConcurrentHashMap with Long keys, aka numbers
      cache = cachedCellImg.getCache()
      f1 = cache.getClass().getDeclaredField("cache") # LoaderCacheAsCacheAdapter.cache
      f1.setAccessible(True)
      softCache = f1.get(cache)
      cache = None
      f2 = softCache.getClass().getDeclaredField("map") # SoftRefLoaderCache.map
      f2.setAccessible(True)
      keys = sorted(f2.get(softCache).keySet())
      if 0 == len(keys):
        return
      first = max(0, keys[-1] - (keys[-1] % block_size[2]))
      last = min(len(filepaths), first + block_size[2]) -1
      keys = None
      syncPrintQ("### Preloading %i-%i ###" % (first, last))
      futures = []
      for index in xrange(first, last + 1):
        futures.append(exe.submit(TimeItTask(softCache.get, index, loader)))
      softCache = None
      # Wait for all
      loaded_any = False
      count = 0
      while len(futures) > 0:
        r, t = futures.pop(0).get() # waits for the image to load
        if t > 1000: # in miliseconds. Less than this is for sure a cache hit, more a cache miss and reload
          loaded_any = True
        r = None
        # t in miliseconds
        syncPrintQ("preloaded index %i in %f ms" % (first + count, t))
        count += 1
      if not loaded_any:
        syncPrintQ("Completed preloading %i-%i" % (first, first + block_size[2] -1))
    except:
      syncPrintQ(sys.exc_info())

  preloader = Executors.newSingleThreadScheduledExecutor()
  preloader.scheduleWithFixedDelay(RunTask(preload, cachedCellImg, loader, block_size, filepaths, exe_preloader), 10, 60, TimeUnit.SECONDS)

  try:
    syncPrint("N5 directory: " + exportDir + "\nN5 dataset name: " + name + "\nN5 blockSize: " + str(block_size))
    writeN5(cachedCellImg, exportDir, name, block_size, gzip_compression_level=gzip_compression, n_threads=n5_threads)
  finally:
    preloader.shutdown()
    exe_preloader.shutdown()
