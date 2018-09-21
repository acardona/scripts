from net.imglib2.converter import Converters
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.array import ArrayImgFactory
from net.imglib2.type.numeric.real import FloatType
from itertools import izip
from ij import IJ

# # Load an RGB or ARGB image
imp = IJ.getImage()

# Access its pixel data from an ImgLib2 data structure:
# a RandomAccessibleInterval<ARGBType>
img = IL.wrapRGBA(imp)

# Convert an ARGB image to a stack of 4 channels: a RandomAccessibleInterval<UnsignedByte>
# with one more dimension that before.
# The order of channels in the stack can be changed by changing their indices.
channels = Converters.argbChannels(img, [0, 1, 2, 3])

impChannels = IL.wrap(channels, imp.getTitle() + " channels")
impChannels.show()

# Read out a single channel directly
red = Converters.argbChannel(img, 1)

# Pick a view of the red channel in the channels stack.
# Takes the last dimension, which are the channels,
# and fixes it, pointing to the index of the red channel (1) in the stack.
red = Views.hyperSlice(channels, channels.numDimensions() -1, 1)

impRed = IL.wrap(red, imp.getTitle() + " - red channel")
impRed.show()

# Create an empty image of type FloatType (floating-point values)
# Here, the img is used to read out the interval: the dimensions for the new image
brightness = ArrayImgFactory(FloatType()).create(img)


def iterableChannel(imgARGB, i):
  return Views.iterable(Converters.argbChannel(imgARGB, i))

zipped_channels = izip(iterableChannel(img, 1), # red
                       iterableChannel(img, 2), # green
                       iterableChannel(img, 3), # blue
                       brightness)

#for r, g, b, s in izip(iterableChannel(img, 1), # red
#                       iterableChannel(img, 2), # green
#                       iterableChannel(img, 3), # blue
#                       brightness):
#  s.setReal(max(r.getInteger(), g.getInteger(), b.getInteger()) / 255.0)

def computeBrightness(e):
  e[3].setReal(max(e[0].getInteger(), e[1].getInteger(), e[2].getInteger()) / 255.0)

filter(computeBrightness, zipped_channels)



impLum = IL.wrap(brightness, imp.getTitle() + " brightness")
impLum.show()