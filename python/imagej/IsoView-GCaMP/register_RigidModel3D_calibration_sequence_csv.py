from __future__ import with_statement
from net.imglib2.algorithm.dog import DogDetection
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2 import KDTree
from net.imglib2.neighborsearch import RadiusNeighborSearchOnKDTree
from net.imglib2.realtransform import RealViews, AffineTransform3D
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from org.scijava.vecmath import Vector3f
from mpicbg.models import Point, PointMatch, RigidModel3D, NotEnoughDataPointsException
from itertools import imap, izip, product
from jarray import array, zeros
from java.util import ArrayList
from java.util.concurrent import Executors, Callable, Future
from java.lang import Runtime
from ij import IJ
import os, csv, sys
from synchronize import make_synchronized


@make_synchronized
def syncPrint(msg):
  print msg


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
    """ Compare the angles, if less than epsilon, compare the vector lengths.
       Return True when deemed similar within measurement error brackets. """
    return abs(self.angle - other.angle) < angle_epsilon \
       and abs(self.len1 - other.len1) + abs(self.len2 - other.len2) < len_epsilon_sq

  @staticmethod
  def subtract(loc1, loc2):
    return (loc1.getFloatPosition(d) - loc2.getFloatPosition(d)
            for d in xrange(loc1.numDimensions()))

  @staticmethod
  def fromSearch(center, p1, d1, p2, d2):
    """ center, p1, p2 are 3 RealLocalizable, with center being the peak
        and p1, p2 being the wings (the other two points).
        p1 is always closer to center than p2 (d1 < d2).
        d1, d2 are the square distances from center to p1, p2
        (could be computed here, but RadiusNeighborSearchOnKDTree did it). """
    pos = tuple(center.getFloatPosition(d) for d in xrange(center.numDimensions()))
    v1 = Vector3f(Constellation.subtract(p1, center))
    v2 = Vector3f(Constellation.subtract(p2, center))
    return Constellation(v1.angle(v2), d1, d2, pos)

  @staticmethod
  def fromRow(row):
    """ Expects: row = [angle, len1, len2, x, y, z] """
    return Constellation(row[0], row[1], row[2], row[3:])

  def asRow(self):
    "Returns: [angle, len1, len2, position.x, position,y, position.z"
    return (self.angle, self.len1, self.len2) + tuple(self.position.getW())

  @staticmethod
  def csvHeader():
    return ["angle", "len1", "len2", "x", "y", "z"]


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

  def toRows(self):
    return [tuple(p1.getW()) + tuple(p2.getW())
            for p1, p2 in self.pointmatches]

  @staticmethod
  def fromRows(rows):
    """ rows: from a CSV file, as lists of strings. """
    return PointMatches([PointMatch(Point(array(imap(float, row[0:3]), 'd')),
                                    Point(array(imap(float, row[3:6]), 'd')))
                         for row in rows])

  @staticmethod
  def csvHeader():
    return ["x1", "y1", "z1", "x2", "y2", "z2"]

  @staticmethod
  def asRow(pm):
    return tuple(pm.getP1().getW()) + tuple(pm.getP2().getW())


def saveFeatures(img_filename, directory, features, params):
  path = os.path.join(directory, img_filename) + ".features.csv"
  try:
    with open(path, 'w') as csvfile:
      w = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
      # First two rows: parameter names and values
      keys = params.keys()
      w.writerow(keys)
      w.writerow(tuple(params[key] for key in keys))
      # Feature header
      w.writerow(Constellation.csvHeader())
      # One row per Constellation feature
      for feature in features:
        w.writerow(feature.asRow())
      # Ensure it's written
      csvfile.flush()
      os.fsync(csvfile.fileno())
  except:
    syncPrint("Failed to save features at %s" % path)
    syncPrint(str(sys.exc_info()))


