from net.imglib2.algorithm.math.ImgMath import compute, maximum
from net.imglib2.converter import Converters
from net.imglib2.img.array import ArrayImgs
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views

from ij import IJ, ImagePlus

# Fetch an RGB image stack
imp_rgb = IJ.getImage() # IJ.openImage("http://imagej.nih.gov/ij/images/flybrain.zip")

img = IL.wrap(imp_rgb) # an ARGBType Img
red   = Converters.argbChannel(img, 1) # a view of the ARGB red channel

# Project the last dimension using the max function
last_d = red.numDimensions() -1
op = maximum([Views.hyperSlice(red, last_d, i) for i in xrange(red.dimension(last_d))])

#img_max_red = compute(op).into(ArrayImgs.unsignedBytes([red.dimension(0), red.dimension(1)]))
img_max_red = compute(op).intoArrayImg()

IL.wrap(img_max_red, "maximum projection of the red channel)").show()