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


# Open 4 views, from IsoView microscope in the Keller lab, Raghav Chhetri et al. 2015.

srcDir = "/home/albert/shares/zlaticlab/Nadine/Raghav/2017-05-10/GCaMP6s_1_20170510_115003.corrected/SPM00/"

# Each time point is a folder like TM000000, TM000001, ...
# that contains 4 views named:
#   SPM00_TM000000_CM00_CHN01.klb
#   SPM00_TM000000_CM01_CHN01.klb
#   SPM00_TM000000_CM02_CHN00.klb
#   SPM00_TM000000_CM03_CHN00.klb

klb = KLB.newInstance()

# paths for same timepoint, 4 different cameras
timepoint_paths = []
timepointDir = srcDir + "TM000000/"
for camera_index, channel_index in zip(xrange(4), [1, 1, 0, 0]):
  timepoint_paths.append(timepointDir + "SPM00_TM000000_CM0" + str(camera_index) + "_CHN0" + str(channel_index) + ".klb")

# append again the first one
timepoint_paths.append(timepoint_paths[0])


# IMPORTANT PARAMETERS
raw_calibration = [0.40625, 0.40625, 2.03125] # micrometers per pixel
calibration = [cal/raw_calibration[0] for cal in raw_calibration] # becomes: [1.0, 1.0, 5.0]
print "Calibration:", calibration
# Parameters for DoG difference of Gaussian
somaDiameter = 8 * calibration[0]
minPeakValue = 20 # 30: Determined by hand
# Parameters for extracting features
radius = somaDiameter * 5 # for searching nearby peaks to create constellations
n_somas_radius = 5 # for the search radius, in multiples of somas
n_max = 5 # Max number of constellation features per DoG peak
furthest = True # Use peaks furthest from the DoG peak
# Parameters for a Difference of Gaussian to detect soma positions
sigmaSmaller = somaDiameter / 4.0 # in calibrated units: a quarter of the radius of a neuron soma
sigmaLarger = somaDiameter / 2.0  # in calibrated units: half the radius of a neuron soma


class KLBLoader(CacheLoader):
  def __init__(self):
    self.klb = KLB.newInstance()
  def get(self, path):
    return self.klb.readFull(path)

# Open a series of 3D stacks as a virtual 4D volume
# (lazily: only load 3D stacks upon request. And cached.)
vol4d = Load.lazyStack(timepoint_paths, KLBLoader())

IL.wrap(vol4d, "vol4d").show()


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

def getDoGPeaks(timepoint_index, calibration):
  img = Views.hyperSlice(vol4d, 3, timepoint_index)
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

def extractFeatures(peaks, search, radius, n_max, furthest):
  for peak in peaks:
    search.search(peak, radius, True) # sorted
    """
    if search.numNeighbors() > 2:
      # 0 is itself: skip
      p1, d1 = search.getPosition(1), search.getSquareDistance(1)
      p2, d2 = search.getPosition(2), search.getSquareDistance(2)
      cons = Constellation(peak, p1, d1, p2, d2)
      if cons.angle < 0.1: # radians
        # Reject: angle is too small
        continue
      yield cons
    """
    if search.numNeighbors() < 3:
      continue
    indices = range(1, search.numNeighbors())
    if furthest:
      indices.reverse()
    # Make as many constellations as possible, up to n_max
    count = 0
    for i, k in combinations(indices, 2):
      p1, d1 = search.getPosition(i), search.getSquareDistance(i)
      p2, d2 = search.getPosition(k), search.getSquareDistance(k)
      cons = Constellation(peak, p1, d1, p2, d2)
      if cons.angle > 0.25 and count < n_max:
        count += 1
        yield cons



exe = Executors.newFixedThreadPool(4)

