from org.janelia.simview.klb import KLB
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.realtransform import RealViews, AffineTransform3D, Translation3D
import os
from os.path import basename
from bdv.util import BdvFunctions, Bdv
import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.registration import computeForwardTransforms, asBackwardConcatTransforms, viewTransformed, saveMatrices, loadMatrices
from lib.util import newFixedThreadPool
from org.janelia.simview.klb import KLB
from net.imglib2.cache import CacheLoader
from java.lang import Runtime
from java.util.concurrent import Executors
from mpicbg.models import TranslationModel3D, RigidModel3D
from net.imglib2.img.io import Load
from net.imglib2.img import ImgView
from itertools import izip, imap, combinations
ifrom net.preibisch.mvrecon.process.deconvolution import MultiViewDeconvolution, DeconView, DeconViews
from net.preibisch.mvrecon.process.deconvolution.iteration.sequential import ComputeBlockSeqThreadCPUFactory
from net.imglib2.img.array import ArraImgFactory
from net.imglib2.type.numeric.real import FloatType
from net.preibisch.mvrecon.process.deconvolution.init.PsiInit import PsiInitType
from net.preibisch.mvrecon.process.deconvolution.init import PsiInitBlurredFusedFactory
from net.preibisch.mvrecon.process.deconvolution.DeconViewPSF import PSFTYPE
from bdv.util import ConstantRandomAccessible
from net.imglib2 import FinalInterval



srcDir = "/home/albert/shares/zlaticlab/Nadine/Raghav/2017-05-10/GCaMP6s_1_20170510_115003.corrected/SPM00/"
klb = KLB.newInstance()

# paths for same timepoint, 4 different cameras
paths = []
timepointDir = srcDir + "TM000000/"
for camera_index, channel_index in zip(xrange(4), [1, 1, 0, 0]):
  paths.append(timepointDir + "SPM00_TM000000_CM0" + str(camera_index) + "_CHN0" + str(channel_index) + ".klb")

for path in paths:
  print basename(path)

img0 = klb.readFull(paths[0])
img1 = klb.readFull(paths[1])
img2 = klb.readFull(paths[2])
img3 = klb.readFull(paths[3])

# Calibration: [1.0, 1.0, 5.0]
scale3D = AffineTransform3D()
scale3D.set(1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 5.0, 0.0)

# Expand camera CM00 to isotropy
imgE = Views.extendZero(img0)
imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
imgT = RealViews.transform(imgI, scale3D)
imgB0 = Views.interval(imgT, [0, 0, 0], [img0.dimension(0) -1, img0.dimension(1) -1, img0.dimension(2) * 5 - 1])


# Transform camera CM01 to CM00: 180 degrees on Y axis, plus a translation
dx = -195
dy = 54
dz = 8
affine = AffineTransform3D()
affine.set(-1.0, 0.0, 0.0, img1.dimension(0) + dx,
            0.0, 1.0, 0.0, 0.0 + dy,
            0.0, 0.0, 1.0, 0.0 + dz)
affine.concatenate(scale3D)
imgE = Views.extendZero(img1)
imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
imgT = RealViews.transform(imgI, affine)
imgB1 = Views.interval(imgT, [0, 0, 0], [img1.dimension(0) -1, img1.dimension(1) -1, img1.dimension(2) * 5 - 1])
#imp = IL.wrap(imgB1, "img1 rotated 180")
#imp.setDisplayRange(74, 542)
#imp.setSlice(175)
#imp.show()


# Transform camera CM02 to CM00: 90 degrees on Y axis, plus a translation
# (Z is 85: 20 more than img0 and img1. So view interval that is 100 shorter in Z)
dx = 0.0
dy = 25.0
dz = 41.0
affine = AffineTransform3D()
affine.set( 0.0, 0.0, 1.0, 0.0 + dx,
            0.0, 1.0, 0.0, 0.0 + dy,
            -1.0, 0.0, 0.0, img2.dimension(2) * 5 + dz)
affine.concatenate(scale3D)
imgE = Views.extendZero(img2)
imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
imgT = RealViews.transform(imgI, affine)
imgB2 = Views.interval(imgT, [0, 0, 0], [img2.dimension(0) -1, img2.dimension(1) -1, img2.dimension(2) * 5 -100 - 1])
#imp = IL.wrap(imgB2, "img2 rotated 90")
#imp.setDisplayRange(74, 542)
#imp.setSlice(175)
#imp.show()

# Transform camera CM03 to CM00: -90 degrees on Y axis, plus a translation
dx = 0
dy = 25
dz = -159
affine = AffineTransform3D()
affine.set( 0.0, 0.0, 1.0, 0.0 + dx,
            0.0, 1.0, 0.0, 0.0 + dy,
            1.0, 0.0, 0.0, 0.0 + dz)
