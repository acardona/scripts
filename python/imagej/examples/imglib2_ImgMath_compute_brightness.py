from net.imglib2.converter import Converters
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.array import ArrayImgFactory
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.algorithm.math.ImgMath import compute, maximum, minimum, div, let, var, IF, THEN, ELSE, EQ, sub
from ij import IJ

# Load an RGB or ARGB image
#imp = IJ.openImage("https://imagej.nih.gov/ij/images/leaf.jpg") 
imp = IJ.getImage()

# Access its pixel data from an ImgLib2 data structure:
# a RandomAccessibleInterval<ARGBType>
img = IL.wrapRGBA(imp)

# Read out single channels
red = Converters.argbChannel(img, 1)
green = Converters.argbChannel(img, 2)
blue = Converters.argbChannel(img, 3)

# Create an empty image of type FloatType (floating-point values)
# Here, the img is used to read out the interval: the dimensions for the new image
brightness = ArrayImgFactory(FloatType()).create(img)

# Compute the brightness: pick the maximum intensity pixel of every channel
# and then normalize it by dividing by the number of channels
compute(div(max([red, green, blue]), 255.0)).into(brightness)

# Show the brightness image
impB = IL.wrap(brightness, imp.getTitle() + " brightness")
impB.show()

# Compute now the image color saturation
saturation = ArrayImgFactory(FloatType()).create(img)
compute( let("red", red,
             "green", green,
             "blue", blue,
             "max", maximum([var("red"), var("green"), var("blue")]),
             "min", minimum([var("red"), var("green"), var("blue")]),
                     IF ( EQ( 0, var("max") ),
                       THEN( 0 ),
                       ELSE( div( sub(var("max"), var("min")),
                                  var("max") ) ) ) ) ).into(saturation)

impC = IL.wrap(saturation, imp.getTitle() + " saturation")
impC.show()