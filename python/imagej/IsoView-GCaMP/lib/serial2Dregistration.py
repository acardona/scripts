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

from __future__ import with_statement
import os, sys, traceback, csv
from os.path import basename
from operator import itemgetter
from mpicbg.ij.blockmatching import BlockMatching
from mpicbg.models import ErrorStatistic, TranslationModel2D, TransformMesh, PointMatch, Point, NotEnoughDataPointsException, Tile, TileConfiguration, TileUtil
from mpicbg.imagefeatures import FloatArray2DSIFT
from mpicbg.ij.util import Filter, Util
from mpicbg.ij import SIFT # see https://github.com/axtimwalde/mpicbg/blob/master/mpicbg/src/main/java/mpicbg/ij/SIFT.java
from mpicbg.ij.clahe import FastFlat as CLAHE
from java.util import ArrayList, HashSet
from java.lang import Double, System, Runnable, Runtime
from net.imglib2.type.numeric.integer import UnsignedShortType, UnsignedByteType
from net.imglib2.view import Views
from ij.process import FloatProcessor
from ij import IJ, ImageListener, ImagePlus, WindowManager
from net.imglib2.img.io.proxyaccess import ShortAccessProxy
from net.imglib2.img.cell import LazyCellImg, Cell, CellGrid
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.array import ArrayImgs
from net.imglib2.img import ImgView 
from net.imglib2.util import ImgUtil, Intervals
from net.imglib2.realtransform import RealViews, AffineTransform2D
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2 import FinalInterval
from net.imglib2.type.PrimitiveType import BYTE, SHORT
from net.imglib2.converter import RealUnsignedByteConverter
from net.imglib2.loops import LoopBuilder
from net.imglib2.algorithm.math import ImgMath
from java.awt.event import KeyAdapter, KeyEvent
from java.util.concurrent import Executors, TimeUnit
from jarray import zeros, array
from functools import partial
from itertools import izip, islice
from collections import defaultdict
# From lib
from io import lazyCachedCellImg, SectionCellLoader, writeN5, serialize, deserialize
from util import SoftMemoize, newFixedThreadPool, Task, RunTask, TimeItTask, ParallelTasks, numCPUs, nativeArray, syncPrint, syncPrintQ, printException
from features import savePointMatches, loadPointMatches, saveFeatures, loadFeatures, PointMatches
from registration import loadMatrices, saveMatrices
from ui import showStack, wrap, showTable, ExecutorCloser
from converter import convert2
from pixels import autoAdjust
from loop import createBiConsumerTypeSet



def loadImp(filepath):
  """ Returns an ImagePlus """
  syncPrintQ("Loading image " + filepath)
  return IJ.openImage(filepath)

def loadUnsignedShort(filepath, invert=True, CLAHE_params=None, loaderImp=None):
  """ Returns an ImgLib2 ArrayImg """
  impLoader = loaderImp if loaderImp else loadImp
  imp = impLoader(filepath)
  if invert:
    imp.getProcessor().invert()
  if CLAHE_params is not None:
    blockRadius, n_bins, slope = CLAHE_params
    CLAHE.run(imp, blockRadius, n_bins, slope, None)
  return ArrayImgs.unsignedShorts(imp.getProcessor().getPixels(), [imp.getWidth(), imp.getHeight()])

def loadFloatProcessor(filepath, params, paramsSIFT, scale=True, loaderImp=None):
  try:
    impLoader = loaderImp if loaderImp else loadImp
    fp = impLoader(filepath).getProcessor().convertToFloatProcessor()
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


