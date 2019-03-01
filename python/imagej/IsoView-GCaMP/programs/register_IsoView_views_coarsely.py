from org.janelia.simview.klb import KLB
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.realtransform import RealViews, AffineTransform3D
import os, sys
from os.path import basename
from bdv.util import BdvFunctions, Bdv
sys.path.append(os.path.dirname(os.path.dirname(sys.argv[0]))
from lib.util import newFixedThreadPool, Task, cropView
from lib.ui import showAsStack, showInBDV
from org.janelia.simview.klb import KLB
from net.imglib2.algorithm.math import ImgMath
from net.imglib2.img.array import ArrayImgs



srcDir = "/home/albert/shares/zlaticlab/Nadine/Raghav/2017-05-10/GCaMP6s_1_20170510_115003.corrected/SPM00/"
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

# Calibration: [1.0, 1.0, 5.0]
scale3D = AffineTransform3D()
scale3D.set(1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 5.0, 0.0)

# Expand camera CM00 to isotropy
imgE = Views.extendZero(img0)
imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
imgT = RealViews.transform(imgI, scale3D)
imgB0 = Views.interval(imgT, [0, 0, 0], [img0.dimension(0) -1, img0.dimension(1) -1, img0.dimension(2) * 5 - 1])


# Transform camera CM01 to CM00: 180 degrees on Y axis, plus a translation
dx = -195
dy = 54
dz = 8
affine = AffineTransform3D()
affine.set(-1.0, 0.0, 0.0, img1.dimension(0) + dx,
            0.0, 1.0, 0.0, 0.0 + dy,
            0.0, 0.0, 1.0, 0.0 + dz)
affine.concatenate(scale3D)
imgE = Views.extendZero(img1)
imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
imgT = RealViews.transform(imgI, affine)
imgB1 = Views.interval(imgT, [0, 0, 0], [img1.dimension(0) -1, img1.dimension(1) -1, img1.dimension(2) * 5 - 1])
#imp = IL.wrap(imgB1, "img1 rotated 180")
#imp.setDisplayRange(74, 542)
#imp.setSlice(175)
#imp.show()


# Transform camera CM02 to CM00: 90 degrees on Y axis, plus a translation
# (Z is 85: 20 more than img0 and img1. So view interval that is 100 shorter in Z)
dx = 0.0
dy = 25.0
dz = 41.0
affine = AffineTransform3D()
affine.set( 0.0, 0.0, 1.0, 0.0 + dx,
            0.0, 1.0, 0.0, 0.0 + dy,
            -1.0, 0.0, 0.0, img2.dimension(2) * 5 + dz)
affine.concatenate(scale3D)
imgE = Views.extendZero(img2)
imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
imgT = RealViews.transform(imgI, affine)
imgB2 = Views.interval(imgT, [0, 0, 0], [img2.dimension(0) -1, img2.dimension(1) -1, img2.dimension(2) * 5 - 1]) # removed the -100
#imp = IL.wrap(imgB2, "img2 rotated 90")
#imp.setDisplayRange(74, 542)
#imp.setSlice(175)
#imp.show()

# Transform camera CM03 to CM00: -90 degrees on Y axis, plus a translation
dx = 0
dy = 25
dz = -159
affine = AffineTransform3D()
affine.set( 0.0, 0.0, 1.0, 0.0 + dx,
            0.0, 1.0, 0.0, 0.0 + dy,
            1.0, 0.0, 0.0, 0.0 + dz)
affine.concatenate(scale3D)
imgE = Views.extendZero(img3)
imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
imgT = RealViews.transform(imgI, affine)
imgB3 = Views.interval(imgT, [0, 0, 0], [img3.dimension(0) -1, img3.dimension(1) -1, img3.dimension(2) * 5 - 1])
#imp = IL.wrap(Views.zeroMin(imgB3), "img3 rotated -90")
#imp.setDisplayRange(74, 542)
#imp.setSlice(175)
#imp.show()


# The field of view is too large, too much black space: crop to a ROI
minCoords = [1, 228, 0]
maxCoords = [1 + 406 -1, 228 + 465 -1, 325 -1]

# Set cropped view for them all
imgB0, imgB1, imgB2, imgB3 = (cropView(img, minCoords, maxCoords) for img in (imgB0, imgB1, imgB2, imgB3))


exe = newFixedThreadPool(4)
try:
  # Copy into ArrayImg
  def copyIntoArrayImg(img):
    return ImgMath.compute(ImgMath.img(img)).into(ArrayImgs.floats([img.dimension(d) for d in xrange(img.numDimensions())]))
  futures = [exe.submit(Task(copyIntoArrayImg, img)) for img in [imgB0, imgB1, imgB2, imgB3]]
  imgB0, imgB1, imgB2, imgB3 = [f.get() for f in futures]
finally:
  exe.shutdown()

showAsStack([imgB0, imgB1, imgB2, imgB3], title="4 views coarsely registered")
#showInBDV([imgB0, imgB1, imgB2, imgB3], title="4 views coarsely registered")
