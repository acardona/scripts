from net.imglib2 import Cursor, RealLocalizable, RealRandomAccess, RealPoint
from net.imglib2.img import Img
from net.imglib2.img.array import ArrayImgs
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.type.numeric.integer import UnsignedByteType
from fiji.scripting import Weaver
from jarray import array, zeros
from java.lang import Float
from ij import VirtualStack, ImagePlus
from ij.process import ByteProcessor

M = Weaver.method("""
    public final int mandelbrot(final double re0, final double im0, final int maxIterations) {
        double re = re0;
        double im = im0;
        int i = 0;
        for ( ; i < maxIterations; ++i )
        {
            final double squre = re * re;
            final double squim = im * im;
            if ( squre + squim > 4 )
                break;
            im = 2 * re * im + im0;
            re = squre - squim + re0;
        }
        return i;
    }

    public final void into(final RealRandomAccess rra, final Cursor cursor, final double scale, final double[] offset) {
        while (cursor.hasNext()) {
            UnsignedByteType t = (UnsignedByteType) cursor.next();
            for ( int d = 0; d < 2; ++d ) {
                rra.setPosition( scale * cursor.getIntPosition( d ) + offset[ d ], d );
            }
            t.set( (UnsignedByteType) rra.get() );
        }
    }
""", [RealPoint, RealRandomAccess, Cursor, UnsignedByteType])


class MandelbrotRealRandomAccess(RealRandomAccess):
    def __init__(self):
      self.t = UnsignedByteType()
      self.pos = zeros(2, 'd')
    def get(self):
      self.t.set( M.mandelbrot( self.pos[0], self.pos[1], 255 ) )
      return self.t
    def copyRealRandomAccess(self):
      return self.copy()
    def copy(self):
      a = MandelbrotRealRandomAccess()
      a.pos[0] = self.pos[0]
      a.pos[1] = self.pos[1]
      return a
    def localize(self, position):
      position[0] = self.pos[0]
      position[1] = self.pos[1]
    def getFloatPosition(self, d):
      return Float(self.pos[d])
    def getDoublePosition(self, d):
      return self.pos[d]
    def move(self, distance, d):
      pass # many overlapping homonimous methods
    def setPosition(self, position):
      # ignore RealLozalizable instances of "position"
      self.pos[0] = position[0]
      self.pos[1] = position[1]
    def setPosition(self, position, d):
      self.pos[d] = position

def draw(dimensions, scale, offset):
  img = ArrayImgs.unsignedBytes(dimensions)
  M.into( MandelbrotRealRandomAccess(), img.cursor(), scale, offset )
  return img


dimensions = array([600, 400], 'l')
scale = 0.005
offset = array([-2, -1], 'd')

#img = draw(dimensions, scale, offset)
#IL.show(img, "Mandelbrot")

# NOT Thread-safe
class MStack(VirtualStack):
  def __init__(self, width, height, n, scale, offset):
    super(VirtualStack, self).__init__(width, height, n)
    self.scale = scale
    self.offset = offset
    self.img = ArrayImgs.unsignedBytes([width, height])
    self.bytes = self.img.update(None).getCurrentStorageArray()
  def getPixels(self, n):
    k = pow(2, n-1)
    scale = self.scale / k
    """
    sclae = self.scale * k
    xd = - (self.width / 2.0) * (k - 1) * self.scale
    yd = - (self.height / 2.0) * (k - 1) * self.scale
    """
    print scale, xd, yd
    offset = [self.offset[0] + xd, self.offset[1] + yd]
    M.into( MandelbrotRealRandomAccess(), self.img.cursor(), scale, offset )
    return self.bytes
  def getProcessor(self, n):
    return ByteProcessor(self.width, self.height, self.getPixels(n), None)
    
imp = ImagePlus("Mandelbrot", MStack(dimensions[0], dimensions[1], 100, scale, offset))
imp.show()
