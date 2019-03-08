from org.janelia.simview.klb import KLB
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.realtransform import RealViews, AffineTransform3D
import os, sys
from os.path import basename
from bdv.util import BdvFunctions, Bdv
sys.path.append(os.path.dirname(os.path.dirname(sys.argv[0])))
from lib.ui import showAsStack, makeTranslationUI, makeCropUI




srcDir = "/home/albert/shares/zlaticlab/Nadine/Raghav/2017-05-10/GCaMP6s_1_20170510_115003.corrected/SPM00/"
calibration = [1.0, 1.0, 5.0]

klb = KLB.newInstance()

# paths for same timepoint, 4 different cameras
paths = []
timepointDir = srcDir + "TM000000/"
for camera_index, channel_index in zip(xrange(4), [1, 1, 0, 0]):
  paths.append(timepointDir + "SPM00_TM000000_CM0" + str(camera_index) + "_CHN0" + str(channel_index) + ".klb")

for path in paths:
  print basename(path)

img0 = klb.readFull(paths[0])
img1 = klb.readFull(paths[1])
img2 = klb.readFull(paths[2])
img3 = klb.readFull(paths[3])


scale3D = AffineTransform3D()
scale3D.set(calibration[0], 0.0, 0.0, 0.0,
            0.0, calibration[1], 0.0, 0.0,
            0.0, 0.0, calibration[2], 0.0)

def maxCoords(img):
  return [int(img.dimension(d) * calibration[d] -1) for d in xrange(img.numDimensions())]

# Expand camera CM00 to isotropy
imgE = Views.extendZero(img0)
imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
imgT = RealViews.transform(imgI, scale3D)
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


images = [imgB0, imgB1, imgB2, imgB3]
imp = showAsStack(images, title="4 views to coarsely register")

# Now edit by hand the affines of CM01, CM02 and CM03 relative to the CM00 (which is used as reference and doesn't change)

frame, panel, buttons_panel = makeTranslationUI([affine1, affine2, affine3], imp, print_button_text="Print coarse transforms")
frame.setTitle("Translate, crop & register")
makeCropUI(imp, images, panel=panel)

