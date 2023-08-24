# 2022 I2K example
# Create an ImgLib2 ArrayImg

# 1. With ArrayImgs: trivial
from net.imglib2.img.array import ArrayImgs

img = ArrayImgs.unsignedShorts([512, 512])

# 2. With ArrayImgFactory: unnecessary, use ArrayImgs
from net.imglib2.img.array import ArrayImgFactory
from net.imglib2.type.numeric.integer import UnsignedShortType

factoryU16 = ArrayImgFactory(UnsignedShortType())
img = factoryU16.create([512, 512])

# 3. With ArrayImg: low-level, shows how the enchilada is made 
from jarray import zeros
import operator
from net.imglib2.img.basictypeaccess.array import ShortArray
from net.imglib2.img.basictypeaccess import ArrayDataAccessFactory
from net.imglib2.img.array import ArrayImgs, ArrayImg


# Dimensions
dimensions = [512, 512]
n_pixels = reduce(operator.mul, dimensions)
# Pixel type
t = UnsignedShortType()
# How many pixels per unit of storage in the native array
entitiesPerPixel = t.getEntitiesPerPixel() # a net.imglib2.util.Fraction instance
# A native short[] array
pixelsU16 = zeros(n_pixels, 'h') # 'h' means short
# Or create array of the correct type in a generic way:
#pixelsU16 = ArrayDataAccessFactory.get(t.getNativeTypeFactory()).createArray(n_pixels)
# DataAccess wrapper for the native short[] array
accessU16 = ShortArray(pixelsU16)
# ArrayImg with a linked type for efficient iteration of its underlying array
img = ArrayImg(accessU16, dimensions, entitiesPerPixel)
img.setLinkedType(t.getNativeTypeFactory().createLinkedType(img))



# 4. Functional image: data generated as a function of its pixel coordinates
from net.imglib2.img.basictypeaccess import FloatAccess
from math import sin, cos, pi
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.array import ArrayImg
from net.imglib2.type.numeric.real import FloatType


class SinDataAccess(FloatAccess):
  """ A DataAccess for float values generated on demand as a function of pixel coordinates. """
  def __init__(self, width, offset, wavelength):
    self.width = width # in pixels
    self.offset = offset # in radians
    self.wavelength = wavelength # in pixels
    
  def getValue(self, index):
    # Compute x,y coordinates of the pixel at index
    x = index % self.width
    y = index / self.width
    # Compute the pixel intensity value as that of a two-dimensional sine wave
    val = sin(x * 2 * pi / self.wavelength + self.offset)\
        + sin(y * 2 * pi / self.wavelength + self.offset)
    # Expand floating-point value in the [0, 1] range to the 16-bit range 
    return min(int(val * 65535/2), 65535)
    
  def putValue(self, index, value):
    pass # ignore

sinaccess = SinDataAccess(dimensions[0], -pi/2, dimensions[0]/4)
t = FloatType()
img = ArrayImg(sinaccess, dimensions, t.getEntitiesPerPixel())
img.setLinkedType(t.getNativeTypeFactory().createLinkedType(img))

IL.show(img)



# 5. Functional image but without faking an ArrayImg
from net.imglib2.img import AbstractImg
from net.imglib2 import Cursor, RandomAccess, Point
from net.imglib2.type.numeric.real import FloatType
from math import sin, pi
from java.lang import System

class FnCursor(Point, Cursor, RandomAccess):
  def __init__(self, n, wavelength, offset):
    super(Point, self).__init__(n)
    self.offset = offset # in radians
    self.wavelength = wavelength
    self.t = FloatType()
  def copyRandomAccess(self):
    return FnCursor(self.numDimensions(), self.wavelength, self.offset)
  def copyCursor(self):
    return self.copyRandomAccess()
  def get(self):
    x = self.getLongPosition(0)
    y = self.getLongPosition(1)
    val = sin(x * 2 * pi / self.wavelength + self.offset)\
        + sin(y * 2 * pi / self.wavelength + self.offset)
    self.t.set(val)
    if 0 == x % 64 and 0 == y % 64:
      System.out.println("x, y: " + str(x) + ", " + str(y) + " :: " + str(val))
    return t

class FnImg(AbstractImg):
  def __init__(self, dimensions):
    super(AbstractImg, self).__init__(dimensions)
  def factory(self):
    return None
  def copy(self):
    return self # stateless, so safe
  def randomAccess(self, interval=None): # optional argument handles case of having randomAccess() and randomAccess(interval).
    return self.cursor()
  def cursor(self):
    return FnCursor(self.numDimensions(), -pi/2, self.dimension(0)/4)
  def localizingCursor(self):
    return self.cursor()
    
img = FnImg([512, 512])
IL.show(img) # shows black, yet above the get() prints values
aimg = ArrayImgs.floats([512, 512])
c1 = img.cursor()
c2 = aimg.cursor()
while c2.hasNext():
  t = c2.next()
  c1.setPosition(c2)
  c2.next().set(c1.get())
IL.show(aimg)  # Shows black, yet above the get() prints values