try:
  # A map of timepoint indices and collections of DoG peaks in calibrated 3D coordinates
  # (Must be calibrated, or the KDTree radius search wouldn't work as intended.)
  futures = [exe.submit(Task(getDoGPeaks, ti, calibration)) for ti in xrange(vol4d.dimension(3))]
  soma_detections = {ti: f.get() for ti, f in enumerate(futures)}

  for ti, peaks in soma_detections.iteritems():
    print "Found %i peaks in timepoint %i" % (len(peaks), ti)

  # Extract features from the detected soma:
  # Each feature is a constellation of a soma position and two other nearby somas.
  # Features are comparable by comparing the angles and distances with the two neighbor somas.

  # Dictionary of time point index vs search
  futures = {ti: exe.submit(Task(makeRadiusSearch, peaks)) for ti, peaks in soma_detections.iteritems()}
  searches = {ti: f.get() for ti, f in futures.iteritems()}

  # Dictionary of time point index vs list of Constellation instances
  futures = {ti: exe.submit(Task(extractFeatures, peaks, searches[ti], radius, n_max, furthest))
             for ti, peaks in soma_detections.iteritems()}
  features = {ti: list(f.get()) for ti, f in futures.iteritems()}

  for ti, fs in features.iteritems():
    print "Found", len(fs), "features in timepoint", ti

  # Compare constellation features from one time point to the next
  # to extract candidate PointMatch instances
  angle_epsilon = 0.05 # in radians. 0.05 is 2.8 degrees
  len_epsilon_sq = pow(somaDiameter / 2, 2) # in calibrated units, squared
  ti_pointmatches = defaultdict(list)

  # Match up specifically:
  # CM00_CHN01, CM03_CHN00
  # CM01_CHN01, CM02_CHN00
  # CM02_CHN00, CM00_CHN01
  # CM03_CHN00, CM01_CHN01
  #
  # Translates to:
  pairings = [[0, 3],
              [1, 2],
              [2, 0],
              [3, 1]]

  # Which, for concatenation of transformations, should be like:
  pairings = [[0, 3],
              [3, 1],
              [1, 2],
              [2, 0]] # would skip the last, but I re-added it at the end of timepoint_paths

  pairs = pairings[:]

  for t0, t1 in pairs:
    # Compare all possible pairs of constellation features
    for c0, c1 in product(features[t0], features[t1]):
      if c0.compareTo(c1, angle_epsilon, len_epsilon_sq):
        ti_pointmatches[t1].append(PointMatch(c0.position, c1.position))
    print t0, "vs", t1, "- found", len(ti_pointmatches[t1]), "point matches"

  """
# Debug: print constellations for point matches
for ti, cs in matching_constellations.iteritems():
  count = 10
  for c0, c1 in cs:
    if count > 0:
      count -=1
      print c0.angle, c1.angle, '::', c0.len1, c1.len1, '::', c0.len2, c1.len2
  """

  # Reduce each list of pointmatches to a spatially coherent subset
  maxEpsilon = somaDiameter / 2 # max allowed alignment error in calibrated units (a distance)
  minInlierRatio = 0.01 # ratio inliers/candidates
  minNumInliers = 5 # minimum number of good matches to accept the result
  n_iterations = 2000 # for estimating the model

  with open("/tmp/rigid-models.csv", "wb") as csvfile:
    w = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
    w.writerow(['filepath', 'm00', 'm01', 'm02', 'm03',
                            'm10', 'm11', 'm12', 'm13',
                            'm20', 'm21', 'm22', 'm23'])
    # First time point (0) gets the identity transform
    w.writerow([timepoint_paths[0]] + [1, 0, 0, 0,
                                       0, 1, 0, 0,
                                       0, 0, 1, 0])
    
    # Write affine matrices for all other time points

    def fit(model, pointmatches):
      inliers = ArrayList()
      exception = None
      try:
        modelFound = model.filterRansac(pointmatches, inliers, n_iterations,
                                    maxEpsilon, minInlierRatio, minNumInliers)
      except NotEnoughDataPointsException, e:
        exception = e
      return model, modelFound, inliers, exception

    futures = {ti: exe.submit(Task(fit, RigidModel3D(), pointmatches))
               for ti, pointmatches in ti_pointmatches.iteritems()}
    for ti, f in futures.iteritems():
      model, modelFound, inliers, exception = f.get()
      if modelFound:
        print ti, "inliers:", len(inliers)
        # Write timepoint filepath and model affine matrix into csv file
        w.writerow([timepoint_paths[ti]] + list(model.getMatrix(zeros(12, 'd'))))
      else:
        print "Model not found for timepoint", ti
        if exception:
          print exception
        w.writerow([timepoint_paths[ti]] + [1, 0, 0, 0, # identity
                                            0, 1, 0, 0,
                                            0, 0, 1, 0])

finally:
  exe.shutdown()




# Open the 4D series again, this time virtually registered
from net.imglib2.realtransform import RealViews, AffineTransform3D
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.util import Intervals
from net.imglib2.img import ImgView

# A scaling transform to visualize volume in calibrated units
scale3d = AffineTransform3D()
scale3d.set(calibration[0], 0, 0, 0,
            0, calibration[1], 0, 0,
            0, 0, calibration[2], 0)

class KLBTransformLoader(CacheLoader):
  def __init__(self, transforms, calibration):
    self.transforms = transforms
    self.klb = KLB.newInstance()
  def get(self, path):
    img = self.klb.readFull(path)
    imgE = Views.extendZero(img)
    imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
    affine = AffineTransform3D()
    affine.set(self.transforms[path])
    affine = affine.inverse() # it's a forward transform: must invert
    affine.concatenate(scale3d) # calibrated space: isotropic
    imgT = RealViews.transform(imgI, affine)
    minC = [0, 0, 0]
    maxC = [int(img.dimension(d) * cal) -1 for d, cal in enumerate(calibration)]
    imgB = Views.interval(imgT, minC, maxC)
    # View a RandomAccessibleInterval as an Img, required by Load.lazyStack
    return ImgView.wrap(imgB, img.factory())

# Read affine matrices for each time point
# into a dictionary of file paths vs AffineTransform3D
# where each AffineTransform3D is chained to all previous transforms.
# This is necessary because the matrices in the CSV file
# only describe the transform from one timepoint to the previous one,
# whereas we want the transform of any time point to the first time point.
with open("/tmp/rigid-models.csv", "r") as csvfile:
  reader = csv.reader(csvfile, delimiter=',', quotechar='"')
  header = reader.next() # advance reader by one line
  transforms = {}
  previous = AffineTransform3D()
  previous.identity() # set to a diagonal of 1s
  for row in reader:
    affine = AffineTransform3D()
    filepath = row[0]
    matrix = imap(float, row[1:])
    affine.set(*matrix) # expand into 12 arguments
    # chain the previous transform
    affine.preConcatenate(previous) # TODO or concatenate?
    previous = affine
    # Store
    transforms[filepath] = affine

for k, v in transforms.iteritems():
  print k

# Load the 4D series with each time point 3D volume transformed
ordered_camera_views = [timepoint_paths[pairings[0][0]],
                        timepoint_paths[pairings[1][0]],
                        timepoint_paths[pairings[2][0]],
                        timepoint_paths[pairings[3][0]],
                        timepoint_paths[pairings[0][0]]] # repeated 
vol4d_registered = Load.lazyStack(ordered_camera_views, KLBTransformLoader(transforms, calibration))

IL.wrap(vol4d_registered, "vol4d registered").show()

