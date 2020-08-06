import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")

from lib.registration import registeredView

from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.io import Load, IJLoader
from mpicbg.models import TranslationModel3D
import os

dataDir = "/home/albert/lab/scripts/data/4D-series-zip/"

filepaths = [os.path.join(dataDir, filename)
             for filename in sorted(os.listdir(dataDir))
             if filename.endswith(".zip")]

unregistered = Load.lazyStack(filepaths, IJLoader())

img_str_indices = map(str, range(len(filepaths)))

class ImgLoader:
  def load(self, str_index):
    return Views.hyperSlice(unregistered, 3, int(str_index))

img_loader = ImgLoader()

def getCalibration(img_filename):
  # All equal
  # Actual: in microns per pixel
  #return [0.40625, 0.40625, 2.03125]
  # Desired: keep XY pixels at 1.0
  #return [1.0, 1.0, 5.0]
  # This test: already registered by the Keller lab, deconvolved, and turned into isotropic volumes:
  return [1.0, 1.0, 1.0]

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
  "pointmatches_nearby": True, # if True, searches for possible matches only within radius
  "pointmatches_search_radius": somaDiameter #
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

registered = registeredView(img_str_indices, img_loader, getCalibration,
                            csv_dir, TranslationModel3D, params, exe=None)

IL.wrap(unregistered, "unregistered").show()
IL.wrap(registered, "registered").show()