from java.io import RandomAccessFile
from net.imglib2.img.array import ArrayImgs
from jarray import zeros
from java.nio import ByteBuffer
import operator
from net.imglib2 import RandomAccessibleInterval
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.cache import CacheLoader
from net.imglib2.realtransform import RealViews
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from ij.io import FileSaver
from ij import ImagePlus, IJ
from synchronize import make_synchronized
from util import syncPrint
try:
  # Needs 'SiMView' Fiji update site enabled
  from org.janelia.simview.klb import KLB
except:
  print "*** KLB library is NOT installed ***"

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


class KLBLoader(CacheLoader):
  def __init__(self):
    self.klb = KLB.newInstance()

  def load(self, path):
    return self.get(path)

  def get(self, path):
    return self.klb.readFull(path)


class TransformedLoader(CacheLoader):
  def __init__(self, loader, transformsDict, roi=None):
    self.loader = loader
    self.transformsDict = transformsDict
    self.roi = roi
  def load(self, path):
    return self.get(path)
  def get(self, path):
    transform = self.transformsDict[path]
    img = self.loader.get(path)
    imgE = Views.extendZero(img)
    imgI = Views.interpolate(imgE, NLinearInterpolatorFactory())
    imgT = RealViews.transform(imgI, transform)
    minC = self.roi[0] if self.roi else [0] * img.numDimensions()
    maxC = self.roi[1] if self.roi else [img.dimension(d) -1 for d in xrange(img.numDimensions())]
    return Views.zeroMin(Views.interval(imgT, minC, maxC))


class ImageJLoader(CacheLoader):
  def get(self, path):
    return IL.wrap(IJ.openImage(path))
  def load(self, path):
    return self.get(path)
