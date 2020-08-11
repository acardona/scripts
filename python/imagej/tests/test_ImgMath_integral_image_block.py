from net.imglib2.algorithm.math.ImgMath import compute, block, div
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.algorithm.integral import IntegralImg
from net.imglib2.type.numeric.integer import UnsignedLongType
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.view import Views
from net.imglib2.algorithm.math.abstractions import Util
from ij import IJ

imp = IJ.getImage() # an 8-bit image, e.g. blobs sample image
img = IL.wrap(imp)

# A converter from 8-bit (unsigned byte) to 64-bit (unsigned long)
int_converter = Util.genericIntegerTypeConverter()
# Create the integral image of an 8-bit input, stored as 64-bit
alg = IntegralImg(img, UnsignedLongType(), int_converter)
alg.process()
integralImg = alg.getResult()

# Read out blocks of radius 5 (i.e. 10x10 for a 2d image)
# in a way that is entirely n-dimensional (applies to 1d, 2d, 3d, 4d ...)
radius = 5
nd = img.numDimensions()
op = div(block(Views.extendBorder(integralImg), [radius] * nd),
         pow(radius*2, nd))
blurred = img.factory().create(img) # an 8-bit image
# Compute in floats, store result into longs
# using a default generic RealType converter via t.setReal(t.getRealDouble())
compute(op).into(blurred, None, FloatType(), None)

# Show the blurred image with the same LUT as the original
imp2 = IL.wrap(blurred, "integral image radius 5 blur")
imp2.getProcessor().setLut(imp.getProcessor().getLut())
imp2.show()



# Compare with Gaussian blur
from ij import ImagePlus
from ij.plugin.filter import GaussianBlur
from ij.gui import Line, ProfilePlot

# Gaussian of the original image
imp_gauss = ImagePlus(imp.getTitle() + " Gauss", imp.getProcessor().duplicate())
GaussianBlur().blurGaussian(imp_gauss.getProcessor(), radius)
imp_gauss.show()

# Plot values from a diagonal from bottom left to top right
line = Line(imp.getWidth() -1, 0, 0, imp.getHeight() -1)
imp_gauss.setRoi(line)
pp1 = ProfilePlot(imp_gauss)
plot = pp1.getPlot()
imp2.setRoi(line)
pp2 = ProfilePlot(imp2)
profile2 = pp2.getProfile() # double[]
plot.setColor("red")
plot.add("line", range(len(profile2)), profile2)
plot.show()