def loadFeatures(img_filename, directory, params, validateOnly=False, epsilon=0.00001):
  """ Attempts to load features from filename + ".features.csv" if it exists,
      returning a list of Constellation features or None.
      params: dictionary of parameters with which features are wanted now,
              to compare with parameter with which features were extracted.
              In case of mismatch, return None.
      epsilon: allowed error when comparing floating-point values.
      validateOnly: if True, return after checking that parameters match. """
  try:
    csvpath = os.path.join(directory, img_filename + ".features.csv")
    if os.path.exists(csvpath):
      with open(csvpath, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        # First line contains parameter names, second line their values
        paramsF = dict(izip(reader.next(), imap(float, reader.next())))
        for name in paramsF:
          if abs(params[name] - paramsF[name]) > 0.00001:
            syncPrint("Mismatching parameters: '%s' - %f != %f" % (name, params[name], paramsF[name]))
            return None
        if validateOnly:
          return True # would return None above, which is falsy
        reader.next() # skip header with column names
        features = [Constellation.fromRow(map(float, row)) for row in reader]
        syncPrint("Loaded %i features for %s" % (len(features), img_filename))
        return features
    else:
      syncPrint("No stored features found at %s" % csvpath)
      return None
  except:
    syncPrint("Could not load features for %s" % img_filename)
    syncPrint(str(sys.exc_info()))
    return None


def savePointMatches(img_filename1, img_filename2, pointmatches, directory, params):
  filename = img_filename1 + '.' + img_filename2 + ".pointmatches.csv"
  path = os.path.join(directory, filename)
  try:
    with open(path, 'w') as csvfile:
      w = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
      # First two rows: parameter names and values
      keys = params.keys()
      w.writerow(keys)
      w.writerow(tuple(params[key] for key in keys))
      # PointMatches header
      w.writerow(PointMatches.csvHeader())
      # One PointMatch per row
      for pm in pointmatches:
        w.writerow(PointMatches.asRow(pm))
      # Ensure it's written
      csvfile.flush()
      os.fsync(csvfile.fileno())
  except:
    syncPrint("Failed to save pointmatches at %s" % path)
    syncPrint(str(sys.exc_info()))
    


def loadPointMatches(img1_filename, img2_filename, directory, params, epsilon=0.00001):
  """ Attempts to load point matches from filename1 + '.' + filename2 + ".pointmatches.csv" if it exists,
      returning a list of PointMatch instances or None.
      params: dictionary of parameters with which pointmatches are wanted now,
              to compare with parameter with which pointmatches were made.
              In case of mismatch, return None.
      epsilon: allowed error when comparing floating-point values. """
  try:
    csvpath = os.path.join(directory, img1_filename + '.' + img2_filename + ".pointmatches.csv")
    if not os.path.exists(csvpath):
      syncPrint("No stored pointmatches found at %s" % csvpath)
      return None
    with open(csvpath, 'r') as csvfile:
      reader = csv.reader(csvfile, delimiter=',', quotechar='"')
      # First line contains parameter names, second line their values
      paramsF = dict(izip(reader.next(), imap(float, reader.next())))
      for name in paramsF:
        if abs(params[name] - paramsF[name]) > 0.00001:
          syncPrint("Mismatching parameters: '%s' - %f != %f" % (name, params[name], paramsF[name]))
          return None
      reader.next() # skip header with column names
      pointmatches = PointMatches.fromRows(reader).pointmatches
      syncPrint("Loaded %i pointmatches for %s, %s" % (len(pointmatches), img1_filename, img2_filename))
      return pointmatches
  except:
    syncPrint("Could not load pointmatches for pair %s, %s" % (img1_filename, img2_filename))
    syncPrint(str(sys.exc_info()))
    return None


def makeFeatures(img_filename, img_loader, getCalibration, csv_dir, params):
  """ Helper function to extract features from an image. """
  img = img_loader.load(img_filename)
  syncPrint("img name: %s, instance: %s" % (img_filename, str(img)))
  # Find a list of peaks by difference of Gaussian
  peaks = getDoGPeaks(img, getCalibration(img_filename),
                      params['sigmaSmaller'], params['sigmaLarger'],
                      params['minPeakValue'])
  # Create a KDTree-based search for nearby peaks
  search = makeRadiusSearch(peaks)
  # Create list of Constellation features
  features = extractFeatures(peaks, search,
                             params['radius'], params['min_angle'], params['max_per_peak'])
  # Store features in a CSV file
  saveFeatures(img_filename, csv_dir, features, params)
  return features

# Partial implementation of a Future, to simulate it
class Getter(Future):
  def __init__(self, ob):
    self.ob = ob
  def get(self):
    return self.ob


def findPointMatches(img1_filename, img2_filename, img_loader, getCalibration, csv_dir, exe, params):
  """ Attempt to load them from a CSV file, otherwise compute them and save them. """
  # Attempt to load pointmatches from CSV file
  pointmatches = loadPointMatches(img1_filename, img2_filename, csv_dir, params)
  if pointmatches is not None:
    return pointmatches

  # Load features from CSV files
  # otherwise compute them and save them.
  img_filenames = [img1_filename, img2_filename]
  names = set(["minPeakValue", "sigmaSmaller", "sigmaLarger",
                "radius", "min_angle", "max_per_peak"])
  feature_params = {k: params[k] for k in names}
  csv_features = [loadFeatures(img1_filename, csv_dir, feature_params)
                  for img_filename in img_filenames]
  # If features were loaded, just return them, otherwise compute them (and save them to CSV files)
  futures = [Getter(fs) if fs
             else exe.submit(Task(makeFeatures, img_filename, img_loader, getCalibration, csv_dir, feature_params))
             for fs, img_filename in izip(csv_features, img_filenames)]
  features = [f.get() for f in futures]
  
  for img_filename, fs in izip(img_filenames, features):
    syncPrint("Found %i constellation features in image %s" % (len(fs), img_filename))

  # Compare all possible pairs of constellation features: the PointMatches
  pm = PointMatches.fromFeatures(features[0], features[1],
                                   params["angle_epsilon"], params["len_epsilon_sq"])

  syncPrint("Found %i point matches between:\n    %s\n    %s" % \
            (len(pm.pointmatches), img1_filename, img2_filename))

  # Store as CSV file
  names = set(["minPeakValue", "sigmaSmaller", "sigmaLarger", # DoG peak params
               "radius", "min_angle", "max_per_peak",         # Constellation params
               "angle_epsilon", "len_epsilon_sq"])            # pointmatches params
  pm_params = {k: params[k] for k in names}
  savePointMatches(img1_filename, img2_filename, pm.pointmatches, csv_dir, pm_params)
  #
  return pm.pointmatches


def ensureFeatures(img_filename, img_loader, getCalibration, csv_dir, params):
  names = set(["minPeakValue", "sigmaSmaller", "sigmaLarger",
               "radius", "min_angle", "max_per_peak"])
  feature_params = {k: params[k] for k in names}
  if not loadFeatures(img_filename, csv_dir, feature_params, validateOnly=True):
    # Create features from scratch, which overwrites any CSV files
    makeFeatures(img_filename, img_loader, getCalibration, csv_dir, params)
    # TODO: Delete CSV files for pointmatches, if any


def fit(model, pointmatches, n_iterations, maxEpsilon,
        minInlierRatio, minNumInliers, maxTrust):
  """ Fit a model to the pointmatches, finding the subset of inlier pointmatches
      that agree with a joint transformation model. """
  inliers = ArrayList()
  try:
    modelFound = model.filterRansac(pointmatches, inliers, n_iterations,
                                    maxEpsilon, minInlierRatio, minNumInliers, maxTrust)
  except NotEnoughDataPointsException, e:
    syncPrint(str(e))
  return modelFound, inliers


def fitModel(img1_filename, img2_filename, img_loader, getCalibration, csv_dir, model, exe, params):
  pointmatches = findPointMatches(img1_filename, img2_filename, img_loader, getCalibration, csv_dir, exe, params)
  modelFound, inliers = fit(model, pointmatches, params["n_iterations"],
                            params["maxEpsilon"], params["minInlierRatio"],
                            params["minNumInliers"], params["maxTrust"])
  if modelFound:
    syncPrint("Found %i inliers for:\n    %s\n    %s" % (len(inliers), img1_filename, img2_filename))
  else:
    syncPrint("Model not found for:\n    %s\n    %s" % (img1_filename, img2_filename))
    # Return identity
    model.set(*[1, 0, 0, 0,
                0, 1, 0, 0,
                0, 0, 1, 0])
  return model

# A wrapper for executing functions in concurrent threads
class Task(Callable):
  def __init__(self, fn, *args):
    self.fn = fn
    self.args = args
  def call(self):
    return self.fn(*self.args)


def computeForwardTransforms(img_filenames, img_loader, getCalibration, csv_dir, exe, params):
  """ Compute transforms from image i to image i+1,
      returning an identity transform for the first image,
      and with each transform being from i to i+1 (forward transforms).
      Returns a list of affine 3D matrices, each a double[] with 12 values.
  """
  try:
    # Ensure features exist in CSV files, or create them
    futures = [exe.submit(Task(ensureFeatures, img_filename, img_loader, getCalibration, csv_dir, params))
               for img_filename in img_filenames]
    # Wait until all complete
    for f in futures:
      f.get()

    # Create models: ensures first that pointmatches exist in CSV files, or creates them
    futures = [exe.submit(Task(fitModel, img1_filename, img2_filename, img_loader,
                               getCalibration, csv_dir, RigidModel3D(), exe, params))
               for img1_filename, img2_filename in izip(img_filenames, img_filenames[1:])]
    # Wait until all complete
    models = [f.get() for f in futures]
  
    # First image gets identity
    matrices = [array([1, 0, 0, 0,
                       0, 1, 0, 0,
                       0, 0, 1, 0], 'd')] + [model.getMatrix(zeros(12, 'd')) for model in models]

    return matrices

  finally:
    exe.shutdown()


def asBackwardAffineTransforms(matrices):
    """ Transforms are img1 -> img2, and we want the opposite: so invert each.
        Also, each image was registered to the previous, so must concatenate all previous transforms. """
    aff_previous = AffineTransform3D()
    aff_previous.identity() # set to identity
    affines = [aff_previous] # first image at index 0

    for matrix in matrices[1:]: # skip zero
      aff = AffineTransform3D()
      aff.set(*matrix)
      aff = aff.inverse() # transform defines img1 -> img2, we want the opposite
      aff.preConcatenate(aff_previous) # Make relative to prior image
      affines.append(aff) # Store
      aff_previous = aff # next iteration

    return affines


def viewTransformed(img, calibration, affine):
  """ View img transformed to isotropy (via the calibration)
      and transformed by the affine. """
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


def registeredView(img_filenames, img_loader, getCalibration, csv_dir, exe, params):
  """ img_filenames: a list of file names
      csv_dir: directory for CSV files
      exe: an ExecutorService for concurrent execution of tasks
      params: dictionary of parameters
      returns a stack view of all registered images, e.g. 3D volumes as a 4D. """
  matrices = computeForwardTransforms(img_filenames, img_loader, getCalibration, csv_dir, exe, params)
  affines = asBackwardAffineTransforms(matrices)
  #
  for i, affine in enumerate(affines):
    matrix = affine.getRowPackedCopy()
    print i, "matrix: [", matrix[0:4]
    print "          ", matrix[4:8]
    print "          ", matrix[8:12], "]"
  #
  # TODO: should use a lazy loader for the stack
  images = [img_loader.load(img_filename) for img_filename in img_filenames]
  registered = Views.stack([viewTransformed(img, getCalibration(img_filename), affine)
                            for img, img_filename, affine
                            in izip(images, img_filenames, affines)])
  return registered


# Test

# Prepare test data
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

# Rotate the cube on the X axis to the top
img3 = Views.zeroMin(Views.rotate(img1, 2, 1))

# Reduce Z resolution: make them anisotropic but in a different direction
nth = 2
img1 = dropSlices(img1, nth)
img2 = dropSlices(img2, nth)
img3 = dropSlices(img3, nth)

# The sequence of images to transform, each relative to the previous
images = [img1, img2, img3]

IL.wrap(Views.stack(images), "unregistered").show()


# PARAMETERS
calibrations = [[1.0, 1.0, 1.0 * nth],
                [1.0, 1.0, 1.0 * nth],
                [1.0, 1.0, 1.0 * nth]]

# Pretend file names:
img_filenames = ["img1", "img2", "img3"]

# Pretend loader:
class ImgLoader():
  def load(self, img_filename):
    return globals()[img_filename]

img_loader = ImgLoader()

# Pretend calibration getter
def getCalibration(img_filename):
  return calibrations[img_filenames.index(img_filename)]


# Parameters for DoG difference of Gaussian to detect soma positions
somaDiameter = 8 * calibrations[0][0]
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


n_threads = Runtime.getRuntime().availableProcessors()
exe = Executors.newFixedThreadPool(n_threads)
csv_dir = "/tmp/"

registered = registeredView(img_filenames, img_loader, getCalibration, csv_dir, exe, params)

IL.wrap(registered, "registered").show()
