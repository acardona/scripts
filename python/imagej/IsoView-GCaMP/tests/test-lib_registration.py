import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/lib/")

from registration import registeredView

from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from mpicbg.models import RigidModel3D
from ij import IJ




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


csv_dir = "/tmp/"

registered = registeredView(img_filenames, img_loader, getCalibration, csv_dir, RigidModel3D, params, exe=None)

IL.wrap(registered, "registered").show()