from net.imglib2.algorithm.math.ImgMath import compute, block, div, offset, add
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.array import ArrayImgs
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.view import Views
from net.imglib2.util import Intervals
from ij import IJ

imp = IJ.getImage() # an 8-bit image
img = IL.wrap(imp)

# Create the integral image of an 8-bit input, stored as 64-bit
target = ArrayImgs.unsignedLongs(Intervals.dimensionsAsLongArray(img))
# Copy input onto the target image
compute(img).into(target)
# Extend target with zeros, so that we can read at coordinate -1
imgE = Views.extendZero(target)
# Integrate every dimension, cummulatively by writing into
# a target image that is also the input
for d in xrange(img.numDimensions()):
  coord = [0] * img.numDimensions() # array of zeros
  coord[d] = -1
  # Cummulative sum along the current dimension
  # Note that instead of the ImgMath offset op,
  # we could have used Views.translate(Views.extendZero(target), [1, 0]))
  # (Notice though the sign change in the translation)
  integral = add(target, offset(imgE, coord))
  compute(integral).into(target)

# The target is the integral image
integralImg = target

# Read out blocks of radius 5 (i.e. 10x10 for a 2d image)
# in a way that is entirely n-dimensional (applies to 1d, 2d, 3d, 4d ...)
radius = 5
nd = img.numDimensions()
op = div(block(Views.extendBorder(integralImg), [radius] * nd),
         pow(radius*2, nd)) # divide by total number of pixels in the block

blurred = ArrayImgs.floats(Intervals.dimensionsAsLongArray(img))
compute(op).into(blurred, FloatType())

# Show the blurred image with the same LUT as the original
imp2 = IL.wrap(blurred, "integral image radius 5 blur")
imp2.getProcessor().setLut(imp.getProcessor().getLut())
imp2.show()
