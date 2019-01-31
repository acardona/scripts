from __future__ import with_statement
from net.imglib2.algorithm.dog import DogDetection
from net.imglib2.img.io import Load
from net.imglib2.cache import CacheLoader
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2 import KDTree
from net.imglib2.neighborsearch import RadiusNeighborSearchOnKDTree
from net.imglib2.img.array import ArrayImgs
from net.imglib2.realtransform import RealViews, AffineTransform3D
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from org.scijava.vecmath import Vector3f
from mpicbg.imagefeatures import FloatArray2DSIFT, FloatArray2D
from mpicbg.models import Point, PointMatch, InterpolatedAffineModel3D, AffineModel3D, RigidModel3D, NotEnoughDataPointsException
from itertools import imap, izip, product
from jarray import array, zeros
from java.util import ArrayList
from java.util.concurrent import Executors, Callable
from java.lang import Runtime
from ij import IJ
import os, csv

def dropSlices(img, nth):
  """ Drop every nth slice. Calibration is to be multipled by nth for Z.
      Counts slices 1-based so as to preserve the first slice (index zero).
  """
  return Views.stack([Views.hyperSlice(img, 2, i)
                      for i in xrange(img.dimension(2)) if 0 == (i+1) % nth])

# Grap the current image
img = IL.wrap(IJ.getImage())

# Cut out a cube
img1 = Views.zeroMin(Views.interval(img, [39, 49, 0],
                                         [39 + 378 -1, 49 + 378 -1, 378 -1]))

# Rotate the cube on the Y axis to the left
img2 = Views.zeroMin(Views.rotate(img1, 2, 0)) # zeroMin is CRITICAL

# Totate the cube on the X axis to the top
img3 = Views.zeroMin(Views.rotate(img1, 2, 1))

# Reduce Z resolution: make them anisotropic but in a different direction
nth = 2
img1 = dropSlices(img1, nth)
img2 = dropSlices(img2, nth)
img3 = dropSlices(img3, nth)

# The sequence of images to transform, one relative to the previous
images = [img1, img2, img3]

#IL.wrap(img1, "cube").show()
#IL.wrap(img2, "cube rotated Y").show()
#IL.wrap(img3, "cube rotated X").show()
IL.wrap(Views.stack(images), "unregistered").show()


# PARAMETERS
calibrations = [[1.0, 1.0, 1.0 * nth],
                [1.0, 1.0, 1.0 * nth],
                [1.0, 1.0, 1.0 * nth]]
               
# Parameters for DoG difference of Gaussian to detect soma positions
somaDiameter = 8 * calibrations[0][0]
minPeakValue = 30 # Determined by hand
sigmaSmaller = somaDiameter / 4.0 # in calibrated units: 1/4 soma
sigmaLarger  = somaDiameter / 2.0 # in calibrated units: 1/2 soma

# Parameters for extracting features (constellations)
radius = somaDiameter * 5 # for searching nearby peaks
min_angle = 1.57 # in radians, between vectors to p1 and p2
max_per_peak = 3 # maximum number of constellations to create per peak

# Parameters for comparing constellations to find point matches
angle_epsilon = 0.02 # in radians. 0.05 is 2.8 degrees, 0.02 is 1.1 degrees
len_epsilon_sq = pow(somaDiameter / 1, 2) # in calibrated units, squared

# RANSAC parameters: reduce list of pointmatches to a spatially coherent subset
maxEpsilon = somaDiameter # / 2 # max allowed alignment error in calibrated units (a distance)
minInlierRatio = 0.0000001 # ratio inliers/candidates
minNumInliers = 5 # minimum number of good matches to accept the result
n_iterations = 2000 # for estimating the model
maxTrust = 4 # for rejecting candidates

def createDoG(img, calibration, sigmaSmaller, sigmaLarger, minPeakValue):
  """ Create difference of Gaussian peak detection instance.
      sigmaSmaller and sigmalLarger are in calibrated units. """
  # Fixed parameters
  extremaType = DogDetection.ExtremaType.MAXIMA
  normalizedMinPeakValue = False
  
  imgE = Views.extendMirrorSingle(img)
  # In the differece of gaussian peak detection, the img acts as the interval
  # within which to look for peaks. The processing is done on the infinite imgE.
  return DogDetection(imgE, img, calibration, sigmaLarger, sigmaSmaller,
    extremaType, minPeakValue, normalizedMinPeakValue)

