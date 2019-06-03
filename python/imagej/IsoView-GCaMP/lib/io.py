from java.io import RandomAccessFile
from net.imglib2.img.array import ArrayImgs
from jarray import zeros
from java.nio import ByteBuffer, ByteOrder
import operator
from net.imglib2 import RandomAccessibleInterval, IterableInterval
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img import ImgView
from net.imglib2.cache import CacheLoader
from net.imglib2.realtransform import RealViews
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.type.numeric.integer import UnsignedByteType, UnsignedShortType
from net.imglib2.type.numeric.real import FloatType
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


def readFloats(path, dimensions, header=0, byte_order=ByteOrder.LITTLE_ENDIAN):
  """ Read a file as an ArrayImg of FloatType """
  size = reduce(operator.mul, dimensions)
  ra = RandomAccessFile(path, 'r')
  try:
    if header < 0:
      # Interpret from the end: useful for files with variable header lengths
      # such as some types of uncompressed TIFF formats
      header = ra.length() + header
    ra.skipBytes(header)
    bytes = zeros(size * 4, 'b')
    ra.read(bytes)
    floats = zeros(size, 'f')
    ByteBuffer.wrap(bytes).order(byte_order).asFloatBuffer().get(floats)
    return ArrayImgs.floats(floats, dimensions)
  finally:
    ra.close()


def readUnsignedShorts(path, dimensions, header=0, return_array=False, byte_order=ByteOrder.LITTLE_ENDIAN):
  """ Read a file as an ArrayImg of UnsignedShortType """
  size = reduce(operator.mul, dimensions)
  ra = RandomAccessFile(path, 'r')
  try:
    if header < 0:
      # Interpret from the end: useful for files with variable header lengths
      # such as some types of uncompressed TIFF formats
      header = ra.length() + header
    ra.skipBytes(header)
    bytes = zeros(size * 2, 'b')
    ra.read(bytes)
    shorts = zeros(size, 'h') # h is for short
    ByteBuffer.wrap(bytes).order(byte_order).asShortBuffer().get(shorts)
    return shorts if return_array else ArrayImgs.unsignedShorts(shorts, dimensions)
  finally:
    ra.close()


def readUnsignedBytes(path, dimensions, header=0):
  """ Read a file as an ArrayImg of UnsignedShortType """
  ra = RandomAccessFile(path, 'r')
  try:
    if header < 0:
      # Interpret from the end: useful for files with variable header lengths
      # such as some types of uncompressed TIFF formats
      header = ra.length() + header
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


def read2DImageROI(path, dimensions, interval, pixelType=UnsignedShortType, header=0, byte_order=ByteOrder.LITTLE_ENDIAN):
  """ Read a region of interest (the interval) of an image in a file.
      Assumes the image is written with the first dimension moving slowest.

      path: the file path to the image file.
      dimensions: a sequence of integer values e.g. [512, 512, 512]
      interval: two sequences of integer values defining the min and max coordinates, e.g.
                [[20, 0], [400, 550]]
      pixeltype: e.g. UnsignedShortType, FloatType
      header: defaults to zero, the number of bytes between the start of the file and the start of the image data.

      Supports only these types: UnsignedByteType, UnsignedShortType, FloatType.

      Returns an ArrayImg of the given type.
  """
  ra = RandomAccessFile(path, 'r')
  try:
    width, height = dimensions
    minX, minY = interval[0]
    maxX, maxY = interval[1]
    roi_width, roi_height = maxX - minX + 1, maxY - minY + 1
    tailX = width - roi_width - minX

    #print minX, minY
    #print maxX, maxY
    #print roi_width, roi_height

    size = roi_width * roi_height
    n_bytes_per_pixel = pixelType().getBitsPerPixel() / 8

    #print n_bytes_per_pixel

    bytes = zeros(size * n_bytes_per_pixel, 'b')

    # Read only the 2D ROI
    ra.seek(header + (minY * width + minX) * n_bytes_per_pixel)
    for h in xrange(roi_height):
      ra.readFully(bytes, h * roi_width * n_bytes_per_pixel, roi_width * n_bytes_per_pixel)
      ra.skipBytes((tailX + minX) * n_bytes_per_pixel)
    # Make an image
    roiDims = [roi_width, roi_height]
    if UnsignedByteType == pixelType:
      return ArrayImgs.unsignedBytes(bytes, roiDims)
    if UnsignedShortType == pixelType:
      shorts = zeros(size, 'h')
      ByteBuffer.wrap(bytes).order(byte_order).asShortBuffer().get(shorts)
      return ArrayImgs.shorts(shorts, roiDims)
    if FloatType == pixelType:
      floats = zeros(size, 'f')
      ByteBuffer.wrap(bytes).order(byte_order).asFloatBuffer().get(floats)
      return ArrayImgs.floats(floats, roiDims)
  finally:
    ra.close()
