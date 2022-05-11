# 2022 I2K example: illustrate how to convert images from e.g., 8-bit byte integer to 32-bit float
# Albert Cardona 2022
# Create an ImgLib2 ArrayImg

from ij import IJ
from net.imglib2.img.array import ArrayImgs
from ij.process import ShortProcessor
from ij.process import ByteProcessor
from ij.process import FloatProcessor
from net.imglib2.util import ImgUtil
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.converter import Converters
from net.imglib2.converter import RealFloatConverter
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.view import Views


imp = IJ.getImage()
dimensions = [imp.getWidth(), imp.getHeight()]
ip = imp.getProcessor()
pixels = ip.getPixels()

# In practice, you never want to do this below,
# and instead you'd use the built-in wrapper: ImageJFunctions.wrap(imp)
# This is merely for illustration of how to use ArrayImgs with an existing pixel array
if isinstance(ip, ByteProcessor):
  img1 = ArrayImgs.unsignedBytes(pixels, dimensions)
elif isinstance(ip, ShortProcessor):
  img1 = ArrayImgs.unsignedShorts(pixels, dimensions)
elif isinstance(ip, FloatProcessor):
  img1 = ArrayImgs.floats(pixels, dimensions)
else:
  print "Can't handle image of type:", type(ip).getClassname()


# An empty image of float[]
img2 = ArrayImgs.floats(dimensions)

# View it as RandomAccessibleInterval<FloatType> by converting on the fly
# using a generic RealType to FloatType converter
floatView = Converters.convertRAI(img1, RealFloatConverter(), FloatType())

# The above 'floatView' can be used as an image: one that gets always converted on demand.
# If you only have to iterate over the pixels just once, there's no need to create a new image.
IL.show(floatView, "32-bit view of the 8-bit")

# Copy one into the other: both are of the same type
ImgUtil.copy(floatView, img2)

IL.show(img2, "32-bit copy")
