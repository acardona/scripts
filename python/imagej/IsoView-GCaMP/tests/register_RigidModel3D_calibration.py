from net.imglib2.algorithm.dog import DogDetection
from net.imglib2.img.io import Load
from net.imglib2.cache import CacheLoader
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2 import KDTree
from net.imglib2.neighborsearch import RadiusNeighborSearchOnKDTree
from org.janelia.simview.klb import KLB
from org.scijava.vecmath import Vector3f
from mpicbg.imagefeatures import FloatArray2DSIFT, FloatArray2D
from mpicbg.models import Point, PointMatch, InterpolatedAffineModel3D, AffineModel3D, RigidModel3D, NotEnoughDataPointsException
from collections import defaultdict
from operator import sub
from itertools import imap, izip, product, combinations
from jarray import array, zeros
import os, csv
from java.util.concurrent import Executors, Callable
from java.util import ArrayList
from ij import IJ
from net.imglib2.algorithm.math import ImgMath, ImgSource
from net.imglib2.img.array import ArrayImgs
from net.imglib2.realtransform import RealViews, AffineTransform3D
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.util import Intervals


img = IL.wrap(IJ.getImage())

def dropSlices(img, nth):
  """
  Drop every nth slice.
  The calibration is then to be multipled by nth for Z.
  Counts slices 1-based so as to preserve the first slice (index zero).
  """
  return Views.stack([Views.hyperSlice(img, 2, i) for i in xrange(img.dimension(2)) if 0 == (i+1) % nth])

# Cut out a cube
img1 = Views.zeroMin(Views.interval(img, [39, 49, 0], [39 + 378 -1, 49 + 378 -1, 378 -1]))
print [img1.dimension(d) for d in xrange(img1.numDimensions())]

# Rotate the cube on the Y axis to the left
img2 = Views.zeroMin(Views.rotate(img1, 2, 0))  # zeroMin is CRITICAL

# Reduce Z resolution
nth = 2
img2 = dropSlices(img2, nth)

# copy into ArrayImg
img1a = ArrayImgs.unsignedShorts([378, 378, 378])
ImgMath.compute(ImgSource(img1)).into(img1a)

img2a = ArrayImgs.unsignedShorts([378, 378, 378 / nth])
ImgMath.compute(ImgSource(img2)).into(img2a)

img1 = img1a
img2 = img2a

IL.wrap(img1, "cube").show()
IL.wrap(img2, "cube rotated").show()

# Now register them


# PARAMETERS
calibration = {0: [1.0, 1.0, 1.0],
               1: [1.0, 1.0, 1.0 * nth]}
               
# Parameters for DoG difference of Gaussian to detect soma positions
somaDiameter = 8 * calibration[0][0]
minPeakValue = 20 # 30: Determined by hand
sigmaSmaller = somaDiameter / 4.0 # in calibrated units: a quarter of the radius of a neuron soma
sigmaLarger = somaDiameter / 2.0  # in calibrated units: half the radius of a neuron soma

# Parameters for extracting features (constellations)
radius = somaDiameter * 5 # for searching nearby peaks to create constellations
min_angle = 0.1 # in radians, between vectors to p1 and p2

# Parameters for comparing constellations to find point matches
angle_epsilon = 0.05 # in radians. 0.05 is 2.8 degrees
len_epsilon_sq = pow(somaDiameter / 2, 2) # in calibrated units, squared


def scale(img, calibration):
  scale3d = AffineTransform3D()
  scale3d.set(calibration[0], 0, 0, 0,
              0, calibration[1], 0, 0,
              0, 0, calibration[2], 0)
  imgE = Views.extendZero(img)
  imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
  imgT = RealViews.transform(imgI, scale3d)
  # dimensions
  minC = [0, 0, 0]
  maxC = [int(img.dimension(d) * cal) -1 for d, cal in enumerate(calibration)]
  imgB = Views.interval(imgT, minC, maxC)
  return imgB

def createDoG(img, calibration, sigmaSmaller, sigmaLarger, minPeakValue):
  """
    sigmaSmaller and sigmalLarger are in calibrated units.
  """
  # Fixed parameters
  extremaType = DogDetection.ExtremaType.MAXIMA
  normalizedMinPeakValue = False
  
  # Infinite img
  imgE = Views.extendMirrorSingle(img)
  # In the differece of gaussian peak detection, the img acts as the interval
  # within which to look for peaks. The processing is done on the infinite imgE.
  return DogDetection(imgE, img, calibration, sigmaLarger, sigmaSmaller,
    extremaType, minPeakValue, normalizedMinPeakValue)

def getDoGPeaks(img, calibration):
  dog = createDoG(img, calibration, sigmaSmaller, sigmaLarger, minPeakValue)
  peaks = dog.getSubpixelPeaks() # could also use getPeaks() in integer precision
  # Return peaks in calibrated units
  for peak in peaks:
    for d, cal in enumerate(calibration):
      peak.setPosition(peak.getFloatPosition(d) * cal, d)
  return peaks

class Task(Callable):
  def __init__(self, fn, *args):
    self.fn = fn
    self.args = args
  def call(self):
    return self.fn(*self.args)