def getDoGPeaks(img, calibration, sigmaSmaller, sigmaLarger, minPeakValue):
  """ Return a list of peaks as net.imglib2.RealPoint instances, calibrated. """
  dog = createDoG(img, calibration, sigmaSmaller, sigmaLarger, minPeakValue)
  peaks = dog.getSubpixelPeaks()
  # Return peaks in calibrated units (modify in place)
  for peak in peaks:
    for d, cal in enumerate(calibration):
      peak.setPosition(peak.getFloatPosition(d) * cal, d)
  return peaks

# A custom feature, comparable with other features
class Constellation:
  """ Expects 3 scalars and an iterable of scalars. """
  def __init__(self, angle, len1, len2, coords):
    self.angle = angle
    self.len1 = len1
    self.len2 = len2
    self.position = Point(array(coords, 'd'))

  def matches(self, other, angle_epsilon, len_epsilon_sq):
    """
       Compare the angles, if less than epsilon, compare the vector lengths.
       Return True when deemed similar within measurement error brackets.
    """
    return abs(self.angle - other.angle) < angle_epsilon \
       and abs(self.len1 - other.len1) + abs(self.len2 - other.len2) < len_epsilon_sq

  @staticmethod
  def subtract(loc1, loc2):
    return (loc1.getFloatPosition(d) - loc2.getFloatPosition(d)
            for d in xrange(loc1.numDimensions()))

  @staticmethod
  def fromSearch(center, p1, d1, p2, d2):
    """
       center, p1, p2 are 3 RealLocalizable, with center being the peak
       and p1, p2 being the wings (the other two points).
       p1 is always closer to center than p2 (d1 < d2).
       d1, d2 are the square distances from center to p1, p2
       (could be computed here, but RadiusNeighborSearchOnKDTree did it).
    """
    pos = tuple(center.getFloatPosition(d) for d in xrange(center.numDimensions()))
    v1 = Vector3f(Constellation.subtract(p1, center))
    v2 = Vector3f(Constellation.subtract(p2, center))
    return Constellation(v1.angle(v2), d1, d2, pos)


def makeRadiusSearch(peaks):
  """ Construct a KDTree-based radius search, for locating points
      within a given radius of a reference point. """
  return RadiusNeighborSearchOnKDTree(KDTree(peaks, peaks))


def extractFeatures(peaks, search, radius, min_angle, max_per_peak):
  """ Construct up to max_per_peak constellation features with furthest peaks. """
  constellations = []
  for peak in peaks:
    search.search(peak, radius, True) # sorted
    n = search.numNeighbors()
    if n > 2:
      yielded = 0
      # 0 is itself: skip from range of indices
      for i, j in izip(xrange(n -2, 0, -1), xrange(n -1, 0, -1)):
        if yielded == max_per_peak:
          break
        p1, d1 = search.getPosition(i), search.getSquareDistance(i)
        p2, d2 = search.getPosition(j), search.getSquareDistance(j)
        cons = Constellation.fromSearch(peak, p1, d1, p2, d2)
        if cons.angle >= min_angle:
          yielded += 1
          constellations.append(cons)
  #
  return constellations


class PointMatches():
  def __init__(self, pointmatches):
    self.pointmatches = pointmatches
  
  @staticmethod
  def fromFeatures(features1, features2, angle_epsilon, len_epsilon_sq):
    """ Compare all features of one image to all features of the other image,
        to identify matching features and then create PointMatch instances. """
    return PointMatches([PointMatch(c1.position, c2.position)
                         for c1, c2 in product(features1, features2)
                         if c1.matches(c2, angle_epsilon, len_epsilon_sq)])



def fit(model, pointmatches, n_iterations, maxEpsilon,
        minInlierRatio, minNumInliers, maxTrust):
  """ Fit a model to the pointmatches, finding the subset of inlier pointmatches
      that agree with a joint transformation model. """
  inliers = ArrayList()
  exception = None
  try:
    modelFound = model.filterRansac(pointmatches, inliers, n_iterations,
                                    maxEpsilon, minInlierRatio, minNumInliers, maxTrust)
  except NotEnoughDataPointsException, e:
    exception = e
  return model, modelFound, inliers, exception