affine.concatenate(scale3D)
imgE = Views.extendZero(img3)
imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
imgT = RealViews.transform(imgI, affine)
imgB3 = Views.interval(imgT, [0, 0, 0], [img3.dimension(0) -1, img3.dimension(1) -1, img3.dimension(2) * 5 - 1])
#imp = IL.wrap(Views.zeroMin(imgB3), "img3 rotated -90")
#imp.setDisplayRange(74, 542)
#imp.setSlice(175)
#imp.show()


# The field of view is too large, too much black space
def cropView(img):
  return Views.zeroMin(Views.interval(img, [1, 228, 0], [1 + 406 -1, 228 + 465 -1, 325 -1]))

# Set cropped view for them all
imgB0, imgB1, imgB2, imgB3 = (cropView(img) for img in (imgB0, imgB1, imgB2, imgB3))


def viewAsStack(imgB0, imgB1, imgB2, imgB3):
  imgAll = Views.stack([imgB0, imgB1, imgB2, imgB3])
  IL.wrap(imgAll, "4 views registered").show()

def viewInBDV(imgB0, imgB1, imgB2, imgB3):
  bdv = BdvFunctions.show(imgB0, "imgB0")
  BdvFunctions.show(imgB1, "imgB1", Bdv.options().addTo(bdv))
  BdvFunctions.show(imgB2, "imgB2", Bdv.options().addTo(bdv))
  BdvFunctions.show(imgB3, "imgB3", Bdv.options().addTo(bdv))


# Validate and adjust manual rotation + translation:
# Compute transformation for all views to all views

def getCalibration(img_filename):
  # Already expanded to isotropy
  return [1.0, 1.0, 1.0]

img_names = ["imgB0", "imgB1", "imgB2", "imgB3"]

class ImgLoader(CacheLoader):
  def load(self, path):
    # Simulate: just get the names
    return globals()[path]

csv_dir = "/mnt/ssd-512/IsoView-1038/4-view-check/"
modelclass = TranslationModel3D

# Parameters for DoG difference of Gaussian to detect soma positions
somaDiameter = 8 * getCalibration(None)[0]
paramsDoG = {
  "minPeakValue": 30, # Determined by hand
  "sigmaSmaller": somaDiameter / 4.0, # in calibrated units: 1/4 soma
  "sigmaLarger": somaDiameter / 2.0, # in calibrated units: 1/2 soma
}

paramsFeatures = {
  # Parameters for features
  "radius": somaDiameter * 5, # for searching nearby peaks
  "min_angle": 1.57, # in radians, between vectors to p1 and p2
  "max_per_peak": 3, # maximum number of constellations to create per peak

  # Parameters for comparing constellations to find point matches
  "angle_epsilon": 0.02, # in radians. 0.05 is 2.8 degrees, 0.02 is 1.1 degrees
  "len_epsilon_sq": pow(somaDiameter, 2), # in calibrated units, squared
  "pointmatches_nearby": 1, # if 1 (True), searches for possible matches only within radius
  "pointmatches_search_radius": somaDiameter * 2 #
}

# RANSAC parameters: reduce list of pointmatches to a spatially coherent subset
paramsModel = {
  "maxEpsilon": somaDiameter, # max allowed alignment error in calibrated units (a distance)
  "minInlierRatio": 0.0000001, # ratio inliers/candidates
  "minNumInliers": 5, # minimum number of good matches to accept the result
  "n_iterations": 2000, # for estimating the model
  "maxTrust": 4, # for rejecting candidates
}

# Joint dictionary of parameters
params = {}
params.update(paramsDoG)
params.update(paramsFeatures)
params.update(paramsModel)

exe = newFixedThreadPool(2)

#viewInBDV(imgB0, imgB1, imgB2, imgB3)


# Parameter exploration target: increase dramatically the number of inlier point matches,
# in order to be able to reliably estimate a TranslationModel3D (and RigidiModel3D) across camera views.
# Which requires extracting features optimized for the overlapping regions.
# Strategy 1: allow more features per peak
params["max_per_peak"] = 4 # was 3
# Did increase the number of features but not by much, and not the number of point matches

# Strategy 2: allow constellations with smaller angles to better capture whatever feature could be available
params["min_angle"] = 0.25 # was: 1.57
# Did increase the number of features by a lot (about double), and a tiny bit the point matches

# Strategy 3: lower the threshold for peak detection to increase the number of features in the blurry regions.
params["minPeakValue"] = 20 # was: 30
# Did increase the number of features by almost double again, and now all pairs of views
# have a model made from 11 to 26 point matches. The estimated translations are quite small,
# except for 0-3: 10-pixel shift in X, which is wrong. Still too few point matches for a reliable model.

