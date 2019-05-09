from net.imglib2 import FinalInterval
from net.imglib2.img.array import ArrayImgFactory
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.view import Views
from net.imglib2.util import Intervals
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.realtransform import RealViews, AffineTransform3D
from net.preibisch.mvrecon.process.deconvolution import MultiViewDeconvolutionSeq, DeconView, DeconViews, MultiViewDeconvolution
from net.preibisch.mvrecon.process.deconvolution.iteration.sequential import ComputeBlockSeqThreadCPUFactory, ComputeBlockSeqThreadCUDAFactory
from net.preibisch.mvrecon.process.deconvolution.init import PsiInitBlurredFusedFactory
from net.preibisch.mvrecon.process.deconvolution.DeconViewPSF import PSFTYPE
from net.preibisch.mvrecon.process.fusion.transformed import TransformView
from net.preibisch.mvrecon.process.psf import PSFExtraction
from net.preibisch.mvrecon.process.cuda import CUDAFourierConvolution, CUDATools, NativeLibraryTools
from com.sun.jna import Native
from bdv.util import ConstantRandomAccessible
from java.util import ArrayList, HashMap
from itertools import repeat, izip
# local lib functions:
from util import newFixedThreadPool, syncPrint
import os


def setupEngine(use_cuda=True, askForMultipleDevices=False):
  """
  Attempt to load the CUDA libraries. Otherwise use CPU threads.
  Return a function that creates the ComputeBlockSeqThread(CPU|CUDA)Factory.

  For the CUDA version to work, do, in Ubuntu 16.04:
   1. Download the .deb file for CUDA 10.0 from:
     https://developer.nvidia.com/compute/cuda/10.0/Prod/local_installers/cuda-repo-ubuntu1604-10-0-local-10.0.130-410.48_1.0-1_amd64
   2. Install the CUDA deb package and more:
      $ sudo dpkg -i cuda-repo-ubuntu1604-10-0-*deb
      $ sudo apt-key add /var/cuda-repo-10-0-local-10.0.130-410.48/7fa2af80.pub
      $ sudo apt-get update
      $ sudo apt-get install cuda
   3. Download the FourierConvolutionCUDALib from:
     https://github.com/StephanPreibisch/FourierConvolutionCUDALib
   4. Install it:
      $ cd FourierConvolutionCUDALib/
      $ mkdir build
      $ cd build
      $ cmake ..
      $ make
      $ sudo make install
  """
  cuda = None
  devices = []
  idToCudaDevice = {}
  if use_cuda:
    so_paths = ["/usr/local/lib/libFourierConvolutionCUDALib.so",
                "/groups/cardona/home/championa/code/FourierConvolutionCUDALib/build-cuda-8-master/src/libFourierConvolutionCUDALib.so"] 
    for so_path in so_paths:
      if os.path.exists(so_path):
        # Still opens a dialog to ask for the one and only existing library
        #cuda = NativeLibraryTools.loadNativeLibrary(ArrayList(["FourierConvolutionCuda"]), File(so_path), CUDAFourierConvolution)
        cuda = Native.loadLibrary(so_path, CUDAFourierConvolution)
        break
    if not cuda:
      # Fire up file dialogs:
      cuda = NativeLibraryTools.loadNativeLibrary(ArrayList(["fftCUDA", "FourierConvolutionCuda"]), CUDAFourierConvolution)
    if not cuda:
      syncPrint("Could not load CUDA JNA library for FFT convolution.")
    else:
      syncPrint("Will use CUDA for FFT convolution.")
      devices = CUDATools.queryCUDADetails(cuda, askForMultipleDevices)
      idToCudaDevice = {index: device for index, device in enumerate(devices)}
  # Return function
  def createFactoryFn(exe, lambda_val, blockSize):
    if use_cuda and cuda:
      return ComputeBlockSeqThreadCUDAFactory(exe, MultiViewDeconvolution.minValue, lambda_val, blockSize, cuda, HashMap(idToCudaDevice))
    else:
      return ComputeBlockSeqThreadCPUFactory(exe, MultiViewDeconvolution.minValue, lambda_val, blockSize, ArrayImgFactory(FloatType()))

  return createFactoryFn

# Define function, having potentially loaded the native CUDA library
createFactory = setupEngine(use_cuda=False)


