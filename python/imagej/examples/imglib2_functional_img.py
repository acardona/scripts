from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.array import ArrayImg
from net.imglib2.img.basictypeaccess import ByteAccess
from net.imglib2.type.numeric.integer import UnsignedByteType
from math import sin, cos, pi


# Example 1: a virtual blank image. No pixel array backing.
t = UnsignedByteType()
img = ArrayImg(type('ConstantValue', (ByteAccess,), {'getValue': lambda self, index: 255})(), [512, 512], t.getEntitiesPerPixel())
img.setLinkedType(t.getNativeTypeFactory().createLinkedType(img))

#IL.wrap(img, "white").show()

# Example 1b: a virtual blank image, with the ByteAccess unpacked into a class
class ConstantValue(ByteAccess):
  def __init__(self, value):
    self.value = value
  def getValue(self, index):
    return self.value
  def setValue(self, index, value):
    pass

t = UnsignedByteType()
data = ConstantValue(255)
dimensions = [512, 512]

img = ArrayImg(data, dimensions, t.getEntitiesPerPixel())
img.setLinkedType(t.getNativeTypeFactory().createLinkedType(img))

#IL.wrap(img, "white").show()

# Example 2: an image generated from a sinusoidal function
class Sinusoid(ByteAccess):
  def __init__(self, width, span):
    self.width = width
    self.span = span
  def getValue(self, index):
    # Obtain 2D coordinates and map into the span range, normalized into the [0, 1] range
    # (which will be used as the linearized 2*pi length of the circumference)
    x = ((index % self.width) % self.span) / self.span
    y = ((index / self.width) % self.span) / self.span
    # Start at 2, with each sin or cos adding from -1 to +1 each, then normalize and expand into 8-bit range
    return int((2 + sin(x  * 2 * pi) + cos(y * 2 * pi)) / 4.0 * 255)
  def setValue(self, index, value):
    pass

t = UnsignedByteType()
dimensions = [512, 512]
data = Sinusoid(dimensions[0], dimensions[0] / 10.0)

img = ArrayImg(data, dimensions, t.getEntitiesPerPixel())
img.setLinkedType(t.getNativeTypeFactory().createLinkedType(img))

IL.wrap(img, "sinusoid").show()