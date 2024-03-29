# Script to register and deconvolve 4D series acquired with the IsoView microscope
# by Raghav Chhetri et al. 2015 Nature Methods (Philipp Keller's lab at HHMI Janelia)
#
# Albert Cardona, 2018-2019
#
# *** INSTRUCTIONS ***
# User: please edit
#
# 1. The source folder 'srcDir',
# 2. The target folder 'tgtDir' (should be writable),
# 3. The 'calibration',
# 4. The 'somaDiameter',
# 5. Optionally, the registration model 'modelclass',
# 5. Optionally, any of the parameters in the 'params' dictionaries.
#
# ... and then push the 'Run' button in this Fiji Script Editor window.
#
# A graphical user interface (GUI) will open, showing:
# - A 4D stack with the 4 3D stacks, one per view, of the first time point.
#   In ImageJ parlance, each 3D stack is a time frame, or frame. We are
#   using here the 4th dimension not as time but as the 4 cameras.
#   Note that each view has already been rotated so as to be in the same
#   orientation as the view of the first camera (named CM00 in the IsoView files).
# 
# - A window titled "Translate & Crop" with fields and buttons showing the X, Y, Z
#   translations of each of the 3D stacks except for the first one (CM00), which is
#   used as reference and it is not meant to be moved.
#   The window has buttons for setting a 2D region of interest (ROI) for cropping
#   prior to launching the new little window for the registration parameters.
#
# Scroll to the middle of the stack (to a slice that you expect will have data)
# and then push "shift+C" to open the Brightness & Contrast dialog. Click on "Auto" for a
# good initial setting.
#
# Browse around the first frame (the first 3D view, which is already the visible one)
# until finding a remarkable feature that you are confident you will see in other views.
# Draw an ROI over it, with the rectangle tool available (selected by default) in the
# Fiji/ImageJ main window. This ROI serves as a reference point.
#
# Now use the bottom slider in the 4D window to view the second frame (the second camera
# view, which would be named CM01 in IsoView parlance). The ROI is still visible,
# as it is independent of the frame. Write down, or remember, which slice (Z coordinate)
# you are in.
# 
# Move the UI window with the X, Y, Z fields near the 4D window, and click on the Z field
# of the "CM01" row. Either use the scroll wheel, or up/down arrows, or type in a number
# (and push return), to edit the translation in the Z axis. The image in the 4D window
# will move accordingly. Try to bring the feature that you saw under the ROI drawn
# over CM00 to the current slice.
#
# Now repeat for the X and Y axes, to bring the feature inside the ROI.
# Then scroll back, using the bottom slider, to the first frame (CM00), and then
# forward again to the second frame (CM01), and check that they look reasonbly
# in register.
# 
# Now repeat for frames 3 (CM02) and 4 (CM03).
#
# When all 4 frames (all 4 camera views) are reasonably in register, draw a large ROI
# enclosing the parts of the image that you want to work with from now on.
# Then using the first slider in the 4D image window, scroll to the first Z where
# any data can be seen, and write that in the "min coords" Z field under "ROI controls".
# Do the same for the last slide.
#
# When done, push "Crop to ROI". Two new windows open:
# - A new 4D window just like before, but cropped in X, Y, Z as desired.
# - A new window titled "Registration", listing all the parameters available
#   below in this script (and which you may have edited).
#   Note that the calibration is now set to 1.0, 1.0, 1.0: that's because
#   the images here are interpolated so as to be isotropic.
#
# Note the chosen ROI will be stored in the target folder 'tgtDir'. Upon reusing
# the same target folder, if the ROI file is present, it will be loaded.
# This is intended for convenience, for either reuse with e.g. different
# parts of the same 4D series, or for a re-run with different parameters.
#
# Push "Run" (here in the "Registration" window) and soon a new 4D window opens,
# with the same data as before but with the registration now refined using e.g.
# a RigidModel3D (translation and rotation only), or using a TranslationModel3D,
# depending on which model you chose here below in the params dictionaries.
# (An AffineModel3D is overkill, and would require regularization.)
#
# Note, the extracted features and point matches will be stored in CSV files
# in the target folder 'tgtDir', along with the parameters used for extracting
# them. Upon re-run, if the parameters haven't changed, these CSV files will
# be loaded (avoiding re-computing features and pointmatches), and the model
# estimated from them, saving lots of time.
# This is intended for re-running quickly to e.g. see the registration computed
# for e.g. the first time point as applied to e.g. another time point.
#
# IMPORTANT: If you have changed the ROI, though, the crop will be different,
# and you should remove these CSV files from the target folder 'tgtDir', as
# the program has no way of knowing what you did.
#
# Now, in the window "Translate & Crop", push "Print coarse transforms",
# and in the window "Registration", push "Print affines".
# These two sets of transforms are what is needed to seed the registration
# of the whole 4D series, using another script.