class Constellation:
  def __init__(self, center, p1, d1, p2, d2):
    """
       center, p1, p2 are 3 RealLocalizable, with center being the center point
       and p1, p2 being the wings (the other two points).
       p1 is always closer to center than p2 (d1 < d2)
       d1, d2 are the square distances from center to p1, p2
       (which we could compute here, but RadiusNeighborSearchOnKDTree did it already).
    """
    self.position = Point(self.array(center))
    v1 = Vector3f(*self.subtract(p1, center))
    v2 = Vector3f(*self.subtract(p2, center))
    self.angle = v1.angle(v2) # in radians
    self.len1 = d1 # same as v1.lengthSquared()
    self.len2 = d2 # same as v2.lengthSquared()

  def subtract(self, loc1, loc2):
    return (loc1.getFloatPosition(d) - loc2.getFloatPosition(d)
            for d in xrange(loc1.numDimensions()))

  def array(self, loc):
    return array((loc.getFloatPosition(d)for d in xrange(loc.numDimensions())), 'd')
    

  def compareTo(self, other, angle_epsilon, len_epsilon_sq):
    """
       Compare the angles, if less than epsilon, compare the vector lengths.
       Return True when deemed similar within measurement error brackets.
    """
    return abs(self.angle - other.angle) < angle_epsilon \
       and abs(self.len1 - other.len1) + abs(self.len2 - other.len2) < len_epsilon_sq


def makeRadiusSearch(peaks):
  return RadiusNeighborSearchOnKDTree(KDTree(peaks, peaks))

def extractFeatures(peaks, search, radius, min_angle):
  for peak in peaks:
    search.search(peak, radius, True) # sorted
    if search.numNeighbors() > 2:
      # 0 is itself: skip
      p1, d1 = search.getPosition(1), search.getSquareDistance(1)
      p2, d2 = search.getPosition(2), search.getSquareDistance(2)
      cons = Constellation(peak, p1, d1, p2, d2)
      if cons.angle >= min_angle:
        yield cons


exe = Executors.newFixedThreadPool(4)

try:
  # A map of image indices and collections of DoG peaks in calibrated 3D coordinates
  # (Must be calibrated, or the KDTree radius search wouldn't work as intended.)
  futures = [exe.submit(Task(getDoGPeaks, img, calibration[i])) for i, img in enumerate([img1, img2])]
  soma_detections = {ti: f.get() for ti, f in enumerate(futures)}

  for ti, peaks in soma_detections.iteritems():
    print "Found %i peaks in %i" % (len(peaks), ti)

  # Dictionary of image index vs search
  futures = {ti: exe.submit(Task(makeRadiusSearch, peaks)) for ti, peaks in soma_detections.iteritems()}
  searches = {ti: f.get() for ti, f in futures.iteritems()}

  # Dictionary of image index vs list of Constellation feature instances
  futures = {ti: exe.submit(Task(extractFeatures, peaks, searches[ti], radius, min_angle))
             for ti, peaks in soma_detections.iteritems()}
  features = {ti: list(f.get()) for ti, f in futures.iteritems()}

  for ti, fs in features.iteritems():
    print "Found", len(fs), "features in image", ti

  # Compare constellation features to find candidate PointMatch instances
  ti_pointmatches = defaultdict(list)

  for t0, t1 in [[0, 1]]:
    # Compare all possible pairs of constellation features
    for c0, c1 in product(features[t0], features[t1]):
      if c0.compareTo(c1, angle_epsilon, len_epsilon_sq):
        ti_pointmatches[t1].append(PointMatch(c0.position, c1.position))
    #
    print t0, "vs", t1, "- found", len(ti_pointmatches[t1]), "point matches"

  # Reduce each list of pointmatches to a spatially coherent subset
  maxEpsilon = somaDiameter / 2 # max allowed alignment error in calibrated units (a distance)
  minInlierRatio = 0.01 # ratio inliers/candidates
  minNumInliers = 5 # minimum number of good matches to accept the result
  n_iterations = 2000 # for estimating the model

  def fit(model, pointmatches):
    inliers = ArrayList()
    exception = None
    try:
      modelFound = model.filterRansac(pointmatches, inliers, n_iterations,
                                    maxEpsilon, minInlierRatio, minNumInliers)
    except NotEnoughDataPointsException, e:
      exception = e
    return model, modelFound, inliers, exception

  matrices = {}

  futures = {ti: exe.submit(Task(fit, RigidModel3D(), pointmatches))
             for ti, pointmatches in ti_pointmatches.iteritems()}
  for ti, f in futures.iteritems():
    model, modelFound, inliers, exception = f.get()
    if modelFound:
      print t0, "vs", t1, "- found", len(inliers), "inliers"
      matrix = list(model.getMatrix(zeros(12, 'd')))
      print "model matrix: [", matrix[0:4]
      print "               ", matrix[4:8]
      print "               ", matrix[8:12], "]"
    else:
      print "Model not found for", ti
      if exception:
        print exception
      matrix = [1, 0, 0, 0, # identity
                0, 1, 0, 0,
                0, 0, 1, 0]
    matrices[ti] = matrix

finally:
  exe.shutdown()


def viewTransformed(img, calibration, matrix):
  affine = AffineTransform3D()
  affine.set(*matrix)
  # It's a forward transform: invert
  affine = affine.inverse()
  # Correct calibration
  scale3d = AffineTransform3D()
  scale3d.set(calibration[0], 0, 0, 0,
              0, calibration[1], 0, 0,
              0, 0, calibration[2], 0)
  affine.concatenate(scale3d)
  imgE = Views.extendZero(img)
  imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
  imgT = RealViews.transform(imgI, affine)
  # dimensions
  minC = [0, 0, 0]
  maxC = [int(img.dimension(d) * cal) -1 for d, cal in enumerate(calibration)]
  imgB = Views.interval(imgT, minC, maxC)
  return imgB

# View img2 transformed
img2T = viewTransformed(img2, calibration[1], matrices[1])
IL.wrap(img2T, "rotated transformed back").show()