# Strategy 4: even more features per peak, from a larger radius
# The larger radius should help a lot, to capture strongly firing nuclei that are visible even in blurred regions.
params["max_per_peak"] = 5 # was 4, was 3
params["radius"] = somaDiameter * 10 # was * 5
# Found a similar amount of features (3000 to 5000) and pointmatches, but more inliers;
# and delivered better registration for 0-3: x, y, z = 0.2, -0.6, 2.1 -- which is plausible

# Strategy 5: improve on #4 by increasing the search radius and the number of features per peak
params["max_per_peak"] = 10 # was 5. No performance cost almost, given the KDTree-based search for PointMatches
params["radius"] = somaDiameter * 15
# Now found many inliers: 18 to 45. Derived from more features (~6000).

# Strategy 6: try with even more features per peak
params["max_per_peak"] = 20
# Even more inliers: 35 - 97 at no measurable additional performance cost. 20,000 features!
# Models differ little, varing mostly by subpixel translations or at most 1 or 2 pixels.

# Strategy 7: even more features per peak.
params["max_per_peak"] = 30
# Finds ~30,000 features. Models are similar (differences are subpixel) but based on more inliers: 66-147.
# Very interesting that most of the large translation estimates are gone, as I was expecting a good model would show.
# The largest is ~5, for the Z of views 0-2, shown consistently in strategies #5, #6, #7.

# Strategy 8: use a RigidModel3D to correct for minor rotations
modelclass = RigidModel3D

matrices = {}

try:
  # Compare all to all
  for view1, view2 in combinations(img_names, 2):
    _, matrix = computeForwardTransforms([view1, view2], ImgLoader(), getCalibration, csv_dir, exe, modelclass, params, exe_shutdown=False)
    print "%s, %s:\n[%s,\n %s,\n %s]" % (view1, view2, str(matrix[0:4].tolist()), str(matrix[4:8].tolist()), str(matrix[8:].tolist()))
    matrices[view1 + "-" + view2] = matrix
finally:
  exe.shutdown()

# Assume translation is small: same enclosing interval
def translatedView(img, matrix):
  imgE = Views.extendZero(img)
  imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
  # In negative: the inverse
  t = Translation3D(-matrix[3], -matrix[7], -matrix[11])
  imgT = RealViews.transform(imgI, t)
  return Views.interval(imgT, [0, 0, 0], [img.dimension(d) for d in xrange(3)])

def transformedView(img, matrix):
  imgE = Views.extendZero(img)
  imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
  aff = AffineTransform3D()
  aff.set(*matrix)
  aff = aff.inverse()
  imgT = RealViews.transform(imgI, aff)
  return Views.interval(imgT, [0, 0, 0], [img.dimension(d) for d in xrange(3)])
  
if TranslationModel3D == modelclass:
  transformed = [
    imgB0,
    translatedView(imgB1, matrices["imgB0-imgB1"]),
    translatedView(imgB2, matrices["imgB0-imgB2"]),
    translatedView(imgB3, matrices["imgB0-imgB3"])
   ]
elif RigidModel3D == modelclass:
  transformed = [
    imgB0,
    transformedView(imgB1, matrices["imgB0-imgB1"]),
    transformedView(imgB2, matrices["imgB0-imgB2"]),
    transformedView(imgB3, matrices["imgB0-imgB3"])
   ]


#viewInBDV(*transformed)
#viewAsStack(*transformed)


# Bayesian-based multi-view deconvolution

# Bayesian-based multi-view deconvolution
images = [imgB0, imgB1, imgB2, imgB3]
exe = newFixedThreadPool(Runtime.getRuntime().availableProcessors())
try:
  # TODO missing the kernel
  mylambda = 0.0006
  blockSize = [128. 128, 128]
  cptf = ComputeBlockSeqThreadCPUFactory(exe, mylambda, blockSize, ArrayImgFactory(FloatType()))
  psiInitType = PsiInitType.FUSED_BLURRED
  psiInitFactory = new PsiInitBlurredFusedFactory()
  weight = Views.interval(ConstantRandomAccessible(FloatType(1), image4D.numDimensions), FinalInterval(image4D))
  kernel = ArrayImgs.floats(31, 31, 31) # TODO MISSING CONTENT
  views = []
  for img in images:
    views.append(DeconView(exe, img, weight, kernel, PSFTYPE.INDEPENDENT, blockSize, 1, True))
  decon_views = DeconViews(views, exe)
  n_iterations = 1 # like in Preibisch's test
  decon = MultiViewDeconvolution(decon_views, n_iterations, psiInitFactory(), cptf, ArrayImgFactory(FloatType()))
  if not decon.initWasSuccessful():
    print "Something went wrong initializing MultiViewDeconvolution"
  else:
    decon.runIterations()
    img = decon.getPSI()
    IL.wrap(img, "deconvolved").show()
finally:
  exe.shutdown()