def multiviewDeconvolution(images, blockSizes, PSF_kernels, n_iterations, lambda_val=0.0006, weights=None,
                           filterBlocksForContent=False, PSF_type=PSFTYPE.INDEPENDENT, exe=None, printFn=syncPrint):
  """
  Apply Bayesian-based multi-view deconvolution to the list of images,
  returning the deconvolved image. Uses Stephan Preibisch's library,
  currently available with the BigStitcher Fiji update site.

  images: a list of images, registered and all with the same dimensions.
  blockSizes: how to chop up the volume of each image for parallel processing.
             When None, a single block with the image dimensions is used,
             plus half of the transformed kernel dimensions for that view.
  PSF_kernels: the images containing the point spread function for each input image. Requirement: the dimensions must be an odd number.
  n_iterations: the number of iterations for the deconvolution. A number between 10 and 50 is desirable. The more iterations, the higher the computational cost.
  lambda_val: default is 0.0006 as recommended by Preibisch.
  weights: a list of FloatType images with the weight for every pixel. If None, then all pixels get a value of 1.
  filterBlocksForContent: whether to check before processing a block if the block has any data in it. Default is False.
  PSF_type: defaults to PSFTYPE.INDEPENDENT.
  exe: a thread pool for concurrent execution. If None, a new one is created, using as many threads as CPUs are available.
  printFn: the function to use for printing error messages. Defaults to syncPrint (thread-safe access to the built-in `print` function).

  Returns an imglib2 ArrayImg, or None if something went wrong.
  """

  mvd_exe = exe
  if not exe:
    mvd_exe = newFixedThreadPool() # as many threads as CPUs

  try:
    mvd_weights = weights
    if not weights:
      mvd_weights = repeat(Views.interval(ConstantRandomAccessible(FloatType(1), images[0].numDimensions()), FinalInterval(images[0])))

    for i, PSF_kernel in enumerate(PSF_kernels):
      for d in xrange(PSF_kernel.numDimensions()):
        if 0 == PSF_kernel.dimension(d) % 2:
          printFn("for image at index %i, PSF kernel dimension %i is not odd." % (i, d))
          return None

    if not blockSizes:
      # Whole image dimensions + half of the transformed PSF kernel dimensions
      kernel_max = int(max(PSF_kernel.dimension(d)
                           for d in xrange(PSF_kernel.numDimensions())
                           for PSF_kernel in PSF_kernels) * 2)
      syncPrint("kernel max dimension *2: %i" % kernel_max)
      blockSizes = []
      for image in images:
        blockSizes.append([image.dimension(d) + kernel_max
                           for d in xrange(image.numDimensions())])
        syncPrint("blockSize:" + str(blockSizes[-1]))

    cptf = createFactory(exe, lambda_val, blockSizes[0]) # TODO which blockSize to give here?
    filterBlocksForContent = False # Run once with True, none were removed
    dviews = [DeconView(mvd_exe, img, weight, PSF_kernel, PSF_type, blockSize, 1, filterBlocksForContent)
              for img, blockSize, weight, PSF_kernel in izip(images, blockSizes, mvd_weights, PSF_kernels)]
    decon = MultiViewDeconvolutionSeq(DeconViews(dviews, exe), n_iterations, PsiInitBlurredFusedFactory(), cptf, ArrayImgFactory(FloatType()))
    if not decon.initWasSuccessful():
      printFn("Something went wrong initializing MultiViewDeconvolution")
      return None
    else:
      decon.runIterations()
      return decon.getPSI()
  finally:
    # Only shut down the thread pool if it was created here
    if not exe:
      mvd_exe.shutdownNow()


def prepareImgForDeconvolution(img, affine3D, interval):
  """
  Transform the img for deconvolution, taking care of pixels with zero value within the image
  and setting the appropriate values for outside the image, and cropping to the interval.
  """
  return Views.zeroMin(TransformView.transformView(img, affine3D, interval,
                                                   MultiViewDeconvolution.minValueImg,
                                                   MultiViewDeconvolution.outsideValueImg,
                                                   1)) # 1: linear interpolation
  """
  # Manual:
  # Obtain a view where every zero value within the image
  # is replaced with MultiViewDeconvolution.minValueImg, which is 1.0f (a float)
  identity = AffineTransform3D()
  identity.identity()
  imgNonZero = TransformView.transformView(img, identity, img, MultiViewDeconvolution.minValueImg, MultiViewDeconvolution.outsideValueImg, 0) # 0: nearest neighbor
  # Transform
  imgE = Views.extendValue(imgNonZero, FloatType(MultiViewDeconvolution.outsideValueImg))
  imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
  imgT = RealViews.transform(imgI, affine3D)
  imgR = Views.zeroMin(Views.interval(imgT, interval))
  return imgR
  """


def transformPSFKernelToView(kernelImg, affine3D):
  """ Return a PSF kernel as an ArrayImg, transformed with the affine3D of the view.
      The center pixel of the PSF remains the same, and the dimensions as well.
  """
  return PSFExtraction.transformPSF(kernelImg, affine3D)
