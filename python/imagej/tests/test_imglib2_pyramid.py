from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2.realtransform import RealViews, ScaleAndTranslation
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.util import ImgUtil
from net.imglib2 import FinalInterval
from ij import IJ

img = IL.wrap(IJ.getImage())

pyramid = [img] # level 0 is the image itself

# Create levels of a pyramid with interpolation
width = img.dimension(0)
min_width = 32

s = [0.5 for d in xrange(img.numDimensions())]
t = [-0.25 for d in xrange(img.numDimensions())]
while width > min_width:
  width /= 2
  imgE = Views.interpolate(Views.extendBorder(img), NLinearInterpolatorFactory())
  # A scaled-down view of the imgR
  level = Views.interval(RealViews.transform(imgE, ScaleAndTranslation(s, t)),
                         FinalInterval([int(img.dimension(d) * 0.5)
                                        for d in xrange(img.numDimensions())]))
  # Create a new image for this level
  scaledImg = img.factory().create(level) # of dimensions as of level
  ImgUtil.copy(level, scaledImg) # copy the scaled down view into scaledImg
  pyramid.append(scaledImg)
  # Prepare for next iteration
  img = scaledImg # for the dimensions of the level in the next iteration

for i, imgScaled in enumerate(pyramid):
  IL.wrap(imgScaled, str(i+1)).show()

