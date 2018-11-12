from mpicbg.models import NotEnoughDataPointsException
from java.util import ArrayList
from net.imglib2.view import Views
from net.imglib2.realtransform import RealViews, AffineTransform3D, Scale3D
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from jarray import array, zeros
from itertools import izip, imap
import os, sys, csv
from os.path import basename
# local lib functions:
from util import syncPrint, Task, nativeArray, newFixedThreadPool
from features import findPointMatches, ensureFeatures


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
  """ The model can be any subclass of mpicbg.models.Affine3D, such as:
        TranslationModel3D, RigidModel3D, SimilarityModel3D,
        AffineModel3D, InterpolatedAffineModel3D
      Returns the transformation matrix as a 1-dimensional array of doubles,
      which is the identity when the model cannot be fit. """
  pointmatches = findPointMatches(img1_filename, img2_filename, img_loader, getCalibration, csv_dir, exe, params)
  if 0 == len(pointmatches):
    modelFound = False
  else:
    modelFound, inliers = fit(model, pointmatches, params["n_iterations"],
                              params["maxEpsilon"], params["minInlierRatio"],
                              params["minNumInliers"], params["maxTrust"])
  if modelFound:
    syncPrint("Found %i inliers for:\n    %s\n    %s" % (len(inliers),
      basename(img1_filename), basename(img2_filename)))
    a = nativeArray('d', [3, 4])
    model.toMatrix(a) # Can't use model.toArray: different order of elements
    return a[0] + a[1] + a[2] # Concat: flatten to 1-dimensional array:
  else:
    syncPrint("Model not found for:\n    %s\n    %s" % (img1_filename, img2_filename))
    # Return identity
    return array([1, 0, 0, 0,
                  0, 1, 0, 0,
                  0, 0, 1, 0], 'd')


def saveMatrices(name, matrices, csv_dir):
  """ Store all matrices in a CSV file named <name>.csv """
  path = os.path.join(csv_dir, name + ".csv")
  try:
    with open(path, 'w') as csvfile:
      w = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)
      # Write header: 12 m<i><j> names
      w.writerow(tuple("m%i%i" % (i,j) for i in (0,1,2) for j in (0,1,2,3)))
      for matrix in matrices:
        w.writerow(matrix)
      csvfile.flush()
      os.fsync(csvfile.fileno())
  except:
    syncPrint("Failed to save matrices at path %s" % path)
    syncPrint(str(sys.exc_info()))


def loadMatrices(name, csv_dir):
  """ Load all matrices as a list of arrays of doubles
      from a CSV file named <name>.csv """
  path = os.path.join(csv_dir, name + ".csv")
  if not os.path.exists(path):
    return None
  try:
    with open(path, 'r') as csvfile:
      reader = csv.reader(csvfile, delimiter=',', quotechar='"')
      reader.next() # skip header
      matrices = [array(imap(float, row), 'd') for row in reader]
      return matrices
  except:
    syncPrint("Could not load matrices from path %s" % path)
    syncPrint(str(sys.exc_info()))

def computeForwardTransforms(img_filenames, img_loader, getCalibration, csv_dir, exe, modelclass, params):
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
                               getCalibration, csv_dir, modelclass(), exe, params))
               for img1_filename, img2_filename in izip(img_filenames, img_filenames[1:])]
    # Wait until all complete
    # First image gets identity
    matrices = [array([1, 0, 0, 0,
                       0, 1, 0, 0,
                       0, 0, 1, 0], 'd')] + [f.get() for f in futures]

    return matrices

  finally:
    exe.shutdown()


def asBackwardConcatTransforms(matrices, transformclass=AffineTransform3D):
    """ Transforms are img1 -> img2, and we want the opposite: so invert each.
        Also, each image was registered to the previous, so must concatenate all previous transforms. """
    # Special-case for speed
    if transformclass == Translation3D:
      tx, ty, tz = 0.0, 0.0, 0.0
      translations = []
      for matrix in matrices:
        # Subtract: same as inverse
        tx -= matrix[3]
        ty -= matrix[7]
        tz -= matrix[11]
        translations.append(Translation3D(tx, ty, tz))

      return translations

    # Else, use AffineTransform3D
    aff_previous = transformclass()
    # It's puzzling that AffineTransform3D is not initialized to identity
    aff_previous.identity() # set to identity
    affines = [aff_previous] # first image at index 0 gets identity

    for matrix in matrices[1:]: # skip zero
      aff = AffineTransform3D()
      aff.set(*matrix)
      aff = aff.inverse() # transform defines img1 -> img2, we want the opposite
      aff.preConcatenate(aff_previous) # Make relative to prior image
      affines.append(aff) # Store
      aff_previous = aff # next iteration

    return affines


def viewTransformed(img, calibration, transform):
  """ View img transformed to isotropy (via the calibration)
      and transformed by the affine. """
  imgE = Views.extendZero(img)
  imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
  if type(transform) == AffineTransform3D:
    scale3d = AffineTransform3D()
    scale3d.set(calibration[0], 0, 0, 0,
                0, calibration[1], 0, 0,
                0, 0, calibration[2], 0)
    affine = transform.copy()
    affine.concatenate(scale3d)
    imgT = RealViews.transform(imgI, affine)
  else:
    imgT = RealViews.transform(imgI, Scale3D(*calibration))
    imgT = RealViews.transform(imgT, transform)
  # dimensions
  minC = [0, 0, 0]
  maxC = [int(img.dimension(d) * cal) -1 for d, cal in enumerate(calibration)]
  imgB = Views.interval(imgT, minC, maxC)
  return imgB


def registeredView(img_filenames, img_loader, getCalibration, csv_dir, modelclass, params, exe=None):
  """ img_filenames: a list of file names
      csv_dir: directory for CSV files
      exe: an ExecutorService for concurrent execution of tasks
      params: dictionary of parameters
      returns a stack view of all registered images, e.g. 3D volumes as a 4D. """
  if not exe:
    exe = newFixedThreadPool()
  matrices = computeForwardTransforms(img_filenames, img_loader, getCalibration, csv_dir, exe, modelclass, params)
  affines = asBackwardConcatTransforms(matrices)
  #
  for i, affine in enumerate(affines):
    matrix = affine.getRowPackedCopy()
    print i, "matrix: [", matrix[0:4]
    print "           ", matrix[4:8]
    print "           ", matrix[8:12], "]"
  #
  # TODO replace with a lazy loader
  images = [img_loader.load(img_filename) for img_filename in img_filenames]
  registered = Views.stack([viewTransformed(img, getCalibration(img_filename), affine)
                            for img, img_filename, affine
                            in izip(images, img_filenames, affines)])
  return registered

