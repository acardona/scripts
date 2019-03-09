from java.io import RandomAccessFile
from net.imglib2.img.array import ArrayImgs
from jarray import zeros
from java.nio import ByteBuffer
import operator
from net.imglib2 import RandomAccessibleInterval, IterableInterval
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img import ImgView
from net.imglib2.cache import CacheLoader
from net.imglib2.realtransform import RealViews
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from ij.io import FileSaver
from ij import ImagePlus, IJ
from synchronize import make_synchronized
from util import syncPrint, newFixedThreadPool
from ui import showStack, showBDV
try:
  # Needs 'SiMView' Fiji update site enabled
  from org.janelia.simview.klb import KLB
except:
  print "*** KLB library is NOT installed ***"
try:
  from org.janelia.saalfeldlab.n5.imglib2 import N5Utils
  from org.janelia.saalfeldlab.n5 import N5FSReader, N5FSWriter, GzipCompression
except:
  print "*** n5-imglib2 from github.com/saalfeldlab/n5-imglib2 not installed. ***"
from com.google.gson import GsonBuilder


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


__klb__ = KLB.newInstance()

def readKLB(path):
  return __klb__.readFull(path)


def writeZip(img, path, title=""):
  if isinstance(img, RandomAccessibleInterval):
    imp = IL.wrap(img, title)
  elif isinstance(img, ImagePlus):
    imp = img
    if title:
      imp.setTitle(title)
  else:
    syncPrint("Cannot writeZip to %s:\n  Unsupported image type %s" % (path, str(type(img))))
    return None
  #
  FileSaver(imp).saveAsZip(path)
  return imp


def readIJ(path):
  return IJ.openImage(path)


class KLBLoader(CacheLoader):
  def __init__(self):
    self.klb = KLB.newInstance()

  def load(self, path):
    return self.get(path)

  def get(self, path):
    return self.klb.readFull(path)


class TransformedLoader(CacheLoader):
  def __init__(self, loader, transformsDict, roi=None, asImg=False):
    self.loader = loader
    self.transformsDict = transformsDict
    self.roi = roi
    self.asImg = asImg
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
    imgO = Views.zeroMin(Views.interval(imgT, minC, maxC))
    return ImgView.wrap(imgO, img.factory()) if self.asImg else imgO


class ImageJLoader(CacheLoader):
  def get(self, path):
    return IL.wrap(IJ.openImage(path))
  def load(self, path):
    return self.get(path)


class InRAMLoader(CacheLoader):
  """ A dummy loader that returns images from a dictionary,
      where the 'paths' are the keys. """
  def __init__(self, table):
    self.table = table
  def get(self, path):
    return self.table[path]
  def load(self, path):
    return self.get(path)


def readN5(path, dataset_name, show=None):
  """ path: filepath to the folder with N5 data.
      dataset_name: name of the dataset to use (there could be more than one).
      show: defaults to None. "IJ" for virtual stack, "BDV" for BigDataViewer.
      
      If "IJ", returns the RandomAccessibleInterval and the ImagePlus.
      If "BDV", returns the RandomAccessibleInterval and the bdv instance. """
  img = N5Utils.open(N5FSReader(path, GsonBuilder()), dataset_name)
  if show:
    if "IJ" == show:
      return img, showStack(img, title=dataset_name)
    elif "BDV" == show:
      return img, showBDV(img, title=dataset_name)
  return img


def writeN5(img, path, dataset_name, blockSize, gzip_compression_level=4, n_threads=0):
  """ img: the RandomAccessibleInterval to store in N5 format.
      path: the directory to store the N5 data.
      dataset_name: the name of the img data.
      blockSize: an array or list as long as dimensions has the img, specifying
                 how to chop up the img into pieces.
      gzip_compression_level: defaults to 4, ranges from 0 (no compression) to 9 (maximum;
                              see java.util.zip.Deflater for details.).
      n_threads: defaults to as many as CPU cores, for parallel writing. """
  N5Utils.save(img, N5FSWriter(path, GsonBuilder()),
               dataset_name, blockSize,
               GzipCompression(gzip_compression_level),
               newFixedThreadPool(n_threads))
