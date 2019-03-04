from ij import IJ
from net.imglib2.view import Views
from net.imglib2.realtransform import AffineTransform3D, RealViews
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.img.array import ArrayImgs
from jarray import zeros
from math import sqrt
import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP")
from lib.ui import showAsStack, makeTranslationUI
from lib.util import affine3D


# Create a [100,100,100] image with a sphere of radius 20 at the center
aimg = ArrayImgs.unsignedBytes([10, 10, 10])
c = aimg.cursor()
pos = zeros(3, 'l')
while c.hasNext():
  t = c.next()
  c.localize(pos)
  v = sqrt(sum(pow(p - 5, 2) for p in pos))
  if v < 2:
    t.setReal(255)

# Use the image to represent a channel
# Transform each channel independently
def identity():
  return affine3D([1, 0, 0, 0,
                   0, 1, 0, 0,
                   0, 0, 1, 0])

aff1 = identity()
aff2 = identity()
aff3 = identity()

def viewTransformed(img, affine):
  imgE = Views.extendZero(img)
  imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
  imgT = RealViews.transform(imgI, affine)
  minC = [0, 0, 0]
  maxC = [img.dimension(d) -1 for d in xrange(img.numDimensions())]
  imgB = Views.interval(imgT, minC, maxC)
  return imgB

imp = showAsStack([viewTransformed(aimg, aff) for aff in [aff1, aff2, aff3]], title="test")

frame, panel, buttons_panel = makeTranslationUI([aff1, aff2, aff3], imp, show=True)
