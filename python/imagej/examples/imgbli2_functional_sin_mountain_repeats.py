# Albert Cardona 2018-09-14
# This source code is in the public domain.
#
# Open the Script Editor in the Fiji image processing software and run it
# to generate the image with repeating mountains and valleys,
# courtesy of the trigonometric sin function.

from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.array import ArrayImg
from net.imglib2.img.basictypeaccess import ByteAccess
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.view import Views
from math import sin, pi

# An image generated from a sinusoidal function
class Sinusoid(ByteAccess):
  def __init__(self, diameter):
    self.diameter = float(diameter)
  def getValue(self, index):
    # Obtain 2D coordinates and map into the span range, normalized into the [0, 1] range
    # (which will be used as the linearized 2*pi length of the circumference)
    x = (index % self.diameter) / self.diameter
    y = (index / self.diameter) / self.diameter
    # Start at 2, with each sin or cos adding from -1 to +1 each, then normalize and expand into 8-bit range
    # (subtract -0.25 to center the white peak)
    return int((2 + sin((x - 0.25) * 2 * pi) + sin((y - 0.25) * 2 * pi)) / 4.0 * 255)
  def setValue(self, index, value):
    pass

# Define the dimensions of the repeat
dimensions = [64, 64]
data = Sinusoid(dimensions[0])

# Construct an 8-bit image
t = UnsignedByteType()
img = ArrayImg(data, dimensions, t.getEntitiesPerPixel())
img.setLinkedType(t.getNativeTypeFactory().createLinkedType(img))

# Define the number of repeats
n_copies = 12
imgMirrored = Views.extendMirrorSingle(img)
imgMosaic = Views.interval(imgMirrored, [0, 0], [d * n_copies -n_copies for d in dimensions]) # subtracts n_copies to correct for mirror single

IL.wrap(imgMosaic, "sinusoid").show()