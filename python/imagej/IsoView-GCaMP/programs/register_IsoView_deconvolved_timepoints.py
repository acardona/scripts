import sys, os
sys.path.append(os.path.dirname(os.path.dirname(sys.argv[0]))
from lib.isoview import registerDeconvolvedTimePoints
from mpicbg.models import RigidModel3D, TranslationModel3D
from net.imglib2.img.display.imagej import ImageJFunctions as IL, ImageJVirtualStackUnsignedShort
from ij import ImagePlus, CompositeImage
from ij.gui import YesNoCancelDialog
from lib.util import newFixedThreadPool
from lib.ui import showStack
from lib.io import writeN5

# Register deconvolved fused views across time and show them as a VirtualStack,
# and also optionally export them as an N5 volume for fast random access

# A folder to save deconvolved images in, and CSV files describing features, point matches and transformations
# and where the deconvolved fused stacks already exist
targetDir = "/home/albert/shares/cardonalab/Albert/2017-05-10_1018/"

first_timepoint = 0
last_timepoint = 399
fixed_tile_indices = [last_timepoint / 2 + 1] # just the middle one

# Deconvolved images have isotropic calibration
calibration = [1.0, 1.0, 1.0]

# Parameters for registering deconvolved time points serially

# Parameters for DoG difference of Gaussian to detect soma positions
somaDiameter = 8 * calibration[0]
paramsDoG = {
  "minPeakValue": 20, # Determined by hand
  "sigmaSmaller": somaDiameter / 4.0, # in calibrated units: 1/4 soma
  "sigmaLarger": somaDiameter / 2.0, # in calibrated units: 1/2 soma
}

paramsFeatures = {
  # Parameters for features
  "radius": somaDiameter * 5, # for searching nearby peaks
  "min_angle": 0.25, # in radians, between vectors to p1 and p2
  "max_per_peak": 20, # maximum number of constellations to create per peak

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
  "minNumInliers": 20, # minimum number of good matches to accept the result
  "n_iterations": 2000, # for estimating the model
  "maxTrust": 4, # for rejecting candidates
}

paramsTileConfiguration = {
  "n_adjacent": 12,
  "fixed_tile_indices": fixed_tile_indices,
  "maxAllowedError": 0, # Saalfeld recommends 0
  "maxPlateauwidth": 200, # Like in TrakEM2
  "maxIterations": 1000, # Saalfeld recommends 1000
  "damp": 1.0, # Saalfeld recommends 1.0, which means no damp
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
                                      subrange=range(first_timepoint, last_timepoint + 1))
# IL.wrap gets structure wrong: uses channels for slices, and slices for frames
#IL.wrap(img4D, "0-399").show()

showStack(img4D, title="%i-%i" % (first_timepoint, last_timepoint))


# Materialize (write to disk) the registered deconvolved stacks
targetDirN5 = os.path.join(targetDir, "deconvolved/n5/")
nameN5 = "%s_%i-%i_%ix%ix%ix%i" % (targetDir.split("/")[-2],
                                   first_timepoint, last_timepoint,
                                   img4D.dimension(0),
                                   img4D.dimension(1),
                                   img4D.dimension(2),
                                   img4D.dimension(3))

writeN5Volume = True
if not os.path.exists(targetDirN5):
  os.mkdir(targetDirN5)
else:
  writeN5Volume = False
  yn = YesNoCancelDialog(IJ.getInstance(), "Write N5",
                         "The N5 folder already exists: continue?")
  writeN5Volume = yn.yesPressed()

if writeN5Volume:
  print "N5 volume folder: ", targetDirN5
  print "N5 volume name: ", nameN5
  writeN5(img4D,
          targetDirN5,
          nameN5,
          [img4D.dimension(0), img4D.dimension(1), 5, 1]) # dimensions of the block size: full X, full Y, just 5 Z sections and 1 single time point
