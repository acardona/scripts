from java.io import RandomAccessFile
from net.imglib2.img.array import ArrayImgs
from jarray import zeros
from java.nio import ByteBuffer
import operator
from net.imglib2 import RandomAccessibleInterval
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from ij.io import FileSaver
from ij import ImagePlus
from synchronize import make_synchronized
try:
  # Neends 'SiMView' Fiji update site enabled
  from org.janelia.simview.klb import KLB
except:
  pass

def readFloats(path, dimensions, header=0):
  """ Read a file as an ArrayImg of FloatType """
  size = reduce(operator.mul, dimensions)
  ra = RandomAccessFile(path, 'r')
  try:
    ra.skipBytes(header)
    bytes = zeros(size * 4, 'b')
    ra.read(bytes)
    floats = zeros(size, 'f')
    ByteBuffer.wrap(bytes).asFloatBuffer().get(floats)
    return ArrayImgs.floats(floats, dimensions)
  finally:
    ra.close()


def readUnsignedBytes(path, dimensions, header=0):
  """ Read a file as an ArrayImg of UnsignedShortType """
  ra = RandomAccessFile(path, 'r')
  try:
    ra.skipBytes(header)
    bytes = zeros(reduce(operator.mul, dimensions), 'b')
    ra.read(bytes)
    return ArrayImgs.unsignedBytes(bytes, dimensions)
  finally:
    ra.close()


__klb__ = None

@make_synchronized
def __initKLB__():
  if not __klb__:
    __klb__ = KLB.newInstance()

def readKLB(path):
  __init__KLB__()
  return __klb__.readFull(path)


def writeZip(img, path, title=""):
  if isinstance(img, RandomAccessibleInterval):
    imp = IL.wrap(Views.iterable(img), title)
  elif isinstance(img, ImagePlus):
    imp = img
    if title:
      imp.setTitle(title)
  #
  FileSaver(imp).saveAsZip(path)
  return imp

