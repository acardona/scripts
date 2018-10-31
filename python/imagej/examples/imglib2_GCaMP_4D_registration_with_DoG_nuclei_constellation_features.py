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
from mpicbg.models import Point, PointMatch, RigidModel3D, NotEnoughDataPointsException
from collections import defaultdict
from operator import sub
from itertools import izip, product
from jarray import array, zeros
import os, csv

# Source directory containing a list of files, one per stack
src_dir = "/home/albert/lab/scripts/data/4D-series/"

# Each timepoint is a path to a 3D stack file
timepoint_paths = sorted(os.path.join(src_dir, name)
                         for name in os.listdir(src_dir)
                         if name.endswith(".klb"))

# DEBUG:
timepoint_paths = timepoint_paths[0:3]

class KLBLoader(CacheLoader):
  def __init__(self):
    self.klb = KLB.newInstance()
  def get(self, path):
    return self.klb.readFull(path)

# Open a series of 3D stacks as a virtual 4D volume
# (lazily: only load 3D stacks upon request. And cached.)
vol4d = Load.lazyStack(timepoint_paths, KLBLoader())

IL.wrap(vol4d, "vol4d").show()

# Parameters for a Difference of Gaussian to detect soma positions
somaDiameter = 10 # in pixels
calibration = [1.0 for i in range(vol4d.numDimensions())] # no calibration: identity
sigmaSmaller = somaDiameter / 4.0 # in pixels: a quarter of the radius of a neuron soma
sigmaLarger = somaDiameter / 2.0  # pixels: half the radius of a neuron soma
minPeakValue = 100 # Maybe raise it to 120

def createDoG(img, calibration, sigmaSmaller, sigmaLarger, minPeakValue):
  # Fixed parameters
  extremaType = DogDetection.ExtremaType.MAXIMA
  normalizedMinPeakValue = False
  # Infinite img
  imgE = Views.extendMirrorSingle(img)
  # In the differece of gaussian peak detection, the img acts as the interval
  # within which to look for peaks. The processing is done on the infinite imgE.
  return DogDetection(imgE, img, calibration, sigmaLarger, sigmaSmaller,
    extremaType, minPeakValue, normalizedMinPeakValue)

def getDoGPeaks(timepoint_index, print_count=True):
  img = Views.hyperSlice(vol4d, 3, timepoint_index)
  dog = createDoG(img, calibration, sigmaSmaller, sigmaLarger, minPeakValue)
  peaks = dog.getSubpixelPeaks() # could also use getPeaks() in integer precision
  if print_count:
    print "Found", len(peaks), "peaks in timepoint", timepoint_index
  return peaks

# A map of timepoint indices and collections of DoG peaks in local 3D coordinates
soma_detections = {ti: getDoGPeaks(ti) for ti in xrange(vol4d.dimension(3))}


# Extract features from the detected soma:
# Each feature is a constellation of a soma position and two other nearby somas.
# Features are comparable by comparing the angles and distances with the two neighbor somas.

class Constellation:
  def __init__(self, center, p1, d1, p2, d2):
    """
       center, p1, p2 are 3 RealLocalizable, with center being the center point
       and p1, p2 being the wings (the other two points).
       p1 is always closer to center than p2 (d1 < d2)
       d1, d2 are the square distances from center to p1, p2
       (which we could compute here, but RadiusNeighborSearchOnKDTree did it already).
    """
    c = zeros(3, 'd')
    center.localize(c)
    self.position = Point(c)
    v1 = Vector3f(*self.subtract(p1, center))
    v2 = Vector3f(*self.subtract(p2, center))
    self.angle = v1.angle(v2) # in radians
    self.len1 = d1 # same as v1.lengthSquared()
    self.len2 = d2 # same as v2.lengthSquared()

  def subtract(self, loc1, loc2):
    return (loc1.getFloatPosition(i) - loc2.getFloatPosition(i)
            for i in xrange(loc1.numDimensions()))

  def compareTo(self, other, angle_epsilon, len_epsilon_sq):
    """
       Compare the angles, if less than epsilon, compare the vector lengths.
       Return True when deemed similar within measurement error brackets.
    """
    return abs(self.angle - other.angle) < angle_epsilon \
       and abs(self.len1 - other.len1) + abs(self.len2 - other.len2) < len_epsilon_sq

# Dictionary of time point index vs search
searches = {ti: RadiusNeighborSearchOnKDTree(KDTree(peaks, peaks))
            for ti, peaks in soma_detections.iteritems()}

def extractFeatures(peaks, search, radius):
  for peak in peaks:
    search.search(peak, radius, True) # sorted
    if search.numNeighbors() > 2:
      # 0 is itself: skip
      p1, d1 = search.getPosition(1), search.getSquareDistance(1)
      p2, d2 = search.getPosition(2), search.getSquareDistance(2)
      yield Constellation(peak, p1, d1, p2, d2)

# Dictionary of time point index vs list of Constellation instances
radius = sigmaLarger * 10 # 5 soma diameters
features = {ti: list(extractFeatures(peaks, searches[ti], radius))
            for ti, peaks in soma_detections.iteritems()}

# Compare constellation features from one time point to the next
# to extract candidate PointMatch instances
angle_epsilon = 0.05 # in radians, 1/20th
len_epsilon_sq = pow(somaDiameter / 2.0, 2) # in pixels, squared: half a soma diameter^2
timepoints = sorted(features.keys())
ti_pointmatches = defaultdict(list)

for t0, t1 in izip(timepoints, timepoints[1:]):
  # Compare all possible pairs of constellation features
  for c0, c1 in product(features[t0], features[t1]):
    if c0.compareTo(c1, angle_epsilon, len_epsilon_sq):
      ti_pointmatches[t0].append(PointMatch(c0.position, c1.position))
  print t0, "vs", t1, "- found", len(ti_pointmatches[t0]), "point matches"

# Reduce each list of pointmatches to a spatially coherent subset
maxEpsilon = sigmaLarger # max allowed alignment error in pixels (a distance)
minInlierRatio = 0.05 # ratio inliers/candidates
minNumInliers = 5 # minimum number of good matches to accept the result
ti_inliers = defaultdict(list)

with open("/tmp/rigid-models.csv", "wb") as csvfile:
  w = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
  w.writerow(['timepoint', 'm00', 'm01', 'm02', 'm03',
                           'm10', 'm11', 'm12', 'm13',
                           'm20', 'm21', 'm22', 'm23'])
  for ti, pointmatches in ti_pointmatches.iteritems():
    model = RigidModel3D()
    inliers = [] # good point matches, to be filled in by model.filterRansac
    try:
      modelFound = model.filterRansac(pointmatches, inliers, 1000,
                                    maxEpsilon, minInlierRatio, minNumInliers)
      if modelFound:
        ti_inliers[ti] = inliers
        print ti, "inliers:", len(inliers)
        # Write model into csv file
        w.writerow([ti] + list(model.getMatrix(zeros(12, 'd'))))
    except NotEnoughDataPointsException, e:
      print e

# The model affine matrix is:
#
# (0.9999996511641432, -7.232108100877311E-5, 8.321305508654424E-4, -0.11069389375730877,
#  7.237326547568491E-5, 0.9999999954165432, -6.26819336798179E-5, -0.021618752972885555,
# -8.321260138262042E-4, 6.274213581938007E-5, 0.9999996518148005, 0.30113192336952466)
#
# ... which, rounded up, looks like exactly what we expected: a tiny subpixel translation
# [1, 0, 0, -0.11,
#  0, 1, 0, -0.02,
#  0, 0, 1,  0.3]

