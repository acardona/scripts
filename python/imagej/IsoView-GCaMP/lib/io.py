from java.io import RandomAccessFile
from net.imglib2.img.array import ArrayImgs
from jarray import zeros, array
from java.nio import ByteBuffer, ByteOrder
from java.math import BigInteger
from java.util import Arrays
from java.lang import System, Long
import operator, sys, os
from net.imglib2 import RandomAccessibleInterval, IterableInterval
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img import ImgView
from net.imglib2.cache import CacheLoader
from net.imglib2.realtransform import RealViews
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.img.basictypeaccess.array import ByteArray, ShortArray, FloatArray, LongArray
from net.imglib2.type.numeric.integer import UnsignedByteType, UnsignedShortType, LongType
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.type.logic import BitType
from net.imglib2.type import PrimitiveType
from net.imglib2.util import Intervals
from net.imglib2.img.cell import CellGrid, Cell
from net.imglib2.img.basictypeaccess import AccessFlags, ArrayDataAccessFactory
from net.imglib2.cache.ref import SoftRefLoaderCache
from net.imglib2.cache.img import CachedCellImg
from ij.io import FileSaver, ImageReader, FileInfo
from ij import ImagePlus, IJ
from ij.process import ShortProcessor
from synchronize import make_synchronized
from util import syncPrint, newFixedThreadPool
from ui import showStack, showBDV
try:
  # Needs 'SiMView' Fiji update site enabled
  from org.janelia.simview.klb import KLB
except:
  KLB = None
  print "*** KLB library is NOT installed ***"
try:
  from org.janelia.saalfeldlab.n5.imglib2 import N5Utils
  from org.janelia.saalfeldlab.n5 import N5FSReader, N5FSWriter, GzipCompression, RawCompression
except:
  print "*** n5-imglib2 from github.com/saalfeldlab/n5-imglib2 not installed. ***"
from com.google.gson import GsonBuilder
from math import ceil
from itertools import imap
try:
  from fiji.scripting import Weaver
  """ TODO isn't working, even when tools.jar is present
  # Check if the tools.jar is in the classpath
  try:
    Class.forName("com.sun.tools.javac.Main")
  except:
    print "*** tools.jar not in the classpath ***"
  """
except:
  print "*** fiji.scripting.Weaver NOT installed ***"
  Weaver = None
  print sys.exc_info()


def findFilePaths(srcDir, extension):
  """ Find file paths that match the filename extension,
      recursively into any subdirectories. """
  paths = []
  for root, dirs, filenames in os.walk(srcDir):
    for filename in filenames:
      if filename.endswith(extension):
        paths.append(os.path.join(root, filename))
  paths.sort()
  return paths
  

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


# An inlined java method for deinterleaving a short[] array
# such as from .dat FIBSEM files where channels are stored
# spatially array-adjacent, i.e. for 2 channels, 2 consecutive shorts.
if Weaver:
  wd = Weaver.method("""
static public final void toUnsigned(final short[] signed) {
  short min = 32767; // max possible signed short value
  for (int i=0; i<signed.length; ++i) {
    if (signed[i] < min) min = signed[i];
  }
  if (min < 0) {
    for (int i=0; i<signed.length; ++i) {
      signed[i] -= min;
    }
  }
}

static public final short[][] deinterleave(final short[] source,
                                           final int numChannels,
                                           final int channel_index) {
  if (channel_index >= 0) {
    // Read a single channel
    final short[] shorts = new short[source.length / numChannels];
    for (int i=channel_index, k=0; i<source.length; ++k, i+=numChannels) {
      shorts[k] = source[i];
    }
    return new short[][]{shorts};
  }
  final short[][] channels = new short[numChannels][source.length / numChannels];
  for (int i=0, k=0; i<source.length; ++k) {
    for (int c=0; c<numChannels; ++c, ++i) {
      channels[c][k] = source[i];
    }
  }
  return channels;
}
""", [], False) # no imports, and don't show code