from org.janelia.simview.klb import KLB
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.realtransform import RealViews, AffineTransform3D
from net.imglib2.cache import CacheLoader
import os, sys
from os.path import basename
from bdv.util import BdvFunctions, Bdv
sys.path.append(os.path.dirname(os.path.dirname(sys.argv[0])))
from lib.ui import showAsStack
from lib.isoview_ui import makeTranslationUI, makeCropUI, makeRegistrationUI
from lib.io import KLBLoader, ImageJLoader, BinaryLoader
from functools import partial
from mpicbg.models import RigidModel3D, TranslationModel3D
from ij import IJ

# START EDITING HERE

#srcDir = "/home/albert/shares/zlaticlab/Nadine/Raghav/2017-05-10/GCaMP6s_1_20170510_115003.corrected/SPM00/"
srcDir = "/home/albert/Desktop/t2/IsoView/"
tgtDir = "/home/albert/Desktop/t2/IsoView/" # to store e.g. CSV files

calibration = [1.0, 1.0, 5.0]

# Img loading function: adjust as desired
# from the lib.io, one of: KLBLoader, ImageJLoader, BinaryLoader
# Note that the BinaryLoader takes argument such as dimensions, header size, byte order, etc.
loader = KLBLoader()
### NOTE: you'll need the same loader in the generated script. ###

# Parameters for feature-based registration
csv_dir = tgtDir # Folder to store CSV files
modelclass = RigidModel3D # or use TranslationModel3D

# Parameters for DoG difference of Gaussian to detect soma positions
somaDiameter = 8 * calibration[0]

paramsDoG = {
  "minPeakValue": 20, # Determined by hand
  "sigmaSmaller": somaDiameter / 4.0, # in calibrated units: 1/4 soma
  "sigmaLarger": somaDiameter / 2.0, # in calibrated units: 1/2 soma
}

# Parameters for feature extraction using points detected by DoG
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

# Parameters for all to all registration
paramsTileConfiguration = {
  "all_to_all": True,
  "fixed_tile_index": [0], # tiles that won't move
  "maxAllowedError": 0, # zero, as recommended by Saalfeld
  "maxPlateauwidth": 200, # like in TrakEM2
  "maxIterations": 1000, # like in TrakEM2
  "damp": 1.0, # default
}


# STOP EDITING HERE

# paths for same timepoint, 4 different cameras
paths = []
timepointDir = srcDir + "TM000000/"
for camera_index, channel_index in zip(xrange(4), [1, 1, 0, 0]):
  paths.append(timepointDir + "SPM00_TM000000_CM0" + str(camera_index) + "_CHN0" + str(channel_index) + ".klb")

for path in paths:
  print basename(path)

img0 = loader.load(paths[0])
img1 = loader.load(paths[1])
img2 = loader.load(paths[2])
img3 = loader.load(paths[3])


# Make all isotropic (virtually, as a view)
scale3D = AffineTransform3D()
scale3D.set(calibration[0], 0.0, 0.0, 0.0,
            0.0, calibration[1], 0.0, 0.0,
            0.0, 0.0, calibration[2], 0.0)