# A wrapper for executing functions in concurrent threads
class Task(Callable):
  def __init__(self, fn, *args):
    self.fn = fn
    self.args = args
  def call(self):
    return self.fn(*self.args)



n_threads = Runtime.getRuntime().availableProcessors()
exe = Executors.newFixedThreadPool(n_threads)


try:
  # A list of collections of DoG peaks in calibrated 3D coordinates
  # (Must be calibrated, or the KDTree radius search wouldn't work as intended.)
  futures = [exe.submit(Task(getDoGPeaks, img, calibration, sigmaSmaller,
                             sigmaLarger, minPeakValue))
             for img, calibration in izip(images, calibrations)]
  soma_detections = [f.get() for f in futures]

  for i, peaks in enumerate(soma_detections):
    print "Found %i peaks in %i" % (len(peaks), i)

  # List of search instances
  futures = [exe.submit(Task(makeRadiusSearch, peaks))
             for peaks in soma_detections]
  searches = [f.get() for f in futures]

  # List of lists of Constellation feature instances
  futures = [exe.submit(Task(extractFeatures, peaks, search, radius, min_angle, max_per_peak))
             for search, peaks in izip(searches, soma_detections)]
  features = [f.get() for f in futures]

  for i, fs in enumerate(features):
    print "Found", len(fs), "constellation features in image", i

  # Compare all possible pairs of constellation features
  futures = [exe.submit(Task(PointMatches.fromFeatures, features1, features2, angle_epsilon, len_epsilon_sq))
             for features1, features2 in izip(features, features[1:])]
  pointmatches = [f.get().pointmatches for f in futures]

  for i, pms in enumerate(pointmatches):
    print i, "vs", (i+1), "- found", len(pms), "point matches"

  # Obtain the transformation matrices
  futures = [exe.submit(Task(fit, RigidModel3D(), pms, n_iterations, maxEpsilon,
                             minInlierRatio, minNumInliers, maxTrust))
             for pms in pointmatches]
  # First image gets identity: unchanged
  matrices = [[1, 0, 0, 0,
               0, 1, 0, 0,
               0, 0, 1, 0]]
  # From second image onward:
  for i, f in enumerate(futures):
    model, modelFound, inliers, exception = f.get()
    if modelFound:
      print i, "vs", (i+1), "- found", len(inliers), "inliers"
      matrix = model.getMatrix(zeros(12, 'd')) # an array of doubles
      print "model matrix: [", matrix[0:4]
      print "               ", matrix[4:8]
      print "               ", matrix[8:12], "]"
    else:
      print "Model not found for", i
      if exception:
        print exception
      matrix = [1, 0, 0, 0, # identity
                0, 1, 0, 0,
                0, 0, 1, 0]
    # Store
    matrices.append(matrix)


finally:
  exe.shutdown()


# Invert and concatenate transforms
aff_previous = AffineTransform3D()
aff_previous.identity() # set to identity
affines = [aff_previous] # first image at index 0

for matrix in matrices[1:]: # skip zero, which is the identity
  aff = AffineTransform3D()
  aff.set(*matrix)
  aff = aff.inverse() # matrix describes the img1 -> img2 transform, we want the opposite
  aff.preConcatenate(aff_previous) # Make relative to prior image
  affines.append(aff) # Store
  aff_previous = aff # next iteration


def viewTransformed(img, calibration, affine):
  # Correct calibration
  scale3d = AffineTransform3D()
  scale3d.set(calibration[0], 0, 0, 0,
              0, calibration[1], 0, 0,
              0, 0, calibration[2], 0)
  transform = affine.copy()
  transform.concatenate(scale3d)
  imgE = Views.extendZero(img)
  imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
  imgT = RealViews.transform(imgI, transform)
  # dimensions
  minC = [0, 0, 0]
  maxC = [int(img.dimension(d) * cal) -1 for d, cal in enumerate(calibration)]
  imgB = Views.interval(imgT, minC, maxC)
  return imgB

# View registered 4D stack
registered4D = Views.stack([viewTransformed(img, calibration, affine)
                            for img, calibration, affine in izip(images, calibrations, affines)])

IL.wrap(registered4D, "registered").show()