def readFIBSEMdat(path, channel_index=-1, header=1024, magic_number=3555587570, asImagePlus=False, toUnsigned=True):
  """ Read a file from Shan Xu's FIBSEM software, where two or more channels are interleaved.
      Assumes channels are stored in 16-bit.
      
      path: the file path to the .dat file.
      channel_index: the 0-based index of the channel to parse, or -1 (default) for all.
      header: defaults to a length of 1024 bytes
      magic_number: defaults to that for version 8 of Shan Xu's .dat image file format.
      isSigned: defaults to True, will subtract the min value when negative.
      asImagePlus: return a list of ImagePlus instead of ArrayImg which is the default.
  """
  ra = RandomAccessFile(path, 'r')
  try:
    # Check the magic number
    ra.seek(0)
    magic = ra.readInt() & 0xffffffff
    if magic != magic_number:
      msg = "magic number mismatch: v8 magic " + str(magic_number) + " != " + str(magic) + " for path:\n" + path
      System.out.println(msg)
      print msg
      # Continue: attempt to parse the file anyway
    # Read the number of channels
    ra.seek(32)
    numChannels = ra.readByte() & 0xff # a single byte as unsigned integer
    # Parse width and height
    ra.seek(100)
    width = ra.readInt()
    ra.seek(104)
    height = ra.readInt()
    # Read the whole interleaved pixel array
    ra.seek(header)
    bytes = zeros(width * height * 2 * numChannels, 'b') # 2 for 16-bit
    ra.read(bytes)
    # Parse as 16-bit array
    sb = ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN).asShortBuffer()
    shorts = zeros(width * height * numChannels, 'h')
    sb.get(shorts)
    # Attempt to help releasing memory
    bytes = None
    sb = None
    # Deinterleave channels and convert to unsigned short
    # Shockingly, these values are signed shorts, not unsigned! (for first popeye2 squid volume, December 2021)
    # With Weaver: fast
    channels = wd.deinterleave(shorts, numChannels, channel_index)
    if toUnsigned:
      for s in channels:
        wd.toUnsigned(s)
    # With python array sampling: very slow, and not just from iterating whole array once per channel
    #seq = xrange(numChannels) if -1 == channel_index else [channel_index]
    #channels = [shorts[i::numChannels] for i in seq]
    if asImagePlus:
      return [ImagePlus(str(i), ShortProcessor(width, height, s, None)) for i, s in enumerate(channels)]
    else:
      return [ArrayImgs.unsignedShorts(s, [width, height]) for s in channels]
  finally:
    ra.close()

if KLB:
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
    return self.klb.readFull(path) # net.imglib2.img.Img


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


class BinaryLoader(CacheLoader):
  """ stype: a string such as "8-bit", "16-bit" or "floats".
      dimensions: a list of integers
      options: keyword arguments as present in the binary loading functions, such as header size, byte order, etc.
  """
  def __init__(self, stype, dimensions, **options):
    self.fn = { "8-bit": readUnsignedBytes,
               "16-bit": readUnsignedShorts,
               "floats": readFloats}[stype]
    self.dimensions = dimensions
    self.options = options
  def get(self, path):
    return self.fn(path, self.dimensions, **self.options)
  def load(self, path):
    return self.get(path)


class SectionCellLoader(CacheLoader):
  """
  A CacheLoader that can load Cell instances using ImageJ's I/O library. 
  Cells only tile in the last dimension, e.g.:
    * a series of sections (one per file) for a 3D volume;
    * a series of 3D volumes (one per file) for a 4D volume.
  """
  def __init__(self, filepaths, asArrayImg, loadFn=IJ.openImage):
    """
    filepaths: list of file paths, one per cell.
    asArrayImg: a function that takes the index and an ImagePlus as argumebts and returns an ArrayImg for the Cell.
    loadFn: default to IJ.openImage. Must return an object that asArrayImg can convert into an ArrayImg.
    """
    self.filepaths = filepaths
    self.asArrayImg = asArrayImg
    self.loadFn = loadFn
  
  def get(self, index):
    img = self.asArrayImg(index, self.loadFn(self.filepaths[index]))
    dims = Intervals.dimensionsAsLongArray(img)
    return Cell(list(dims) + [1], # cell dimensions
                [0] * img.numDimensions() + [index], # position in the grid: 0, 0, 0, Z-index
                img.update(None)) # get the underlying LongAccess