def maxCoords(img):
  return [int(img.dimension(d) * calibration[d] -1) for d in xrange(img.numDimensions())]

# Identity transform for CM00, scaled to isotropy
affine0 = AffineTransform3D()
affine0.identity()
affine0.concatenate(scale3D)

# Expand camera CM00 to isotropy
imgE = Views.extendZero(img0)
imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
imgT = RealViews.transform(imgI, affine0)
imgB0 = Views.interval(imgT, [0, 0, 0], maxCoords(img0))


# Transform camera CM01 to CM00: 180 degrees on Y axis, plus a translation in X
affine1 = AffineTransform3D()
affine1.set(-1.0, 0.0, 0.0, img1.dimension(0),
             0.0, 1.0, 0.0, 0.0,
             0.0, 0.0, 1.0, 0.0)
affine1.concatenate(scale3D)
imgE = Views.extendZero(img1)
imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
imgT = RealViews.transform(imgI, affine1)
imgB1 = Views.interval(imgT, [0, 0, 0], maxCoords(img1))


# Transform camera CM02 to CM00: 90 degrees on Y axis, plus a translation in Z
affine2 = AffineTransform3D()
affine2.set( 0.0, 0.0, 1.0, 0.0,
             0.0, 1.0, 0.0, 0.0,
             -1.0, 0.0, 0.0, img2.dimension(2) * calibration[2])
affine2.concatenate(scale3D)
imgE = Views.extendZero(img2)
imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
imgT = RealViews.transform(imgI, affine2)
imgB2 = Views.interval(imgT, [0, 0, 0], maxCoords(img2))


# Transform camera CM03 to CM00: -90 degrees on Y axis (no need for translation)
affine3 = AffineTransform3D()
affine3.set( 0.0, 0.0, 1.0, 0.0,
             0.0, 1.0, 0.0, 0.0,
             1.0, 0.0, 0.0, 0.0)
affine3.concatenate(scale3D)
imgE = Views.extendZero(img3)
imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
imgT = RealViews.transform(imgI, affine3)
imgB3 = Views.interval(imgT, [0, 0, 0], maxCoords(img3))

original_images = [img0, img1, img2, img3]
images = [imgB0, imgB1, imgB2, imgB3]
imp = showAsStack(images, title="4 views to coarsely register")



# DEBUG: so that I don't have to adjust the test data set manually every time
"""
affine1.set(*[-1.000000, 0.000000, 0.000000, 377.000000,
 0.000000, 1.000000, 0.000000, 50.000000,
 0.000000, 0.000000, 5.000000, 0.000000])
affine2.set(*[0.000000, 0.000000, 5.000000, -11.000000,
 0.000000, 1.000000, 0.000000, 22.000000,
 -1.000000, 0.000000, 0.000000, 464.000000])
affine3.set(*[0.000000, 0.000000, 5.000000, -11.000000,
 0.000000, 1.000000, 0.000000, 18.000000,
 1.000000, 0.000000, 0.000000, -165.000000])
"""

affines = [affine0, affine1, affine2, affine3] # they will be used merely for adjusting translations manually

# Now edit by hand the affines of CM01, CM02 and CM03 relative to the CM00 (which is used as reference and doesn't change)
frame, panel, buttons_panel = makeTranslationUI(affines, imp, print_button_text="Print coarse transforms")
frame.setTitle("Translate & crop")


# Joint dictionary of parameters
params = {}
params.update(paramsDoG)
params.update(paramsFeatures)
params.update(paramsModel)
params.update(paramsTileConfiguration)

params["calibration"] = [1.0, 1.0, 1.0] # images are now isotropic
params["csv_dir"] = csv_dir
params["modelclass"] = modelclass
params["srcDir"] = srcDir
params["tgtDir"] = tgtDir

makeCropUI(imp, images, tgtDir,
           panel=panel,
           cropContinuationFn=partial(makeRegistrationUI,
                                      original_images, calibration,
                                      affines, params))

