import sys
sys.path.append("//home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.isoview import deconvolveTimePoints
from mpicbg.models import RigidModel3D, TranslationModel3D
from net.imglib2.img.display.imagej import ImageJFunctions as IL


# The folder with the sequence of TM\d+ folders, one per time point in the 4D series.
# Each folder should contain 4 KLB files, one per camera view of the IsoView microscope.
srcDir = "/home/albert/shares/zlaticlab/Nadine/Raghav/2017-05-10/GCaMP6s_1_20170510_115003.corrected/SPM00/"

# A folder to save deconvolved images in, and CSV files describing features, point matches and transformations
targetDir = "/home/albert/shares/cardonalab/Albert/2017-05-10_1018/"

# Path to the volume describing the point spread function (PSF)
kernelPath = "/home/albert/shares/cardonalab/Albert/Raghav-IsoView-PSF/PSF-19x19x25.tif"

# The calibration is [0.40625, 0.40625, 2.03125]
# To preserve XY pixels, expand Z only:
calibration = [1.0, 1.0, 5.0]

# The transformations of each timepoint onto the camera at index zero.
def cameraTransformations(dims0, dims1, dims2, dims3, calibration):
  return {
    0: [1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0],
    1: [-1.0, 0.0, 0.0, dims1[0] * calibration[0] - 195,
         0.0, 1.0, 0.0, 54.0,
         0.0, 0.0, 1.0,  8.0],
    2: [ 0.0, 0.0, 1.0,  0.0,
         0.0, 1.0, 0.0, 25.0,
        -1.0, 0.0, 0.0, dims2[2] * calibration[2] + 41.0],
    3: [0.0, 0.0, 1.0,    0.0,
        0.0, 1.0, 0.0,   25.0,
        1.0, 0.0, 0.0, -159.0]
  }


# Deconvolution parameters
paramsDeconvolution = {
  "blockSizes": None, # None means the image size + kernel size. Otherwise specify like e.g. [[128, 128, 128]] for img in images]
  "CM_0_1_n_iterations": 5,
  "CM_2_3_n_iterations": 7,
}

# Joint dictionary of parameters
params = {}
params.update(paramsDeconvolution)


# A region of interest for each camera view, for cropping after registration but prior to deconvolution
roi = ([1, 228, 0], # top-left coordinates
       [1 + 406 -1, 228 + 465 -1, 0 + 325 -1]) # bottom-right coordinates (inclusive, hence the -1)

# After cropping, these are the finer transformations from any camera view to CM00.
# (discovered with the script: load_four_cameras_single_timepoint_transformed_registration-check.py)
# These registrations don't change from timepoint to timepoint within the same time series acquisition.

# All 4 cameras relative to CM00
fineTransformsPostROICrop = \
   [[1, 0, 0, 0,
     0, 1, 0, 0,
     0, 0, 1, 0],
     
    [0.9999949529841275, -0.0031770224721305684, 2.3118912942710207e-05, -1.6032353998500826,
     0.003177032139125933, 0.999994860398559, -0.00043086338151948394, -0.4401520585103873,
     -2.1749931475206362e-05, 0.0004309346564745992, 0.9999999069111268, 6.543187040788581],
     
    [0.9997987121628504, -0.009472768268010913, -0.01768620419553878, 3.930297652126247,
     0.009342009169030474, 0.9999285252136545, -0.007461322183871208, 2.427195709390503,
     0.017755619453893427, 0.0072945956287064715, 0.999815746451526, 1.0095040792330394],
     
    [0.9998779568655723, -0.015226665797195312, 0.0034957149525624287, 3.2525448680408826,
     0.01523705113687456, 0.9998795170641414, -0.002963718649331728, -2.1506102341571323,
     -0.0034501662251717287, 0.003016621335310332, 0.9999894981192247, 2.447694931285838]]


# The transformation model for registering views onto each other
modelclass = RigidModel3D

deconvolveTimePoints(srcDir, targetDir, kernelPath, calibration,
                    cameraTransformations, fineTransformsPostROICrop,
                    params, roi, camera_groups=((0, 1), (2, 3)),
                    subrange=range(0, 400))