def extractBlockMatches(filepath1, filepath2, params, paramsSIFT, properties, csvDir, exeload, load, loaderImp=None):
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
    #use_blockmatching = fp1.getWidth() == fp2.getWidth() and fp1.getHeight() == fp2.getHeight()

    # Fill the sourcePoints in unscaled space (will be scaled down again by matchByMaximalPMCCFromPreScaledImages)
    dimensions = properties['img_dimensions'] # unscaled
    mesh = TransformMesh(params["meshResolution"], dimensions[0], dimensions[1]) # unscaled
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
      futures = [exeload.submit(Task(loadFloatProcessor, filepath1, params, paramsSIFT, scale=False, loaderImp=loaderImp)),
                 exeload.submit(Task(loadFloatProcessor, filepath2, params, paramsSIFT, scale=False, loaderImp=loaderImp))]

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
                                                     params.get("max_sd", 1.5), # max_sd: maximal difference in size (ratio max/min)
                                                     TranslationModel2D(),
                                                     params.get("max_id", Double.MAX_VALUE), # max_id: maximal distance in image space
                                                     params.get("rod", 0.9)) # rod: ratio of best vs second best

      msg = ""
      # Filter matches by geometric consensus
      if properties.get("use_RANSAC", True):
        n_pm = sourceMatches.size()
        inliers = ArrayList()
        iterations = properties.get("RANSAC_iterations", 1000)
        maxEpsilon = properties.get("RANSAC_maxEpsilon", 25) # pixels
        minInlierRatio = properties.get("RANSAC_minInlierRatio", 0.01) # 1%
        modelFound = TranslationModel2D().filterRansac(sourceMatches, inliers, iterations, maxEpsilon, minInlierRatio)
        if modelFound:
          sourceMatches = inliers
        else:
          sourceMatches.clear()
          msg = "SIFT: model NOT FOUND for %s vs %s\n" % (os.path.basename(filepath1),
                                                          os.path.basename(filepath2))
      
      syncPrintQ("%sFound %i inlier SIFT pointmatches (from %i) for %s vs %s" % (msg,
                                                            sourceMatches.size(),
                                                            n_pm,
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
    printException()


def ensureSIFTFeatures(filepath, paramsSIFT, properties, csvDir, validateByFileExists=False, loaderImp=None):
  """
     filepath: to the image from which SIFT features have been or have to be extracted.
     params: dict of registration parameters, including the key "scale".
     paramsSIFT: FloatArray2DSIFT.Params instance.
     csvDir: directory into which serialized features have been or will be saved.
     load: function to load an image as an ImageProcessor from the filepath.
     validateByFileExists: whether to merely check that the .obj file exists as a quick form of validation.
     
     First check if serialized features exist for the image, and if the Params match.
     Otherwise extract the features and store them serialized.
     Returns the ArrayList of Feature instances.
  """
  path = os.path.join(csvDir, os.path.basename(filepath) + ".SIFT-features.obj")
  if validateByFileExists:
    if os.path.exists(path):
      return True
  # An ArrayList whose last element is a mpicbg.imagefeatures.FloatArray2DSIFT.Param
  # and all other elements are mpicbg.imagefeatures.Feature
  features = deserialize(path) if os.path.exists(path) else None
  if features:
    if features.get(features.size() -1).equals(paramsSIFT):
      features.remove(features.size() -1) # removes the Params
      syncPrintQ("Loaded %i SIFT features for %s" % (features.size(), os.path.basename(filepath)))
      return features
    else:
      # Remove the file: paramsSIFT have changed
      os.remove(path)
  # Else, extract de novo:
  try:
    impLoader = loaderImp if loaderImp else loadImp
    # Extract features
    imp = impLoader(filepath)
    ip = imp.getProcessor()
    paramsSIFT = paramsSIFT.clone()
    ijSIFT = SIFT(FloatArray2DSIFT(paramsSIFT))
    features = ArrayList() # of Feature instances
    ijSIFT.extractFeatures(ip, features)
    ip = None
    imp.flush()
    imp = None
    features.add(paramsSIFT) # append Params instance at the end for future validation
    serialize(features, path)
    features.remove(features.size() -1) # to return without the Params for immediate use
    syncPrintQ("Extracted %i SIFT features for %s" % (features.size(), os.path.basename(filepath)))
  except:
    printException()
  return features


def extractSIFTMatches(filepath1, filepath2, params, paramsSIFT, properties, csvDir, loaderImp=None):
  # Skip if pointmatches CSV file exists already:
  csvpath = os.path.join(csvDir, basename(filepath1) + '.' + basename(filepath2) + ".pointmatches.csv")
  if os.path.exists(csvpath):
    return False

  try:
    # Load from CSV files or extract features de novo
    features1 = ensureSIFTFeatures(filepath1, paramsSIFT, properties, csvDir, loaderImp=loaderImp)
    features2 = ensureSIFTFeatures(filepath2, paramsSIFT, properties, csvDir, loaderImp=loaderImp)
    #syncPrintQ("Loaded %i features for %s\n       %i features for %s" % (features1.size(), os.path.basename(filepath1),
    #                                                                     features2.size(), os.path.basename(filepath2)))
    # Vector of PointMatch instances
    sourceMatches = FloatArray2DSIFT.createMatches(features1,
                                                   features2,
                                                   params.get("max_sd", 1.5), # max_sd: maximal difference in size (ratio max/min)
                                                   TranslationModel2D(),
                                                   params.get("max_id", Double.MAX_VALUE), # max_id: maximal distance in image space
                                                   params.get("rod", 0.9)) # rod: ratio of best vs second best
    msg = ""
    # Filter matches by geometric consensus
    if properties.get("use_RANSAC", True):
      n_pm = sourceMatches.size()
      inliers = ArrayList()
      iterations = properties.get("RANSAC_iterations", 1000)
      maxEpsilon = properties.get("RANSAC_maxEpsilon", 25) # pixels
      minInlierRatio = properties.get("RANSAC_minInlierRatio", 0.01) # 1%
      modelFound = TranslationModel2D().filterRansac(sourceMatches, inliers, iterations, maxEpsilon, minInlierRatio)
      if modelFound:
        sourceMatches = inliers
      else:
        sourceMatches.clear() # None
        msg = "SIFT: model NOT FOUND for %s vs %s\n" % (os.path.basename(filepath1),
                                                        os.path.basename(filepath2))
    
    syncPrintQ("%sFound %i inlier SIFT pointmatches (from %i) for %s vs %s" % (msg,
                                                            sourceMatches.size(),
                                                            n_pm,
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
    printException()


def pointmatchingTasks(filepaths, csvDir, params, paramsSIFT, n_adjacent, exeload, properties, loadFPMem, loaderImp=None):
  for i in xrange(len(filepaths) - n_adjacent):
    for inc in xrange(1, n_adjacent + 1):
      #syncPrintQ("Preparing extractBlockMatches for: \n  1: %s\n  2: %s" % (filepaths[i], filepaths[i+inc]))
      yield Task(extractBlockMatches, filepaths[i], filepaths[i + inc], params, paramsSIFT, properties, csvDir, exeload, loadFPMem, loaderImp=loaderImp)

def generateSIFTMatches(filepaths, n_adjacent, params, paramsSIFT, properties, csvDir, loaderImp=None):
  paramsRod = {"rod": params["rod"]} # only this parameter is needed for SIFT pointmatches
  for i in xrange(max(1, len(filepaths) - n_adjacent)):
    for inc in xrange(1, min(n_adjacent + 1, len(filepaths))):
      yield Task(extractSIFTMatches, filepaths[i], filepaths[i + inc], paramsRod, paramsSIFT, properties, csvDir, loaderImp=loaderImp)


def ensurePointMatches(filepaths, csvDir, params, paramsSIFT, n_adjacent, properties, loaderImp=None):
  """ If a pointmatches csv file doesn't exist, will create it. """
  w = ParallelTasks("ensurePointMatches", exe=newFixedThreadPool(properties["n_threads"]))
  exeload = newFixedThreadPool()
  try:
    if properties.get("use_SIFT", False):
      syncPrintQ("use_SIFT is True")
      # Pre-extract SIFT features for all images first
      # ensureSIFTFeatures returns the features list so the Future will hold it in memory: can't hold onto them
      # therefore consume the tasks in chunks:
      chunk_size = properties["n_threads"] * 2
      count = 1
      for result in w.chunkConsume(chunk_size, # tasks to submit before starting to wait for futures
                                   (Task(ensureSIFTFeatures, filepath, paramsSIFT, properties, csvDir, validateByFileExists=properties.get("SIFT_validateByFileExists"), loaderImp=loaderImp)
                                    for filepath in filepaths)):
        count += 1
        if 0 == count % chunk_size:
          syncPrintQ("Completed extracting or validating SIFT features for %i images." % count)
      w.awaitAll()
      syncPrintQ("Completed extracting or validating SIFT features for all images.")
      # Compute pointmatches across adjacent sections
      count = 1
      for result in w.chunkConsume(chunk_size,
                                   generateSIFTMatches(filepaths, n_adjacent, params, paramsSIFT, properties, csvDir, loaderImp=loaderImp)):
        count += 1
        syncPrintQ("Completed SIFT pointmatches %i/%i" % (count, len(filepaths) * n_adjacent))
    else:
      # Use blockmatches
      syncPrintQ("using blockmatches")
      loadFPMem = SoftMemoize(lambda path: loadFloatProcessor(path, params, paramsSIFT, scale=True, loaderImp=loaderImp), maxsize=properties["n_threads"] + n_adjacent)
      count = 1
      for result in w.chunkConsume(properties["n_threads"], pointmatchingTasks(filepaths, csvDir, params, paramsSIFT, n_adjacent, exeload, properties, loadFPMem, loaderImp=loaderImp)):
        if result: # is False when CSV file already exists
          syncPrintQ("Completed %i/%i" % (count, len(filepaths) * n_adjacent))
        count += 1
      syncPrintQ("Awaiting all remaining pointmatching tasks to finish.")
    w.awaitAll()
    syncPrintQ("Finished all pointmatching tasks.")
  except:
    printException()
  finally:
    exeload.shutdown()
    w.destroy()


def loadPointMatchesPlus(filepaths, i, j, csvDir, params, properties):
  #return i, j, loadPointMatches(os.path.basename(filepaths[i]),
  #                              os.path.basename(filepaths[j]),
  #                              csvDir,
  #                              params,
  #                              verbose=False)
  # DOES NOT check header params
  pointmatches = PointMatches.fromPath(os.path.join(csvDir, os.path.basename(filepaths[i]) + "." + os.path.basename(filepaths[j]) + ".pointmatches.csv")).pointmatches
  max_n_pointmatches = properties.get("max_n_pointmatches", 0)
  if max_n_pointmatches > 0:
    pointmatches = samplePointMatches(pointmatches, maximum=max_n_pointmatches)
  return i, j, pointmatches


def loadPointMatchesTasks(filepaths, csvDir, params, n_adjacent, properties):
  for i in xrange(max(1, len(filepaths) - n_adjacent)):
    for inc in xrange(1, min(n_adjacent + 1, len(filepaths))):
      yield Task(loadPointMatchesPlus, filepaths, i, i + inc, csvDir, params, properties)

# When done, optimize tile pose globally
def makeLinkedTiles(filepaths, csvDir, params, paramsSIFT, n_adjacent, properties, loaderImp=None):
  if properties.get("precompute", True):
    ensurePointMatches(filepaths, csvDir, params, paramsSIFT, n_adjacent, properties, loaderImp=loaderImp)
  tiles = [Tile(TranslationModel2D()) for _ in filepaths]
  syncPrintQ("Loading all pointmatches.")
  if properties.get("use_SIFT"):
    params = {"rod": params["rod"]}
  try:
    # FAILS when running in parallel, for mysterious reasons related to jython internals, perhaps syncPrint fails
    w = ParallelTasks("loadPointMatches")
    last = -1
    #for task in loadPointMatchesTasks(filepaths, csvDir, params, n_adjacent):
    #  i, j, pointmatches = task.call()
    for task in w.chunkConsume(properties["n_threads"] * 2,
                               loadPointMatchesTasks(filepaths, csvDir, params, n_adjacent, properties)):
      i, j, pointmatches = task
      #syncPrintQ("%i, %i : %i" % (i, j, len(pointmatches)))
      if pointmatches is None or 0 == len(pointmatches):
        fn = properties.get("handleNoPointMatchesFn", None)
        if fn:
          pointmatches = fn(filepaths, i, j)
      if pointmatches is None or 0 == len(pointmatches):
        syncPrintQ("%i, %i : %i from files:\n%s\n%s" % (i, j, len(pointmatches) if pointmatches else 0, filepaths[i], filepaths[j]))
      else:
        # Only if there are more than 0 pointmatches!
        if len(pointmatches) < 2:
          syncPrintQ("%i pointmatches for %i, %i" % (len(pointmatches), i, j))
        tiles[i].connect(tiles[j], pointmatches) # reciprocal connection
      if 0 == i % 1000 and i != last:
        last = i
        syncPrintQ("Completed loading %i/%i pointmatches" % (i, len(filepaths)))
    syncPrintQ("Finished loading all pointmatches.")
    return tiles
  except Exception as e:
    print e
  finally:
    w.destroy()
    pass


def handleNoPointMatches(filepaths, i, j):
  """
  Defaults to returning a single pointmatch correspondence, at coordinate 1.0,1.0.
  """
  syncPrintQ("No pointmatches. Using zero translation for %i, %i" % (i, j))
  pm = PointMatch(Point(array([1.0, 1.0], 'd')), Point(array([1.0,1.0], 'd')))
  a = ArrayList()
  a.add(pm)
  return a


def optimize(tiles, paramsTileConfiguration, fixed_tile_indices=None, verbose=False):
  tc = TileConfiguration()
  tc.addTiles(tiles)
  if not fixed_tile_indices:
    tc.fixTile(tiles[len(tiles) / 2]) # middle tile
  else:
    for i in fixed_tile_indices:
      tc.fixTile(tiles[i])
  
  maxAllowedError = paramsTileConfiguration["maxAllowedError"]
  maxPlateauwidth = paramsTileConfiguration["maxPlateauwidth"]
  maxIterations = paramsTileConfiguration["maxIterations"]
  damp = paramsTileConfiguration["damp"]
  nThreads = paramsTileConfiguration.get("nThreadsOptimizer", Runtime.getRuntime().availableProcessors())
  TileUtil.optimizeConcurrently(ErrorStatistic(maxPlateauwidth + 1), maxAllowedError,
                                maxIterations, maxPlateauwidth, damp, tc, HashSet(tiles),
                                tc.getFixedTiles(), nThreads, verbose)
  

def align(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration, properties,
          loaderImp=None, fixed_tile_indices=None, io=True, verboseOptimize=True):
  if not os.path.exists(csvDir):
    os.makedirs(csvDir) # recursively
  name = "matrices"
  
  if io:
    matrices = loadMatrices(name, csvDir)
    if matrices:
      return matrices
  
  # Optimize
  tiles = makeLinkedTiles(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration["n_adjacent"], properties, loaderImp=loaderImp)
  optimize(tiles, paramsTileConfiguration, fixed_tile_indices, verbose=verboseOptimize)

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

  if io:
    saveMatrices(name, matrices, csvDir)
  
  return matrices
  
  
def alignInChunks(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration, properties,
                  loaderImp=None, fixed_tile_index=None):
  """
  Align overlapping chunks of serial sections independently, and then interpolate the alignments.
  This approach helps the optimizer do a good job and fast.
  The size of the chunks should be small, like 400, and the overlap between consecutive chunks should be 50%.
  Needs only one fixed section (tile) for the overall; when aligning each chunk, the middle tile is kept fixed.
  """
  if not os.path.exists(csvDir):
    os.makedirs(csvDir) # recursively
  name = "matrices"
  matrices = loadMatrices(name, csvDir)
  if matrices:
    return matrices
    
  # Determine fixed tile
  if fixed_tile_index is None:
    fixed_tile_index = int(len(filepaths) / 2)
  
  # Compute alignment for overlapping chunks
  chunk_size = paramsTileConfiguration.get("chunk_size", 400)
  overlap = int(chunk_size / 2)
  
  # Each element is a list of matrices, one for each section in the chunk
  chunks = []
  
  # The last overlap shouldn't be created, since it's half the size as chunk_size, so subtract overlap from len(filepaths)
  k, localindex = divmod(fixed_tile_index, overlap) # k is the chunk index, and localindex (the remainder) is the index within the chunk
  for i in xrange(0, len(filepaths) - overlap, overlap): # ASSUMES overlap is larger than len(filepaths)
    start = i
    end = min(start + chunk_size, len(filepaths))
    chunk_index = len(chunks)
    # If the fixed_tile_index is in this chunk, use that as the fixed tile instead of the middle one
    if k == chunk_index:
      fixed = localindex # in the first half of the chunk
    elif k == chunk_index + 1:
      fixed = overlap + localindex # in the second half of the chunk
    else:
      # Use the middle tile
      fixed = min(overlap -1, end - start -1) # -1 because it's 0-based.
    print start, end, fixed, overlap
    name_i = "%s_%i-%i" % (name, start, end)
    matrices = loadMatrices(name_i, csvDir)
    if matrices:
      print "Loaded", name_i
    else:
      print "Computing", name_i
      matrices = align(filepaths[start:end], csvDir, params, paramsSIFT, paramsTileConfiguration, properties,
                       loaderImp=loaderImp, fixed_tile_indices=[fixed], io=False, verboseOptimize=True)
    chunks.append(matrices)
    saveMatrices(name_i, matrices, csvDir)
    
  # Now register the overlapping chunks, considering each chunk as a tile
  # Given that the subset of sections is the same, use for pointmatches across tiles one point per section,
  # transformed by the transform of that section in that chunk,
  # towards computing a TranslationModel2D for each tile (each chunk is tile).
  dims = properties["img_dimensions"]
  px, py = dims[0] / 2, dims[1] / 2
  chunk_tiles = [(chunk, Tile(TranslationModel2D())) for chunk in chunks]
  for (cmatrices1, tile1), (cmatrices2, tile2) in izip(chunk_tiles, islice(chunk_tiles, 1, None)):
    pointmatches = []
    for m1, m2 in izip(islice(cmatrices1, overlap, None), # from overlap to the end
                       islice(cmatrices2, 0, overlap)):   # from 0 to overlap
      # Apply each transform to the center point: since it's just a Translation, simply add it
      pointmatches.append(Point(array([px + m1[2], py + m1[5]], 'd')),
                          Point(array([px + m2[2], py + m2[5]], 'd')))
    tile1.connect(tile2, pointmatches) # reciprocal
  
  # Fix one of the chunks (there can be two) that contains the fixed_tile_index
  # (The other one will have had its fixed tile at the same section)
  ifix = [fixed_tile_index % overlap] if fixed_tile_index is not None else None
  
  optimize([tile for _, tile in chunk_tiles],
            paramsTileConfiguration, fixed_tile_indices=ifix)
  
  # Now use the matrices from the chunk-wise registration to offset the local registrations within each chunk.
  
  # Apply the chunk_tile translation to the matrix
  def toChunkCoordinates(chunk_tile, matrix):
    tx, ty = chunk_tile.getModel().getTranslation() # TranslationModel2D
    m = matrix[:] # clone (works for both arrays and lists
    m[2] += tx
    m[5] += ty
    return m
  
  # Interpolate matrices across overlapping regions
  # There is one chunk for sections [0, overlap],
  # two chunks for sections [>overlap, last chunk -1]
  # and one chunk for sections on the second half of the last chunk, about [> n - overlap, n]
  matrices = []
  
  # The first set of sections from 0 to overlap: no interpolation needed, doesn't overlap with any other chunk
  cmatrices, chunk_tile = chunk_tiles[0]
  for i in xrange(overlap):
    matrices.append(toChunkCoordinates(chunk_tile, cmatrices[i]))
  
  # The set of sections where there's overlap between chunks
  for (cmatrices1, chunk_tile1), (cmatrices2, chunk_tile2) in izip(chunk_tiles, islice(chunk_tiles, 1, None)):
    for i in xrange(overlap):
      # weights: 1.0 at the middle of the chunk, 0.0 at the start or end of a chunk.
      w1 = 1.0 - i / float(overlap -1)
      w2 = 1.0 - w1
      m1 = toChunkCoordinates(chunk_tile1, cmatrices1[overlap + i]) # the second half of the chunk
      m2 = toChunkCoordinates(chunk_tile2, cmatrices2[i]) # the first half, up to the middle section
      matrix = [1, 0, m1[3] * w1 + m2[3] * w2,
                0, 1, m1[5] * w1 + m2[5] * w2]
      matrices.append(matrix)
  
  # The last set of sections up to len(filepaths)
  cmatrices, chunk_tile = chunk_tiles[-1]
  for i in xrange(min(overlap, len(filepaths) % overlap)):
    matrices.append(toChunkCoordinates(chunk_tile, cmatrices[overlap + i]))
    
  # matrices are now all relative to the fixed tile
  
  """
  
  matrices = []
  for i in xrange(len(filepaths)):
    k = int(i / overlap) # index on the list of chunks
    chunk_tile = chunk_tiles[k][1]
    # Handle beginning when there's only one chunk
    if 0 == k:
      matrix = toChunkCoordinates(chunk_tile, chunks[0][i])
    # Handle end, when there isn't an ending chunk beyond the middle tile of the actual last chunk
    elif k == len(chunks): # k is beyond the start+overlap section of the last chunk
      matrix = toChunkCoordinates(chunk_tile, chunks[k-1][i - (k-1) * overlap])
    # Else, there are two chunks overlapping, at k and at k-1
    else:
      i1 = i - (k-1) * overlap
      i2 = i -  k    * overlap
      # weights: 1.0 at the center of the chunk, 0.0 at the start or end of a chunk.
      w1 = 1.0 - (abs(i1 - overlap) / float(overlap))
      w2 = 1.0 - (abs(i2 - overlap) / float(overlap))
      m1 = toChunkCoordinates(chunk_tile, chunks[k-1][i1])
      m2 = toChunkCoordinates(chunk_tile, chunks[k  ][i2])
      matrix = [1, 0, m1[3] * w1 + m2[3] * w2,
                0, 1, m1[5] * w1 + m2[5] * w2]
    #
    matrices.append(matrix)
  
  # All matrices are relative translations. Make them relative to the global fixed tile,
  # so that the global fixed tile has a 0, 0 translation:
  m_fixed = matrices[fixed_tile_index]
  offset_x, offset_y = -m_fixed[2], -m_fixed[5]
  for m in matrices:
    m[2] += offset_x
    m[5] += offset_y
  """
  
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
    self.exe = None
    if preload:
      self.exe = newFixedThreadPool(preload) # BEWARE native memory leak if not closed
    self.preload = preload

  def preloadCells(self, index):
    # Submit jobs to concurrently preload cells ahead into the cache, if not there already
    if self.preload is not None and self.preload > 0 and 0 == index % self.preload:
      # e.g. if index=0 and preload=5, will load [1,2,3,4]
      for i in xrange(index + 1, min(index + self.preload, len(self.filepaths))):
        self.exe.submit(Task(self.cache, i))

  def destroy(self):
    if self.exe is not None:
      self.exe.shutdownNow()

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
  """ Note that when preload > 0, tjhe returned cellGet (a TranslatedSectionGet as defined above)
      will have created an ExecutorService that can be shutdown by invoking destroy() on the returned cellGet.
  """
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
      self.cellGet.destroy()
  def imageOpened(self, imp):
    pass
  def imageUpdated(self, imp):
    pass

def viewAlignedPlain(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration, properties, cropInterval, loaderImp=None):
  matrices = align(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration, properties, loaderImp=loaderImp)
  def loadImg(filepath):
    return loadUnsignedShort(filepath, invert=properties["invert"], CLAHE_params=properties["CLAHE_params"], loaderImp=loaderImp)
  cellImg, cellGet = makeImg(filepaths, properties["pixelType"], loadImg, properties["img_dimensions"], matrices, cropInterval, properties.get('preload', 0))
  print "cropInterval", cropInterval
  print "viewAlignedPlain, cellImg:", cellImg
  print "viewAlignedPlain:", cellImg.getCellGrid()
  print "viewAlignedPlain:", cellImg.getCells()
  print "viewAlignedPlain, properties::name : ", properties.get("name", "")
  ra = cellImg.randomAccess()
  ra.setPosition([0, 0, 0])
  print "RandomAccess at 0,0,0: ", ra.get()
  imp = IL.wrap(cellImg, properties.get("name", ""))
  imp.show()
  return cellImg


def viewAligned(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration, properties, cropInterval, loaderImp=None):
  matrices = align(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration, properties, loaderImp=loaderImp)
  def loadImg(filepath):
    return loadUnsignedShort(filepath, invert=properties["invert"], CLAHE_params=properties["CLAHE_params"], loaderImp=loaderImp)
  cellImg, cellGet = makeImg(filepaths, properties["pixelType"], loadImg, properties["img_dimensions"], matrices, cropInterval, properties.get('preload', 0))
  print cellImg
  comp = showStack(cellImg, title=properties["srcDir"].split('/')[-2], proper=True)
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


def computeMaxInterval(matrices_csvpath, dimensions, limit=None):

  """
     matrices_csvpath: the file path to the matrices.csv file.
     dimensions: the dimensions of the images, assumes all images have the same dimensions.
     limit: defaults to None; if it's integer, stop parsing X,Y at that many sections.
  """
  if os.path.exists(matrices_csvpath):
    with open(matrices_csvpath, 'r') as csvfile:
      reader = csv.reader(csvfile, delimiter=',', quotechar='"')
      # First line contains parameter names, second line their values
      headerParams = reader.next(), reader.next()
      # skip header with column names
      headerColumnNames = reader.next()
      # Find the lowest coordinate and the highest coordinate
      minX, minY, maxX, maxY = 0, 0, 0, 0
      maxZ = -1
      for row in reader:
        if not limit or maxZ <= limit:
          values = map(float, row)
          minX = min(minX, values[2])
          minY = min(minY, values[5])
          maxX = max(maxX, values[2])
          maxY = max(maxY, values[5])
        maxZ += 1
      return FinalInterval([int(minX), int(minY), 0], [int(dimensions[0]+ maxX + 0.5), int(dimensions[1] + maxY + 0.5), maxZ])
  else:
    print "File does not exist: ", matrices_csvpath


def export8bitN5(*args, **kwargs):
  kwargs["as8bit"] = True
  return exportN5(*args, **kwargs)

def exportN5(filepaths,
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
            block_size=[128,128,128],
            as8bit=False,
            display_range_crop_roi=None): # an ROI to measure min and max from the histogram
  """
  Export into an N5 volume, in parallel, in 8-bit or 16-bit

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
  as8bit: defaults to False.
  """

  dims = Intervals.dimensionsAsLongArray(interval)
  voldims = [dims[0],
             dims[1],
             len(filepaths)]
  cell_dimensions = [dims[0],
                     dims[1],
                     1]

  def asNormalizedUnsignedArrayImg(as8bit, interval, invert, blockRadius, n_bins, slope, matrices, display_range_crop_roi, index, imp): # index and imp must always be the last arguments
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

    # Normalize: with Contrast Limited Adaptive Histogram Equalization
    if blockRadius and n_bins and slope:
      CLAHE.run(ImagePlus("", sp), blockRadius, n_bins, slope, None) # far less memory requirements than NormalizeLocalContrast, and faster.
 
    # Transform
    img = ArrayImgs.unsignedShorts(sp.getPixels(), [sp.getWidth(), sp.getHeight()])
    imp = None
    # Must use linear interpolation for subpixel precision
    affine = AffineTransform2D()
    affine.set(matrices[index])
    imgI = Views.interpolate(Views.extendZero(img), NLinearInterpolatorFactory())
    imgA = RealViews.transform(imgI, affine)
    imgT = Views.zeroMin(Views.interval(imgA, img))
    
    # Convert to 8-bit, mapping to display range
    if as8bit:
      if display_range_crop_roi:
        sp.setRoi(display_range_crop_roi)
        spCrop = sp.crop() # returns a new ImageProcessor
        minimum, maximum = autoAdjust(spCrop)
      else:
        minimum, maximum = autoAdjust(sp)
      # syncPrint("Image -> " + str(index) + " ; minimum pixel value: " + str(minimum) + " ; maximum pixel value: " + str(maximum))
      imgMinMax = convert2(imgT, RealUnsignedByteConverter(minimum, maximum), UnsignedByteType, randomAccessible=True) # use IterableInterval
      aimg = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(img))
    else:
      imgMinMax = imgT
      aimg = ArrayImgs.unsignedShorts(Intervals.dimensionsAsLongArray(img))
    
    # ImgUtil copies multi-threaded, which is not appropriate here as there are many other images being copied too
    #ImgUtil.copy(ImgView.wrap(imgMinMax, aimg.factory()), aimg)
    
    # Single-threaded copy
    #copier = createBiConsumerTypeSet(UnsignedByteType)
    #LoopBuilder.setImages(imgMinMax, aimg).forEachPixel(copier)

    # Use my own copier, which actually works
    ImgMath.compute(imgMinMax).into(aimg)
    
    img = imgI = imgA = imgMinMax = imgT = sp = None
    return aimg
  
  blockRadius, n_bins, slope = CLAHE_params if CLAHE_params else [None, None, None]

  # A CacheLoader that interprets the list of filepaths as a 3D volume: a stack of 2D slices
  loader = SectionCellLoader(filepaths,
                             asArrayImg=partial(asNormalizedUnsignedArrayImg, as8bit, interval, invert, blockRadius, n_bins, slope, matrices, display_range_crop_roi),
                             loadFn=loadFn)

  t = UnsignedByteType if as8bit else UnsignedShortType
  nt = BYTE if as8bit else SHORT
    
  cachedCellImg = lazyCachedCellImg(loader, voldims, cell_dimensions, t, nt)

  exe_preloader = newFixedThreadPool(n_threads=min(block_size[2], n5_threads if n5_threads > 0 else numCPUs()), name="preloader")


  # How to preload block_size[2] files at a time? Or at least as many as numCPUs()?
  # One possibility is to query the SoftRefLoaderCache.map for its entries, using a ScheduledExecutorService,
  # and preload sections ahead for the whole blockSize[2] dimension.

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


class SetStackSlice(Runnable):
  def __init__(self, imp):
    self.imp = imp
    self.stack_slice = imp.getSlice()
  def setFromTableCell(self, rowIndex, colIndex, value):
    if 2 == colIndex:
      return # ignore number of pointmatches
    self.stack_slice = value + 1 # stack slices are 1-based
  def run(self):
    if self.imp.getSlice() != self.section_index:
      self.imp.setSlice(self.section_index)


def qualityControl(filepaths, csvDir, params, properties, paramsTileConfiguration, imp=None):
  """
     Show a 3-column table with the indices of all compared pairs of sections and their pointmatches.
  """

  rows = []
  
  """
  for task in loadPointMatchesTasks(filepaths, csvDir, params, paramsTileConfiguration["n_adjacent"]):
    i, j, pointmatches = task.call() # pointmatches is a list
    rows.append([i, j, len(pointmatches)])
    syncPrintQ("Counting pointmatches for sections %i::%i = %i" % (i, j, len(pointmatches)))
  """

  # Same, in parallel:
  w = ParallelTasks("loadPointMatches")
  for i, j, pointmatches in w.chunkConsume(properties["n_threads"],
                                           loadPointMatchesTasks(filepaths, csvDir, params, paramsTileConfiguration["n_adjacent"]), properties):
    rows.append([i, j, len(pointmatches)])
    syncPrintQ("Counting pointmatches for sections %i::%i = %i" % (i, j, len(pointmatches)))
  w.awaitAll()
  w.destroy()
  
  if imp is None:
    img_title = properties["srcDir"].split('/')[-2]
    imp = WindowManager.getImage(img_title)
    destroy = None
    setStackSlice = None
  
  print imp
  
  if imp:
    ob = SetStackSlice(imp)
    exe = Executors.newSingleThreadScheduledExecutor()
    exe.scheduleWithFixedDelay(ob, 0, 500, TimeUnit.MILLISECONDS)
  else:
    print "image titled %s is not open." % img_title
  
  table, frame = showTable(rows,
                           column_names=["section i", "section j", "n_pointmatches"],
                           title="Number of pointmatches",
                           onCellClickFn=ob.setFromTableCell)
  frame.addWindowListener(ExecutorCloser(exe))

  return table, frame
 

def samplePointMatches(pointmatches, maximum=1000):
  """
  For TranslationModel2D, even just 1 PointMatch suffices, if correct.
  Reduce collections of PointMatch instances by measuring the Euclidian distance
  between correspondences P1 and P2, sort them all by that distance,
  and return the subset (up to maximum pointmatches) around the median distance.
  """
  
  if len(pointmatches) < maximum:
    return pointmatches
  
  # Else sort by distance, and pick the middle range of points
  ls = []
  for pm in pointmatches:
    ls.append((Point.squareDistance(pm.getP1(), pm.getP2()), pm))
  ls.sort(key=itemgetter(0))
  
  # Take the middle chunk
  trim = int((len(ls) - maximum) / 2)
  return map(itemgetter(1), ls[trim:trim+maximum])



def computeShifts(groupNames, csvDir, threshold, params, properties, shifts_filename):
  """
  For each groupName,
  reads the pointmatches file in csvDir with its subsequent section only (ignoring the rest),
  takes the median subset via samplePointMatches,
  then computes the translation via fitting a TransformModel2D,
  determines whether the translation is bigger than threshold,
  and prints a list of translations for each section to be used as section shifts.
  
  These shifts are useful for re-rendering images prior to re-extracting features,
  to avoid large shifts that the optimizer would need a lot of iterations to resolve.
  """
  with open(os.path.join(csvDir, shifts_filename), 'w') as f:
    for j in xrange(len(groupNames)):
      if 0 == j:
        continue
      # Load pointmatches
      i, j, pointmatches = loadPointMatchesPlus(groupNames, j-1, j, csvDir, params, properties)
      # Compute translation model
      model = TranslationModel2D()
      modelFound = model.fit(pointmatches)
      # Extract translation
      matrix = zeros(6, 'd')
      model.toArray(matrix)
      dx = matrix[4]
      dy = matrix[5]
      # If larger than 1 pixel in X or Y, consider this a shift
      if abs(dx) > threshold or abs(dy) > threshold:
        s = "[%i, %i, %.1f, %.1f, '%s.%s']," % (i, j, dx, dy, groupNames[i], groupNames[j])
        syncPrintQ(s)
        f.write(s)
        f.write('\n')





