def lazyCachedCellImg(loader, volume_dimensions, cell_dimensions, pixelType, primitiveType):
  """ Create a lazy CachedCellImg, backed by a SoftRefLoaderCache,
      which can be used to e.g. create the equivalent of ij.VirtualStack but with ImgLib2,
      with the added benefit of a cache based on SoftReference (i.e. no need to manage memory).

      loader: a CacheLoader that returns a single Cell for each index (like the Z index in a VirtualStack).
      volume_dimensions: a list of int or long numbers, with the last dimension
                         being the number of Cell instances (i.e. the number of file paths).
      cell_dimensions: a list of int or long numbers, whose last dimension is 1.
      pixelType: e.g. UnsignedByteType
      primitiveType: e.g. BYTE

      Returns a CachedCellImg.
  """
  return CachedCellImg(CellGrid(volume_dimensions, cell_dimensions),
                       pixelType(),
                       SoftRefLoaderCache().withLoader(loader),
                       ArrayDataAccessFactory.get(primitiveType, AccessFlags.setOf(AccessFlags.VOLATILE)))


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
               GzipCompression(gzip_compression_level) if gzip_compression_level > 0 else RawCompression(),
               newFixedThreadPool(n_threads=n_threads, name="jython-n5writer"))


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


def parseNextIntBigEndian(ra, count):
  # ra: a RandomAccessFile at the correct place to read the next sequence of bytes
  bytes = zeros(count + 1, 'b')
  ra.read(bytes, 1, count) # a leading zero to avoid parsing as negative numbers
  return BigInteger(bytes).longValue() # long to avoid bit overflows

def parseNextIntLittleEndian(ra, count):
  # ra: a RandomAccessFile at the correct place to read the next sequence of bytes
  bytes = zeros(count + 1, 'b')
  ra.read(bytes, 0, count) # ending zero will be the leading zero when reversed
  return BigInteger(reversed(bytes)).longValue() # long to avoid bit overflows


def parseIFD(ra, parseNextInt):
  """ An IFD (image file directory) is the metadata for one image (e.g. one slice)
      contained within a TIFF stack.
      
      ra: RandomAccessFile.
      parseNextInt: function that takes an ra and the count of bytes to parse.
      
      returns a dictionary with some keys from the IFD (width, height, samples_per_pixel and offset)
              and the offset of the IFD of the next image plane."""
  # Assumes ra is at the correct offset to start reading the IFD
  # First the NumDirEntries as 2 bytes
  # Then the TagList as zero or more 12-byte entries
  # Finally the NextIFDOffset: 4 bytes, the offset to the next IFD (i.e. metadata to the next image)
  # Each tag has:
  # - TagId (2 bytes): many, e.g.:
  #       256: image width
  #       257: image height (aka image length)
  #       258: bits per sample (bit depth)
  #       259: compression (short), can be e.g.
  #                    1: uncompressed
  #                32773: PackBits compression
  #                    5: LZW compression
  #                    6: JPEG compression
  #       273: strip offsets (offset to start of image data, as array of offset values, one per strip,
  #                           which indicate the position of the first byte of each strip within the TIFF file)
  #       279: strip byte count (number of bytes per strip, when uncompressed is width*height)
  #       277: samples per pixel (number of channels)
  #       278: rows per strip (akin to image height)
  # - DataType (2 bytes): 1 byte (8-bit unsigned int),
  #                       2 ascii (8-bit NULL-terminated string),
  #                       3 short (16-bit unsigned int),
  #                       4 long (32-bit unsigned int)
  #                       5 rational (two 32-bit unsigned integers)
  #                       6 sbyte (8-bit signed int)
  #                       7 undefined (8-bit byte)
  #                       8 sshort (16-bit signed int)
  #                       9 slong (32-bit signed int)
  #                      10 srational (two 32-bit signed int)
  #                      11 float (4-byte float)
  #                      12 double (8-byte float)
  nBytesPerType = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}
  # - DataCount (4 bytes): number of items in the tag data (e.g. if 8, and Datatype is 4, means 8 x 32-bit consecutive numbers)
  # - DataOffset (4 bytes): offset to the data items. If four bytes or less in size, the data may be found in this
  #                         field as left-justified, i.e. if it uses less than 4 bytes, it's in the first bytes.
  #                         If the tag data is greater than four bytes in size, then this field contains an offset
  #                         to the position of the data in the TIFF file.
  nTags = parseNextInt(ra, 2) # NumDirEntries
  #print "nTags", nTags
  # A minimum set of tags to read for simple, uncompressed images
  tagNames = {256: "width",
              257: "height", # aka image length
              258: "bitDepth",
              259: "compression",
              273: "StripOffsets", # always a list  # was: offset
              277: "samples_per_pixel",
              278: "RowsPerStrip", # always a list
              279: "StripByteCounts"} # always a list  # was: n_bytes
  # Set of tags that are always lists, even when they contain a single value
  countable = set(["StripOffsets", "RowsPerStrip", "StripByteCounts"])
  tags = {}
  for i in xrange(nTags):
    tagId = parseNextInt(ra, 2)
    #print "tagId", tagId
    name = tagNames.get(tagId, None)
    if name:
      dataType = parseNextInt(ra, 2)
      dataCount = parseNextInt(ra, 4)
      n = nBytesPerType[dataType]
      #print "name: %s, n: %i dataType: %i dataCount %i" % (name, n, dataType, dataCount)
      if n > 4 or dataCount > 1:
        # jump ahead and come back
        pos = ra.getFilePointer()
        offset = parseNextInt(ra, 4)
        ra.seek(offset)
        dataOffset = [parseNextInt(ra, n) for _ in xrange(dataCount)]
        if 1 == dataCount and name not in countable:
          dataOffset = dataOffset[0]
        ra.seek(pos + 4) # restore position to continue reading tags
      else:
        # data embedded in dataOffset
        dataOffset = parseNextInt(ra, n) # should have the actual data, left-justified
        if name in countable:
          dataOffset = [dataOffset]
        ra.skipBytes(4 - n) # if any left to skip up to 12 total for the tag entry, may skip none        
      tags[name] = dataOffset
      #print "tag: %s, dataType: %i, dataCount: %i" % (name, dataType, dataCount), "dataOffset:", dataOffset
    else:
      ra.skipBytes(10) # 2 were for the tagId, 12 total for each tag entry
  nextIFDoffset = parseNextInt(ra, 4)
  return tags, nextIFDoffset


