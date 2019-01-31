from net.imglib2.algorithm.math.ImgMath import add, sub
from net.imglib2.img.array import ArrayImgs
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.util import Intervals
from jarray import zeros, array
from net.imglib2.type.numeric.real import FloatType

def test(iraf):
  
  # Test dimensions: should be the same as the one input image
  print "Dimensions:", Intervals.dimensionsAsLongArray(iraf)

  # Test Cursor
  c = iraf.cursor()
  pos = zeros(2, 'l')
  while c.hasNext():
    c.fwd()
    c.localize(pos)
    print "Cursor:", pos, "::", c.get()

  # Test RandomAccess
  ra = iraf.randomAccess()
  c = iraf.cursor()
  while c.hasNext():
    c.fwd()
    ra.setPosition(c)
    c.localize(pos)
    print "RandomAccess:", pos, "::", ra.get()

  # Test source img: should be untouched
  c = img.cursor()
  while c.hasNext():
    print "source:", c.next()

  # Test interval view: the middle 2x2 square
  v = Views.interval(iraf, [1, 1], [2, 2])
  IL.wrap(v, "+2 view").show()


# An array from 0 to 15
a = [ 0,  1,  2,  3,
      4,  5,  6,  7,
      8,  9, 10, 11,
     12, 13, 14, 15]
pixels = array(a, 'b')
img = ArrayImgs.unsignedBytes(pixels, [4, 4])

test(add(img, 2).view())
test(add(img, 2).view(FloatType()))
