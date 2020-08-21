from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2.realtransform import RealViews
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.realtransform import Scale
from net.imglib2 import FinalInterval
from ij import IJ

img = IL.wrap(IJ.getImage())

imgR = Views.interpolate(Views.extendBorder(img), NLinearInterpolatorFactory())  

# Create levels of a pyramid as interpolated views
width = img.dimension(0)
min_width = 32
pyramid = [] # level 0 is the image itself, not added
scale = 1.0
while width > min_width:
  scale /= 2.0
  width /= 2
  s = [scale for d in xrange(img.numDimensions())]
  scaled = Views.interval(RealViews.transform(imgR, Scale(s)),
                          FinalInterval([int(img.dimension(d) * scale)
                                         for d in xrange(img.numDimensions())]))
  pyramid.append(scaled)

for i, imgScaled in enumerate(pyramid):
  IL.wrap(imgScaled, str(i+1)).show()