def parse_TIFF_IFDs(filepath):
  """ Returns a generator of dictionaries of tags for each IFD in the TIFF file,
      as defined by the 'parseIFD' function above. """
  ra = RandomAccessFile(filepath, 'r')
  try:
    # TIFF file format can have metadata at the end after the images, so the above approach can fail
    # TIFF file header is 8-bytes long:
    # (See: http://paulbourke.net/dataformats/tiff/tiff_summary.pdf )
    #
    # Bytes 1 and 2: identifier. Either the value 4949h (II) or 4D4Dh (MM),
    #                            meaning little-endian and big-endian, respectively.
    # All data encountered past the first two bytes in the file obey
    # the byte-ordering scheme indicated by the identifier field.
    b1, b2 = ra.read(), ra.read() # as two java int, each one byte sized
    bigEndian = chr(b1) == 'M'
    parseNextInt = parseNextIntBigEndian if bigEndian else parseNextIntLittleEndian
    # Bytes 3 and 4: Version: Always 42
    ra.skipBytes(2)
    # Bytes 5,6,7,8: IFDOffset: offset to first image file directory (IFD), the metadata entry for the first image.
    nextIFDoffset = parseNextInt(ra, 4) # offset to first IFD
    while nextIFDoffset != 0:
      ra.seek(nextIFDoffset)
      tags, nextIFDoffset = parseIFD(ra, parseNextInt)
      tags["bigEndian"] = bigEndian
      yield tags
  finally:
    ra.close()


def getIFDImageBytes(ra, tags):
  """ Read byte[] from a TIFF file IFD, which may or may not be compressed. """
  bytes = zeros(sum(tags["StripByteCounts"]), 'b')
  indexP = 0
  for strip_offset, strip_length in zip(tags["StripOffsets"], tags["StripByteCounts"]):
    ra.seek(strip_offset)
    ra.read(bytes, indexP, strip_length)
    indexP += strip_length
  return bytes

