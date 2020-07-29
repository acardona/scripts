from ij import IJ
from net.imglib2.algorithm.math.ImgMath import compute, maximum, minimum, log, exp, div, mul
from net.imglib2.algorithm.math import Print
from net.imglib2.converter import Converters, ColorChannelOrder
from net.imglib2.img.array import ArrayImgs
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views

# Fetch an RGB image stack
imp_rgb = IJ.getImage() # IJ.openImage("http://imagej.nih.gov/ij/images/flybrain.zip")

img = IL.wrap(imp_rgb) # an ARGBType Img
# Color channel views
red, green, blue = (Converters.argbChannel(img, c) for c in [1, 2, 3])

# ImgLib1 scripting gamma function
# return Min(255, Max(0, Multiply(Exp(Multiply(gamma, Log(Divide(channel, 255)))), 255)))  

gamma = 0.5

def op(channel):
  return minimum(255, maximum(0, mul(exp(mul(gamma, log(div(channel, 255)))), 255)))

img_gamma = Converters.mergeARGB(Views.stack(op(red).viewDouble(),
                                             op(green).viewDouble(),
                                             op(blue).viewDouble()),
                                 ColorChannelOrder.RGB)

IL.wrap(img_gamma, "gamma 0.5").show()
                                