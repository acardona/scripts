from net.imglib2 import FinalInterval
from net.imglib2.img.array import ArrayImgs
from net.imglib2.img import ImgView
from net.imglib2.util import Intervals, ImgUtil
from net.imglib2.realtransform import Scale3D, AffineTransform3D, RealViews
from net.imglib2.img.io import Load
from net.imglib2.view import Views
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
import os, re, sys
from pprint import pprint
from itertools import izip, chain, repeat
from operator import itemgetter
from util import newFixedThreadPool, Task, syncPrint, affine3D
from io import readFloats, writeZip, KLBLoader, TransformedLoader, ImageJLoader
from registration import computeForwardTransforms, saveMatrices, loadMatrices, asBackwardConcatTransforms, viewTransformed, transformedView
from deconvolution import multiviewDeconvolution, prepareImgForDeconvolution, transformPSFKernelToView

from net.imglib2.img.display.imagej import ImageJFunctions as IL


def deconvolveTimePoints(srcDir,
                         targetDir,
                         kernel_filepath,
                         calibration,
                         cameraTransformations,
                         fineTransformsPostROICrop,
                         params,
                         roi,
                         subrange=None,
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
     kernel_filepath: file path to the 3D image of the point spread function (PSF),
                      which can be computed from fluorescent beads with the BigStitcher functions
                      and which must have odd dimensions.
     calibration: the array of [x, y, z] dimensions.
     camera_transformations: a map of camera index vs the 12-digit 3D affine matrices describing
                             the transform to register the camera view onto the camera at index 0.
     fineTransformsPostROICrop: a list of the transform matrices to be applied after both the coarse transform and the ROI crop.
     params: a dictionary with all the necessary parameters for feature extraction, registration and deconvolution.
     roi: the min and max coordinates for cropping the coarsely registered volumes prior to registration and deconvolution.
     subrange: defaults to None. Can be a list specifying the indices of time points to deconvolve.
  """
  kernel = readFloats(kernel_filepath, [19, 19, 25], header=434)
  klb_loader = KLBLoader()

  def getCalibration(img_filename):
    return calibration

  # Regular expression pattern describing KLB files to include
  pattern = re.compile("^SPM00_TM\d+_CM(\d+)_CHN0[01]\.klb$")

  exe = newFixedThreadPool(n_threads=n_threads)

  # Find all time point folders with pattern TM\d{6} (a TM followed by 6 digits)
  def iterTMs():
    """ Return a generator over dicts of 4 KLB file paths for each time point. """
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
  for filepaths in TMs:
    if 4 != len(filepaths):
      print "Folder %s has problems: found %i KLB files in it instead of 4." % (tm_dir, len(filepaths))
      print "Address the issues and rerun."
      return

  print "Will process these timepoints:",
  for i, TM in enumerate(TMs):
    print i
    pprint(TM)

  # dimensions: all images from each camera have the same dimensions
  dimensions = [Intervals.dimensionsAsLongArray(klb_loader.get(filepath))
                for index, filepath in sorted(TMs[0].items(), key=itemgetter(0))]

  # All OK, submit all timepoint folders for registration and deconvolution 
  
  # Prepare coarse transforms ("cm" prefix means camera)
  def prepareCoarseTransforms():
    cmTransforms = cameraTransformations(dimensions[0], dimensions[1], dimensions[2], dimensions[3], calibration)
    scale3D = AffineTransform3D()
    scale3D.set(calibration[0], 0.0, 0.0, 0.0,
                0.0, calibration[1], 0.0, 0.0,
                0.0, 0.0, calibration[2], 0.0)
    
    cmIsotropicTransforms = []
    for camera_index in sorted(cmTransforms.keys()):
      aff = AffineTransform3D()
      aff.set(*cmTransforms[camera_index])
      aff.concatenate(scale3D)
      cmIsotropicTransforms.append(aff)
    return cmTransforms, cmIsotropicTransforms

  # matrices, AffineModel3D instances
  cmTransforms, cmIsotropicTransforms = prepareCoarseTransforms()
  
  # Create target folder for storing deconvolved images
  if not os.path.exists(os.path.join(targetDir, "deconvolved")):
    os.mkdir(os.path.join(targetDir, "deconvolved"))

  # Transform kernel to each view
  matrices = fineTransformsPostROICrop

  """
  # Concatenate coarse transforms with fine transformation matrices
  def concat(aff, matrix):
    t = AffineTransform3D()
    t.set(aff)
    aff1 = AffineTransform3D()
    aff1.set(*matrix)
    aff1 = aff1.inverse() # THIS WAS MISSING: matrices contain forward transforms, e.g. CM00->CM01, not CM01->cM00.
    t.preConcatenate(aff1)
    return t
  
  # Can't: the cropping by ROI introduces translations not accounted for in the matrices
  transforms = [concat(cmIsotropicTransforms[0], matrices[0]),
                concat(cmIsotropicTransforms[1], matrices[1]),
                concat(cmIsotropicTransforms[2], matrices[2]),
                concat(cmIsotropicTransforms[3], matrices[3])]
  """

  print "cmTransforms:", cmTransforms

  # For the PSF kernel, transforms without the scaling up to isotropy
  # No need to account for the translation: the transformPSFKernelToView keeps the center point centered.
  PSF_kernels = [transformPSFKernelToView(kernel, affine3D(cmTransforms[i])) for i in xrange(4)]
  PSF_kernels = [transformPSFKernelToView(k, affine3D(matrix).inverse()) for k, matrix in izip(PSF_kernels, matrices)]
  # TODO: if kernels are not ArrayImg, they should be made be.
  print "PSF_kernel[0]:", PSF_kernels[0], type(PSF_kernels[0])

  """
  # WRONG, can't concate these: the translation is not accounted for.
  transformsPSF = [concat(affine3D(cmTransforms[0]), matrices[0]),
                   concat(affine3D(cmTransforms[1]), matrices[1]),
                   concat(affine3D(cmTransforms[2]), matrices[2]),
                   concat(affine3D(cmTransforms[3]), matrices[3])]

  # Transform the kernel with the affine of the view, without the scaling to isotropy
  PSF_kernels = [transformPSFKernelToView(kernel, t) for t in transformsPSF]
  """
  
  # DEBUG: write the kernelA
  for index in [0, 1, 2, 3]:
    writeZip(PSF_kernels[index], "/tmp/kernel" + str(index) + ".zip", title="kernel" + str(index))
  
  # Submit for registration + deconvolution
  # The registration uses 2 parallel threads, and deconvolution all possible available threads.
  # Cannot invoke more than one time point at a time because the deconvolution requires a lot of memory.
  for i, filepaths in enumerate(TMs):
    syncPrint("Deconvolving time point %i with files:\n  %s" %(i, "\n  ".join(sorted(filepaths.itervalues()))))
    deconvolveTimePoint(filepaths, targetDir, klb_loader, getCalibration,
                        cmIsotropicTransforms, roi, fineTransformsPostROICrop, params, PSF_kernels, exe)
  
  # Register deconvolved time points
  deconvolved_csv_dir = os.path.join(targetDir, "deconvolved/csvs")
  if not os.path.exists(deconvolved_csv_dir):
    os.mkdir(deconvolved_csv_dir)
  # TODO


def deconvolveTimePoint(filepaths, targetDir, klb_loader, getCalibration,
                        cmIsotropicTransforms, roi, fineTransformsPostROICrop, params, PSF_kernels,
                        exe, write=writeZip):
  """ filepaths is a dictionary of camera index vs filepath to a KLB file.
      This function will generate two deconvolved views, one for each channel,
      where CHN00 is made of CM00 + CM01, and
            CHNO1 is made of CM02 + CM03.
      Will take the camera registrations (cmIsotropicTransforms), which are coarse,
      apply them to the images, then crop the images, then apply the fine transformations.
      If the deconvolved images exist, it will neither compute it nor write it."""
  tm_dirname = filepaths[0][filepaths[0].rfind("_TM") + 1:filepaths[0].rfind("_CM")]
  
  def deconvolveAndSave(indices):
    name = "CM0%i-CM0%i-deconvolved" % indices
    syncPrint("Invoked deconvolveAndSave for indices %i, %i" % indices)
    filename = tm_dirname + "_" + name + ".zip"
    path = os.path.join(targetDir, "deconvolved/" + filename)
    if not os.path.exists(path):
      images = []
      for index in indices:
        # Prepare the img:
        # 0. Transform in two (three) steps:
        #    first transform with coarse cmIsotropicTransform,
        #    then crop to ROI,
        #    then with the inverse of the fineTransformsPostRoiCrop matrices.
        # 1. Ensure its pixel values conform to expectations (no zeros inside)
        # 2. Copy it into an ArrayImg for faster recurrent retrieval of same pixels
        syncPrint("Working now on %s CM0%i" % (tm_dirname, index))
        img = klb_loader.get(filepaths[index])
        imgE = Views.extendZero(img)
        imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
        imgT = RealViews.transform(imgI, cmIsotropicTransforms[index])
        imgB = Views.zeroMin(Views.interval(imgT, roi[0], roi[1])) # bounded: crop with ROI
        imgP = prepareImgForDeconvolution(imgB,
                                          affine3D(fineTransformsPostROICrop[index]).inverse(),
                                          FinalInterval([0, 0, 0],
                                                        [imgB.dimension(d) -1 for d in xrange(3)]))
        # Copy transformed view into ArrayImg for best performance in deconvolution
        imgA = ArrayImgs.floats(Intervals.dimensionsAsLongArray(imgP))
        ImgUtil.copy(ImgView.wrap(imgP, imgA.factory()), imgA)
        images.append(imgA)
        syncPrint("--Completed copying transformed and prepared image into ArrayImg.")

      # DEBUG: save the images
      if tm_dirname == "TM000000":
        try:
          #for i, img in zip(indices, images):
          #  writeZip(img, "/tmp/" + "pre_deconv__" + tm_dirname + "_CM0" + str(i) + "-PREPARED.zip", title="CM" + str(i))
          # DEBUG: show the registered images into a hyperstack
          IL.wrap(Views.stack(images), "stack %i-%i" % indices).show()
        except:
          print sys.exc_info()
      
      #if True:
      #  return None # DEBUG
      
      # Deconvolve: merge two views into a single volume
      n_iterations = params["CM_%i_%i_n_iterations" % indices]
      img = multiviewDeconvolution(images, params["blockSize"], PSF_kernels, n_iterations, exe=exe)
      writeZip(img, path, title=filename)

  deconvolveAndSave((0, 1))
  deconvolveAndSave((2, 3))



# TODO NEEDS UPDATE, both channels are now registered to CM00
def registerDeconvolvedTimePoints(srcDir,
                                  targetDir,
                                  params,
                                  modelclass,
                                  exe):
  """ Can only be run after running deconvolveTimePoints, because it
      expects deconvolved images to exist under targetDir/deconvolved/,
      with a name pattern like: TM_\d+_CM0\d_CM0\d-deconvolved.zip
      
      Tests if files exist first, if not, will stop execution.
      
      Returns an imglib2 4D img with the registered deconvolved 3D stacks. """

  csv_dir = os.path.join(target_dir, "deconvolved/csvs/")
  if not os.path.exists(csv_dir):
    os.mkdir(csv_dir)
  
  deconvolved_filepaths_0_1 = []
  deconvolved_filepaths_2_3 = []
  for tm_dirname in sorted(os.listdir(srcDir)):
    if tm_dirname.startswith("TM00"):
      path_0_1 = os.path.join(targetDir, "deconvolved/" + tm_dirname + "_CM00-CM01-deconvolved.zip")
      if not os.path.exists(path_0_1):
        print "File does not exists: ", path_0_1
        return
      path_2_3 = os.path.join(targetDir, "deconvolved/" + tm_dirname + "_CM02-CM03-deconvolved.zip")
      if not os.path.exists(path_2_3):
        print "File does not exists: ", path_2_3
        return
      deconvolved_filepaths_0_1.append(path_0_1)
      deconvolved_filepaths_2_3.append(path_2_3)

  # Deconvolved images are isotropic
  def getCalibration(img_filepath):
    return [1, 1, 1]

  # Register all path_0_1 to each other, then register each path_2_3 to each path_0_1
  matrices_0_1_name = "matrices_CM00_CM01"
  if os.path.exists(os.path.join(csv_dir, matrices_0_1_name + ".csv")):
    matrices_0_1 = loadMatrices(matrices_0_1_name, csv_dir)
  else:
    # Deconvolved images are opened with ImageJ: they are zipped tiff stacks.
    matrices_0_1_fwd = computeForwardTransforms(filepaths_0_1, ImageJLoader(), getCalibration,
                                                deconvolved_csv_dir, exe, modelclass, params, exe_shutdown=False)
    matrices_0_1 = [affine.getRowPackedCopy() for affine in asBackwardConcatTransforms(matrices_0_1_fwd)]
    saveMatrices(matrices_0_1_filename, matrices_0_1, csv_dir)

  # Register each deconvolved 2_3 volume to its corresponding 0_1
  matrices_2_3_name = "matrices_CM02_CM03"
  if os.path.exists(os.path.join(csv_dir, matrices_2_3_name + ".csv")):
    matrices_2_3 = loadMatrices(matrices_2_3_name, csv_dir)
  else:
    futures = []
    for pair_filepaths in izip(filepaths_0_1, filepaths_2_3):
      futures.append(exe.submit(Task, computeForwardTransforms, pair_filepaths, ImageJLoader(), getCalibration,
                                deconcolved_csv_dir, exe, modelclass, params, exe_shutdown=False))
    matrices_2_3 = []
    # Invert and concatenate the transforms
    for i, f in enumerate(futures):
      _, matrix_2_3_fwd = f.get() # first one is the identity
      aff_0_1 = AffineTransform3D()
      aff_0_1.set(*matrices_0_1[i])
      aff_2_3 = AffineTransform3D()
      aff_2_3.set(*matrix_2_3_fwd)
      aff_2_3 = aff_2_3.inverse()
      aff_2_3.preConcatenate(aff_0_1)
      matrices_2_3.append(aff_2_3.getRowPackedCopy())
    saveMatrices(matrices_2_3_name, matrices_2_3, csv_dir)

  # Show the registered deconvolved series as a 4D volume.
  affines = []
  for pair in izip(matrices_0_1, matrices_2_3):
    for matrix in pair:
      aff = AffineTransform3D()
      aff.set(*matrix_0_1)
      affines.append(aff)

  filepaths = list(chain.from_iterable(izip(deconvolved_filepaths_0_1, deconvolved_filepaths_2_3)))
  img = Load.lazyStack(filepaths, TransformedLoader(ImageJLoader(), dict(izip(filepaths, affines))))
  return img