def unpackBits(ra, tags, use_imagereader=False):
  # Decompress a packBits-compressed image, write into bytes array starting at indexU.
  # ra: a RandomAccessFile with the pointer at the right place to start reading.
  # PackBits actually packages bytes: a byte-wise RLE most efficient at encoding runs of bytes
  # 3 types of data packets:
  # 1. two-byte encoded run packet:
  #     - first byte is the number of bytes in the run.
  #       Ranges from -127 to -1, meaning +1: from 2 to 128 (-count + 1)
  #     - second byte value of each byte in the run.
  # 2. literal run packet: stores 1 to 128 bytes literally without compression.
  #     - first byte is the number of bytes in the run.
  #       Ranges from 0 to 127, indicating 1 to 128 values (count + 1)
  #     - then the sequence of literal bytes
  # 3. no-op packet: never used, value -128.
  # See documentation: http://paulbourke.net/dataformats/tiff/tiff_summary.pdf
  # (note documentation PDF has its details flipped when it comes to the ranges for literal runs and packed runs)
  # See also: ij.io.ImageReader.packBitsUncompress (a public method without side effects)
  
  if use_imagereader:
    return ImageReader(FileInfo()).packBitsUncompress(getIFDImageBytes(ra, tags),
                                                      tags["width"] * tags["height"])
  
  try:
    bytes = zeros(tags["width"] * tags["height"], 'b')
    indexU = 0 # index over unpacked bytes
    for strip_offset, strip_length in zip(tags["StripOffsets"], tags["StripByteCounts"]):
      ra.seek(strip_offset)
      indexP = 0
      while indexP < strip_length and indexU < len(bytes):
        count = ra.readByte()
        if count >= 0:
          # Literal run
          ra.read(bytes, indexU, count + 1)
          indexP += count + 2 # one extra for the count byte
          indexU += count + 1
        else:
          # Packed run
          Arrays.fill(bytes, indexU, indexU - count + 1, ra.readByte())
          indexP += 2
          indexU += -count + 1
  except:
    print sys.exc_info()
  finally:
    return bytes


def unpackBits2(bytes_packedbits, tags, use_imagereader=False):
  # Decompress a packBits-compressed image, returns an array of n_bytes.
  # ra: a RandomAccessFile with the pointer at the right place to start reading.
  # PackBits actually packages bytes: a byte-wise RLE most efficient at encoding runs of bytes
  # 3 types of data packets:
  # 1. two-byte encoded run packet:
  #     - first byte is the number of bytes in the run.
  #       Ranges from -127 to -1, meaning +1: from 2 to 128 (-count + 1)
  #     - second byte value of each byte in the run.
  # 2. literal run packet: stores 1 to 128 bytes literally without compression.
  #     - first byte is the number of bytes in the run.
  #       Ranges from 0 to 127, indicating 1 to 128 values (count + 1)
  #     - then the sequence of literal bytes
  # 3. no-op packet: never used, value -128.
  # See documentation: http://paulbourke.net/dataformats/tiff/tiff_summary.pdf
  # (note documentation PDF has its details flipped when it comes to the ranges for literal runs and packed runs)
  # See also: ij.io.ImageReader.packBitsUncompress (a public method without side effects)

  n_bytes = tags["width"] * tags["height"]

  if use_imagereader:
    return ImageReader(FileInfo()).packBitsUncompress(bytes_packedbits, n_bytes)
    
  bytes = zeros(n_bytes, 'b')
  try:
    indexP = 0 # packed
    indexU = 0 # unpacked
    while indexU < n_bytes:
      count = bytes_packedbits[indexP]
      if count >= 0:
        # Literal run
        System.arraycopy(bytes_packedbits, indexP + 1, bytes, indexU, count + 1)
        indexP += count + 2 # one extra for the 'count' byte
        indexU += count + 1
      else:
        # Packed run
        Arrays.fill(bytes, indexU, indexU - count + 1, bytes_packedbits[indexP + 1])
        indexP += 2
        indexU += -count + 1
  except:
    print sys.exc_info()
  finally:
    return bytes


