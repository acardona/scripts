from net.imglib2 import FinalInterval
from net.imglib2.img.array import ArrayImgs
from net.imglib2.img import ImgView
from net.imglib2.util import Intervals, ImgUtil
from net.imglib2.realtransform import Scale3D, AffineTransform3D, RealViews
from net.imglib2.img.io import Load
from net.imglib2.view import Views
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.type.numeric.integer import UnsignedShortType
from java.util.concurrent import TimeUnit
import os, re, sys
from pprint import pprint
from itertools import izip, chain, repeat
from operator import itemgetter
from util import newFixedThreadPool, Task, syncPrint, affine3D
from io import readFloats, writeZip, KLBLoader, TransformedLoader, ImageJLoader
from registration import computeOptimizedTransforms, saveMatrices, loadMatrices, asBackwardConcatTransforms, viewTransformed, transformedView, mergeTransforms
from deconvolution import multiviewDeconvolution, prepareImgForDeconvolution, transformPSFKernelToView
from converter import convert, createConverter
from collections import defaultdict
from java.lang import Runtime, Thread

from net.imglib2.img.display.imagej import ImageJFunctions as IL


def deconvolveTimePoints(srcDir,
                         targetDir,
                         kernel_filepaths,
                         calibration,
                         cameraTransformations,
                         fineTransformsPostROICrop,
                         params,
                         roi,
                         subrange=None,
                         camera_groups=((0, 1), (2, 3)),
                         kernel_dimensions=[19, 19, 25],
                         kernel_header=434,
                         fine_fwd=False,
                         loader=ImageJLoader(),
                         n_threads=0): # 0 means all
  """
     Main program entry point.
     For each time point folder TM\d+, find the KLB files of the 4 cameras,
     then register them all to camera CM01, and deconvolve CM01+CM02, and CM02+CM03,
     and store these two images in corresponding TM\d+ folders under targetDir.

     Assumes that each camera view has the same dimensions in each time point folder.
     A camera view may have dimensions different from those of the other cameras.

     Can be run as many times as necessary. Intermediate computations are saved
     as csv files (features, pointmatches and transformation matrices), and 
     the deconvolved images as well, into folder targetDir/deconvolved/ with
     a name pattern like TM\d+_CM0\d_CM0\d-deconvolved.zip
     
     srcDir: file path to a directory with TM\d+ subdirectories, one per time point.
     targetDir: file path to a directory for storing deconvolved images
                and CSV files with features, point matches and transformation matrices.
     kernel_filepaths: string (a single file path for all views) or list of strings (one per file path and view)
                       to the 3D image of the point spread function (PSF),
                       which can be computed from fluorescent beads with the BigStitcher functions
                       and which must have odd dimensions.
     calibration: the array of [x, y, z] dimensions.
     cameraTransformations: a function that returns a map of camera index vs the 12-digit 3D affine matrices describing
                            the transform to register the camera view onto the camera at index 0.
     fineTransformsPostROICrop: a list of the transform matrices to be applied after both the coarse transform and the ROI crop.
     params: a dictionary with all the necessary parameters for feature extraction, registration and deconvolution.
     roi: the min and max coordinates for cropping the coarsely registered volumes prior to registration and deconvolution.
     subrange: defaults to None. Can be a list specifying the indices of time points to deconvolve.
     camera_groups: the camera views to fuse and deconvolve together. Defaults to two: ((0, 1), (2, 3))
     kernel_dimensions: defaults to [19, 19, 25]. A list of 3 odd integers defining the dimensions of the kernel stack.
     kernel_header: defaults to 434. The header size of the kernel file, for direct binary parsing.
                    When None, open the kernel file with IJ.openImage.
     fine_fwd: whether the fineTransformsPostROICrop were computed all-to-all, which optimizes the pose and produces direct transforms,
               or, when False, the fineTransformsPostROICrop were computed from 0 to 1, 0 to 2, and 0 to 3, so they are inverted.
     loader: a CacheLoader like lib.io KLBLoader, ImageJLoader, or BinaryLoader
     n_threads: number of threads to use. Zero (default) means as many as possible.
  """
  if str == type(kernel_filepaths): # handle legacy invocations
    kernel_filepaths = [kernel_filepaths]

  def readKernel(path):
    if kernel_header is None:
      imp = IJ.openImage(path)
      return ArrayImgs.floats(imp.getProcessor().getPixels(),
                              [imp.getWidth(), imp.getHeight(), imp.getNSlices()])
    return readFloats(path, kernel_dimensions, kernel_header)

  kernels = map(readKernel, kernel_filepath)
  if 1 == len(kernels):
    # Reuse the same kernel for all views
    kernels = [kernels[0]] * (2 * len(camera_groups))

  def getCalibration(img_filename):
    return calibration

  # Regular expression pattern describing KLB files to include
  pattern = re.compile("^SPM00_TM\d+_CM(\d+)_CHN0[01]\.klb$")

  # Find all time point folders with pattern TM\d{6} (a TM followed by 6 digits)
  def iterTMs():
    """ Return a generator over dicts of KLB file paths for each time point. """
    for dirname in sorted(os.listdir(srcDir)):
      if not dirname.startswith("TM00"):
        continue
      filepaths = {}
      tm_dir = os.path.join(srcDir, dirname)
      for filename in sorted(os.listdir(tm_dir)):
        r = re.match(pattern, filename)
        if r:
          camera_index = int(r.groups()[0])
          filepaths[camera_index] = os.path.join(tm_dir, filename)
      yield filepaths

  if subrange:
    indices = set(subrange)
    TMs = [tm for i, tm in enumerate(iterTMs()) if i in indices]
  else:
    TMs = list(iterTMs())
  
  # Validate folders
  n_expected_files = 2 * len(camera_groups)
  for filepaths in TMs:
    # There can be more, but not less
    if len(filepaths) < n_expected_files:
      print "Folder %s has problems: found %i KLB files in it instead of %i." % (tm_dir, len(filepaths), n_expected_files)
      print "Address the issues and rerun."
      return

  print "Will process these timepoints:",
  for i, TM in enumerate(TMs):
    print i
    pprint(TM)

  # All OK, submit all timepoint folders for registration and deconvolution

  # dimensions: all images from each camera have the same dimensions
  dimensions = [Intervals.dimensionsAsLongArray(loader.get(filepath))
                for index, filepath in sorted(TMs[0].items(), key=itemgetter(0))]

  cmTransforms = cameraTransformations(dimensions[0], dimensions[1], dimensions[2], dimensions[3], calibration)

  # Transforms apply to all time points equally
  #   If fine_fwd, the fine transform was forward.
  #   Otherwise, it was from CM00 to e.g. CM01, so backwards for CM01, needing an inversion.
  transforms = mergeTransforms(calibration, [cmTransforms[i] for i in sorted(cmTransforms.keys())],
                               roi, fineTransformsPostROICrop, invert2=not fine_fwd)
  
  # Create target folder for storing deconvolved images
  if not os.path.exists(os.path.join(targetDir, "deconvolved")):
    os.mkdir(os.path.join(targetDir, "deconvolved"))

  # Transform kernel to each view
  matrices = fineTransformsPostROICrop

  # For the PSF kernel, transforms without the scaling up to isotropy
  # No need to account for the translation: the transformPSFKernelToView keeps the center point centered.
  PSF_kernels = [transformPSFKernelToView(kernels[i], affine3D(cmTransforms[i])) for i in xrange(len(cmTransforms)]
  PSF_kernels = [transformPSFKernelToView(k, affine3D(matrix).inverse()) for k, matrix in izip(PSF_kernels, matrices)]
  # TODO: if kernels are not ArrayImg, they should be made be.
  print "PSF_kernel[0]:", PSF_kernels[0], type(PSF_kernels[0])

  # DEBUG: write the kernelA
  for index in xrange(len(PSF_kernels)):
    path = "/tmp/kernel" + str(index) + ".zip"
    try:
      writeZip(PSF_kernels[index], , title="kernel" + str(index)).flush()
    except:
      print "Error saving kernels to", path
      print sys.exc_info()

  # A converter from FloatType to UnsignedShortType
  output_converter = createConverter(FloatType, UnsignedShortType)

  target_interval = FinalInterval([0, 0, 0],
                                  [maxC - minC for minC, maxC in izip(roi[0], roi[1])])

  exe = newFixedThreadPool(n_threads=n_threads)
  try:
    # Submit for registration + deconvolution
    # The registration uses 2 parallel threads, and deconvolution all possible available threads.
    # Cannot invoke more than one time point at a time because the deconvolution requires a lot of memory.
    for i, filepaths in enumerate(TMs):
      if Thread.currentThread().isInterrupted(): break
      syncPrint("Deconvolving time point %i with files:\n  %s" %(i, "\n  ".join(sorted(filepaths.itervalues()))))
      deconvolveTimePoint(filepaths, targetDir, loader,
                          transforms, target_interval,
                          params, PSF_kernels, exe, output_converter,
                          camera_groups=camera_groups)
  finally:
    exe.shutdown() # Not accepting any more tasks but letting currently executing tasks to complete.
    # Wait until the last task (writing the last file) completes execution.
    exe.awaitTermination(5, TimeUnit.MINUTES)


def deconvolveTimePoint(filepaths, targetDir, loader,
                        transforms, target_interval,
                        params, PSF_kernels, exe, output_converter,
                        camera_groups=((0, 1), (2, 3)),
                        write=writeZip):
  """ filepaths is a dictionary of camera index vs filepath to a KLB file.
      With the default camera_groups=((0, 1), (2, 3)) this function will generate
      two deconvolved views, one for each channel,
      where CHN00 is made of CM00 + CM01, and
            CHNO1 is made of CM02 + CM03.
      Will take the camera registrations (cmIsotropicTransforms), which are coarse,
      apply them to the images, then crop the images, then apply the fine transformations.
      If the deconvolved images exist, it will neither compute it nor write it."""
  tm_dirname = filepaths[0][filepaths[0].rfind("_TM") + 1:filepaths[0].rfind("_CM")]

  n_threads = max(1, Runtime.getRuntime().availableProcessors() -1)

  def prepare(index):
    # Prepare the img for deconvolution:
    # 0. Transform in one step.
    # 1. Ensure its pixel values conform to expectations (no zeros inside)
    # 2. Copy it into an ArrayImg for faster recurrent retrieval of same pixels
    syncPrint("Preparing %s CM0%i for deconvolution" % (tm_dirname, index))
    img = loader.get(filepaths[index]) # of UnsignedShortType
    imgP = prepareImgForDeconvolution(img, transforms[index], target_interval) # returns of FloatType
    # Copy transformed view into ArrayImg for best performance in deconvolution
    imgA = ArrayImgs.floats(Intervals.dimensionsAsLongArray(imgP))
    #ImgUtil.copy(ImgView.wrap(imgP, imgA.factory()), imgA)
    ImgUtil.copy(imgP, imgA, n_threads / 2) # parallel copying
    syncPrint("--Completed preparing %s CM0%i for deconvolution" % (tm_dirname, index))
    imgP = None
    img = None
    return (index, imgA)

  def strings(indices):
    cameras = "-".join("CM0%i" % i for i in indices)
    name = cameras + "-deconvolved"
    filename = tm_dirname + "_" + name + ".zip"
    path = os.path.join(targetDir, "deconvolved/" + filename)
    return filename, path

  # Find out which pairs haven't been created yet
  futures = []
  todo = []
  for indices in camera_groups:
    filename, path = strings(indices)
    if not os.path.exists(path):
      todo.append(indices)
      for index in indices:
        futures.append(exe.submit(Task(prepare, index)))

  # Dictionary of index vs imgA
  prepared = dict(f.get() for f in futures)

  def writeToDisk(writeZip, img, path, title=''):
    writeZip(img, path, title=title).flush() # flush the returned ImagePlus

  # Each deconvolution run uses many threads when run with CPU
  # So do one at a time.
  last_future = None
  for indices in todo:
    if Thread.currentThread().isInterrupted(): break
    images = [prepared[index] for index in indices]
    syncPrint("Invoked deconvolution for %s %s" % (tm_dirname, " ".join("%i" % i for i in indices)))
    # Deconvolve: merge two views into a single volume
    n_iterations = params["CM_%s_n_iterations" % "_".join("%i" % i for i in indices)]
    img = multiviewDeconvolution(images, params["blockSizes"], PSF_kernels, n_iterations, exe=exe)
    # On-the-fly convert to 16-bit: data values are well within the 16-bit range
    imgU = convert(img, output_converter, UnsignedShortType)
    filename, path = strings(indices)
    # Write in a separate thread so as not to wait
    last_future = exe.submit(Task(writeToDisk, writeZip, imgU, path, title=filename))
    imgU = None
    img = None
    images = None

  if last_future:
    last_future.get()

  prepared = None




def registerDeconvolvedTimePoints(targetDir,
                                  params,
                                  modelclass,
                                  exe=None,
                                  verbose=True,
                                  subrange=None):
  """ Can only be run after running deconvolveTimePoints, because it
      expects deconvolved images to exist under <targetDir>/deconvolved/,
      with a name pattern like: TM_\d+_CM0\d_CM0\d-deconvolved.zip
      
      Tests if files exist first, if not, will stop execution.

      Will write the features, pointmatches and registration affine matrices
      into a csv folder under targetDir.

      If a CSV file with the affine transform matrices exist, it will read them out
      and provide the 4D img right away.
      Else, it will check which files are missing their features and pointmatches as CSV files,
      create them, and ultimately create the CSV filew ith the affine transform matrices,
      and then provide the 4D img.

      targetDir: the directory containing the deconvolved images.
      params: for feature extraction and registration.
      modelclass: the model to use, e.g. Translation3D, AffineTransform3D.
      exe: the ExecutorService to use (optional).
      subrange: the range of time point indices to process, as enumerated
                by the folder name, i.e. the number captured by /TM(\d+)/
      
      Returns an imglib2 4D img with the registered deconvolved 3D stacks."""

  deconvolvedDir = os.path.join(targetDir, "deconvolved")
  
  # A folder for features, pointmatches and matrices in CSV format
  csv_dir = os.path.join(deconvolvedDir, "csvs")
  if not os.path.exists(csv_dir):
    os.mkdir(csv_dir)

  # A datastructure to represent the timepoints, each with two filenames
  timepoint_views = defaultdict(defaultdict)
  pattern = re.compile("^TM(\d+)_(CM0\d-CM0\d)-deconvolved.zip$")
  for filename in sorted(os.listdir(deconvolvedDir)):
    m = re.match(pattern, filename)
    if m:
      stime, view = m.groups()
      timepoint_views[int(stime)][view] = filename

  # Filter by specified subrange, if any
  if subrange:
    subrange = set(subrange)
    for time in timepoint_views.keys(): # a list copy of the keys, so timepoints can be modified
      if time not in subrange:
        del timepoint_views[time]

  # Register only the view CM00-CM01, given that CM02-CM03 has the same transform
  matrices_name = "matrices-%s" % modelclass.getSimpleName()
  matrices = None
  if os.path.exists(os.path.join(csv_dir, matrices_name + ".csv")):
    matrices = loadMatrices(matrices_name, csv_dir)
    if len(matrices) != len(timepoint_views):
      syncPrint("Ignoring existing matrices CSV file: length (%i) doesn't match with expected number of timepoints (%i)" % (len(matrices), len(timepoint_views)))
      matrices = None
  if not matrices:
    original_exe = exe
    if not exe:
      exe = newFixedThreadPool()
    try:
      # Deconvolved images are isotropic
      def getCalibration(img_filepath):
        return [1, 1, 1]
      timepoints = [] # sorted
      filepaths = [] # sorted
      for timepoint, views in sorted(timepoint_views.iteritems(), key=itemgetter(0)):
        timepoints.append(timepoint)
        filepaths.append(os.path.join(deconvolvedDir, views["CM00-CM01"]))
      #
      #matrices_fwd = computeForwardTransforms(filepaths, ImageJLoader(), getCalibration,
      #                                        csv_dir, exe, modelclass, params, exe_shutdown=False)
      #matrices = [affine.getRowPackedCopy() for affine in asBackwardConcatTransforms(matrices_fwd)]
      matrices = computeOptimizedTransforms(filepaths, ImageJLoader(), getCalibration,
                                            csv_dir, exe, modelclass, params, verbose=verbose)
      saveMatrices(matrices_name, matrices, csv_dir)
    finally:
      if not original_exe:
        exe.shutdownNow() # Was created new
  
  # Convert matrices into twice as many affine transforms
  affines = []
  for matrix in matrices:
    aff = AffineTransform3D()
    aff.set(*matrix)
    affines.append(aff)
    affines.append(aff) # twice: also for the CM02-CM03
  
  # Show the registered deconvolved series as a 4D volume.
  filepaths = []
  for timepoint in sorted(timepoint_views.iterkeys()):
    views = timepoint_views.get(timepoint)
    for view_name in sorted(views.keys()): # ["CM00-CM01", "CM02-CM03"]
      filepaths.append(os.path.join(deconvolvedDir, views[view_name]))
  
  img = Load.lazyStack(filepaths, TransformedLoader(ImageJLoader(), dict(izip(filepaths, affines)), asImg=True))
  return img

