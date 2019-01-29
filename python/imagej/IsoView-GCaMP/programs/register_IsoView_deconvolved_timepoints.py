import sys
sys.path.append("//home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.isoview import registerDeconvolvedTimePoints
from mpicbg.models import RigidModel3D, TranslationModel3D
from net.imglib2.img.display.imagej import ImageJFunctions as IL, ImageJVirtualStackUnsignedShort
from ij import ImagePlus, CompositeImage

# Register deconvolved views across time and show them as a VirtualStack

# A folder to save deconvolved images in, and CSV files describing features, point matches and transformations
targetDir = "/home/albert/shares/cardonalab/Albert/2017-05-10_1018/"

# Deconvolved images have isotropic calibration
calibration = [1.0, 1.0, 1.0]

# Parameters for registering deconvolved time points serially

# Parameters for DoG difference of Gaussian to detect soma positions
somaDiameter = 8 * calibration[0]
paramsDoG = {
  "minPeakValue": 30, # Determined by hand
  "sigmaSmaller": somaDiameter / 4.0, # in calibrated units: 1/4 soma
  "sigmaLarger": somaDiameter / 2.0, # in calibrated units: 1/2 soma
}

paramsFeatures = {
  # Parameters for features
  "radius": somaDiameter * 5, # for searching nearby peaks
  "min_angle": 0.25, # in radians, between vectors to p1 and p2
  "max_per_peak": 10, # maximum number of constellations to create per peak

  # Parameters for comparing constellations to find point matches
  "angle_epsilon": 0.02, # in radians. 0.05 is 2.8 degrees, 0.02 is 1.1 degrees
  "len_epsilon_sq": pow(somaDiameter, 2), # in calibrated units, squared
  "pointmatches_nearby": 1, # if 1 (True), searches for possible matches only within radius
  "pointmatches_search_radius": somaDiameter * 2
}

# RANSAC parameters: reduce list of pointmatches to a spatially coherent subset
paramsModel = {
  "maxEpsilon": somaDiameter, # max allowed alignment error in calibrated units (a distance)
  "minInlierRatio": 0.0000001, # ratio inliers/candidates
  "minNumInliers": 5, # minimum number of good matches to accept the result
  "n_iterations": 2000, # for estimating the model
  "maxTrust": 4, # for rejecting candidates
}

paramsTileConfiguration = {
  "n_adjacent": 6,
  "fixed_tile_index": 0, # first one
  "maxAllowedError": 0, # Saalfeld recommends 0
  "maxPlateauwidth": 200, # Like in TrakEM2
  "maxIterations": 1000, # Saalfeld recommends 1000
  "damp": 1.0, # Saalfeld recommends 1.0, which mens no damp
  #"maxMeanFactor": 1.0, # TODO adjust -- unused, only for TileConfiguration.optimizeAndFilter, which is not used here.
}

# Joint dictionary of parameters
params = {}
params.update(paramsDoG)
params.update(paramsFeatures)
params.update(paramsModel)
params.update(paramsTileConfiguration)

modelclass = TranslationModel3D

img4D = registerDeconvolvedTimePoints(targetDir,
                                      params,
                                      modelclass,
                                      exe=None,
                                      verbose=False,
                                      subrange=range(0, 400))
# IL.wrap gets structure wrong: uses channels for slices, and slices for frames
#IL.wrap(img4D, "0-399").show()

stack = ImageJVirtualStackUnsignedShort.wrap(img4D)
imp = ImagePlus("0-399", stack)
imp.setDimensions(1, img4D.dimension(2), img4D.dimension(3))
comp = CompositeImage(imp, CompositeImage.GRAYSCALE)
comp.show()