def read_TIFF_plane(ra, tags, handler=None):
  """ ra: RandomAccessFile
      tags: dicctionary of TIFF tags for the IFD of the plane to parse.
      handler: defaults to Nobe; a function that reads the image data and returns an array.

      For compressed image planes, takes advantage of the ij.io.ImageReader class
      which contains methods that ought to be static (no side effects) and therefore
      demand a dummy constructor just to invoke them.
  """
  if handler:
    return handler(ra, tags)
  # Values of the "compressed" tag field (when present):
  #     1: "uncompressed",
  # 32773: "packbits",
  #     5: "LZW",
  #     6: "JPEG",
  width, height = tags["width"], tags["height"]
  bitDepth = tags["bitDepth"]
  n_bytes = int(ceil(width * height * (float(bitDepth) / 8))) # supports bitDepth < 8
  compression = tags.get("compression", 1)
  bytes = None

  if 32773 == compression:
    bytes = unpackBits(ra, tags, use_imagereader=True) 
  elif 5 == compression:
    bytes = ImageReader(FileInfo()).lzwUncompress(getIFDImageBytes(ra, tags),
                                                  tags["width"] * tags["height"])
  elif 32946 == compression or 8 == compression:
    bytes = ImageReader(FileInfo()).zipUncompress(getIFDImageBytes(ra, tags),
                                                  tags["width"] * tags["height"])
  elif 1 == compression:
    bytes = zeros(n_bytes, 'b')
    index = 0
    for strip_offset, strip_length in zip(tags["StripOffsets"], tags["StripByteCounts"]):
      ra.seek(strip_offset)
      ra.read(bytes, index, strip_length)
  elif 6 == compression:
    print "Unsupported compression: JPEG"
    raise Exception("Can't handle JPEG compression of TIFF image planes")
  else:
    raise Exception("Can't deal with compression type " + str(compression))

  # If read as bytes, parse to the appropriate primitive type
  if 8 == bitDepth:
    return bytes
  bb = ByteBuffer.wrap(bytes)
  if not tags["bigEndian"]:
    bb = bb.order(ByteOrder.BIG_ENDIAN)
  if 16 == bitDepth:
    pixels = zeros(width * height, 'h')
    bb.asShortBuffer().get(pixels)
    return pixels
  if 32 == bitDepth:
    pixels = zeros(width * height, 'f')
    bb.asFloatBuffer().get(pixels)
    return pixels
  if bitDepth < 8:
    # Support for 1-bit, 2-bit, 3-bit, ... 12-bit, etc. images
    pixels = zeros(int(ceil(width * height * bitDepth / 64.0)), 'l')
    bb.asLongBuffer().get(pixels)
    # Reverse bits from left to right to right to left for ImgLib2 LongArray
    pixels = array(imap(Long.reverse, pixels), 'l')
    return pixels


class TIFFSlices(CacheLoader):
  """ Unless additional types are provided to the constructor,
      supports only UnsignedByteType, UnsignedShortType, FloatType and LongType. """
  types = { 8: (ByteArray, PrimitiveType.BYTE, UnsignedByteType),
           16: (ShortArray, PrimitiveType.SHORT, UnsignedShortType),
           32: (FloatArray, PrimitiveType.FLOAT, FloatType),
           64: (LongArray, PrimitiveType.LONG, LongType),
            1: (LongArray, PrimitiveType.LONG, BitType)}
  
  def __init__(self, filepath, types=None):
    self.filepath = filepath
    self.IFDs = list(parse_TIFF_IFDs(filepath)) # the tags of each IFD
    # Assumes all TIFF slices have the same dimensions and type
    print self.IFDs[0]
    self.cell_dimensions = [self.IFDs[0]["width"], self.IFDs[0]["height"], 1]
    self.types = types if types else TIFFSlices.types
  
  def get(self, index):
    IFD = self.IFDs[index]
    ra = RandomAccessFile(self.filepath, 'r')
    try:
      cell_position = [0, 0, index]
      pixels = read_TIFF_plane(ra, IFD) # a native array
      access = self.types[IFD["bitDepth"]][0] # e.g. ByteArray, FloatArray ...
      return Cell(self.cell_dimensions, cell_position, access(pixels))
    finally:
      ra.close()
  
  def asLazyCachedCellImg(self):
    access, primitiveType, pixelType = self.types[self.IFDs[0]["bitDepth"]]
    return lazyCachedCellImg(self, self.cell_dimensions[:-1] + [len(self.IFDs)],
                             self.cell_dimensions, pixelType, primitiveType)

