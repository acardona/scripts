from net.imglib2 import FinalInterval
from net.imglib2.img.array import ArrayImgFactory
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.view import Views
from net.preibisch.mvrecon.process.deconvolution import MultiViewDeconvolutionSeq, DeconView, DeconViews
from net.preibisch.mvrecon.process.deconvolution.iteration.sequential import ComputeBlockSeqThreadCPUFactory
from net.preibisch.mvrecon.process.deconvolution.init import PsiInitBlurredFusedFactory
from net.preibisch.mvrecon.process.deconvolution.DeconViewPSF import PSFTYPE
from bdv.util import ConstantRandomAccessible
from itertools import repeat, izip
# local lib functions:
from util import newFixedThreadPool, syncPrint


def multiviewDeconvolution(images, blockSize, PSF_kernel, n_iterations, lambda_val=0.0006, weights=None, filterBlocksForContent=False, PSF_type=PSFTYPE.INDEPENDENT, exe=None, printFn=syncPrint):
  """
  Apply Bayesian-based multi-view deconvolution to the list of images,
  returning the deconvolved image. Uses Stephan Preibisch's library,
  currently available with the BigStitcher Fiji update site.

  images: a list of images, registered and with the same dimensions.
  n_iterations: the number of iterations for the deconvolution. A number between 10 and 50 is desirable. The more iterations, the higher the computational cost.
  blockSize: how to chop up the volume for parallel processing.
  PSF_kernel: the image containing the point spread function. Requirement: its dimensions must be an odd number.
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

    for d in xrange(PSF_kernel.numDimensions()):
      if 0 == PSF_kernel.dimension(d) % 2:
        printFn("PSF kernel dimension %i is not odd." % d)
        return None

    factory = ArrayImgFactory(FloatType())
    cptf = ComputeBlockSeqThreadCPUFactory(exe, lambda_val, blockSize, factory)
    filterBlocksForContent = False # Run once with True, none were removed
    decon_views = DeconViews([DeconView(mvd_exe, img, weight, PSF_kernel, PSF_type, blockSize, 1, filterBlocksForContent)
                              for img, weight in izip(images, mvd_weights)],
                             exe)
    decon = MultiViewDeconvolutionSeq(decon_views, n_iterations, PsiInitBlurredFusedFactory(), cptf, factory)
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

