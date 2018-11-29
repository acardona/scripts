import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.lsm.isoview import deconvolveTimePoints
from mpicbg.models import RigidModel3D


# The folder with the sequence of TM\d+ folders, one per time point in the 4D series.
# Each folder should contain 4 KLB files, one per camera view of the IsoView microscope.
srcDir = "/home/albert/shares/zlaticlab/Nadine/Raghav/2017-05-10/GCaMP6s_1_20170510_115003.corrected/SPM00/"

# A folder to save deconvolved images in, and CSV files describing features, point matches and transformations
targetDir = "/home/albert/shares/cardonalab/Albert/deconvolved/"

# Path to the volume describing the point spread function (PSF)
kernelPath = "/home/albert/lab/Raghav-IsoView-PSF/PSF-19x19x25.tif"

# The calibration is [0.40625, 0.40625, 2.03125]
# To preserve XY pixels, expand Z only:
calibration = [1.0, 1.0, 5.0]

# The transformations of each timepoint onto the camera at index zero.
def cameraTransformations(img1, img2, img3, img4, calibration):
  return {
    0: [1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0],
    1: [-1.0, 0.0, 0.0, img1.dimension(0) * calibration(0) - 195,
         0.0, 1.0, 0.0, 54.0,
         0.0, 0.0, 1.0,  8.0],
    2: [ 0.0, 0.0, 1.0,  0.0,
         0.0, 1.0, 0.0, 25.0,
        -1.0, 0.0, 0.0, img2.dimension(2) * calibration[2] + 41.0],
    3: [0.0, 0.0, 1.0,    0.0,
        0.0, 1.0, 0.0,   25.0,
        1.0, 0.0, 0.0, -159.0]
  }


# Parameters for DoG difference of Gaussian to detect soma positions
somaDiameter = 8 * calibration[0]
paramsDoG = {
  "minPeakValue": 20, # Determined by hand
  "sigmaSmaller": somaDiameter / 4.0, # in calibrated units: 1/4 soma
  "sigmaLarger": somaDiameter / 2.0, # in calibrated units: 1/2 soma
}

paramsFeatures = {
  # Parameters for features
  "radius": somaDiameter * 15, # for searching nearby peaks
  "min_angle": 0.25, # in radians, between vectors to p1 and p2
  "max_per_peak": 30, # maximum number of constellations to create per peak

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

# Deconvolution parameters
paramsDeconvolution = {
  "blockSize": [128, 128, 128],
  "CM_0_1_n_iterations": 10,
  "CM_2_3_n_iterations": 30,
}

# Joint dictionary of parameters
params = {}
params.update(paramsDoG)
params.update(paramsFeatures)
params.update(paramsModel)
params.update(paramsDeconvolution)


# A region of interest for each camera view, for cropping after registration but prior to deconvolution
roi = ([1, 228, 0], # top-left coordinates
       [1 + 406 -1, 228 + 465 -1, 325 -1]) # bottom-right coordinates (inclusive, hence the -1)


# The transformation model for registering views onto each other
modelclass = RigidModel3D

deconvolveTimePoints(srcDir, targetDir, kernelPath, calibration,
                    cameraTransformations, params, modelclass, roi)






