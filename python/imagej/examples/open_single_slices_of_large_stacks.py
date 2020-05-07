from loci.formats import ChannelSeparator
import os, sys

# Read the dimensions of the image at path by parsing the file header only,
# thanks to the LOCI Bioformats library

filepath = "/home/albert/Desktop/t2/bat-cochlea-volume.tif"

try:
  fr = ChannelSeparator()
  fr.setGroupFiles(False)
  fr.setId(filepath)
  width, height, nSlices = fr.getSizeX(), fr.getSizeY(), fr.getSizeZ()
  n_pixels = width * height * nSlices
  bitDepth = fr.getBitsPerPixel()
  fileSize = os.path.getsize(filepath)
  headerSize = fileSize - (n_pixels * bitDepth / 8) # 8 bits in 1 byte
  print "Dimensions:", width, height, nSlices
  print "Bit depth: %i-bit" % bitDepth
  print "Likely header size, in number of bytes:", headerSize
except:
  # Print the error, if any
  print sys.exc_info()
finally:
  fr.close() # close the file handle safely and always



# For parsing TIFF file headers
from java.io import RandomAccessFile
from java.math import BigInteger

def parseNextIntBigEndian(ra, count):
  # ra.read() reads a single byte as an unsigned int
  return BigInteger([ra.readByte() for _ in xrange(count)]).intValue()

def parseNextIntLittleEndian(ra, count):
  # ra.read() reads a single byte as an unsigned int
  return BigInteger(reversed([ra.readByte() for _ in xrange(count)])).intValue()

def parseIFD(ra, parseNextInt):
  # Assumes ra is at the correct offset to start reading the IFD
  # First the NumDirEntries as 2 bytes
  # Then the TagList as zero or more 12-byte entries
  # Finally the NextIFDOffset: 4 bytes, the offset to the next IFD (i.e. metadata to the next image)
  # Each tag has:
  # - TagId (2 bytes): many, e.g.:
  #       256: image width
  #       257: image height
  #       273: strip offsets (offset to start of image data, as ray of offset values, one per strip,
  #                           which indicate the position of the first byte of each strip within the TIFF file)
  #       277: samples per pixel
  # - DataType (2 bytes): 1 byte (8-bit unsigned int),
  #                       2 ascii (8-bit NULL-terminated string),
  #                       3 short (16-bit unsigned int),
  #                       4 long (32-bit unsigned int)
  #                       5 rational (two 32-bit unsigned integers)
  #                       6 sbyte (8-bit signed int)
  #                       7 undefine (8-bit byte)
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
  print "nTags", nTags
  # A minimum set of tags to read for simple, uncompressed images
  tagNames = {256: "width",
              257: "height",
              273: "offset",
              277: "samples_per_pixel"}
  tags = {}
  for i in xrange(nTags):
    tagId = parseNextInt(ra, 2)
    print "tagId", tagId
    name = tagNames.get(tagId, None)
    if name:
      dataType = parseNextInt(ra, 2)
      dataCount = parseNextInt(ra, 4) # always 1 in the 4 tags above
      n = nBytesPerType[dataType]
      if n > 4:
        # jump ahead and come back
        pos = ra.getFilePointer()
        offset = parseNextInt(ra, 4)
        ra.skipBytes(offset - pos) # i.e. ra.seek(offset)
        dataOffset = ra.parseNextInt(ra, n) # a long unsigned int
        ra.seek(pos + 4) # restore position to continue reading tags
      else:
        # offset directly in dataOffset
        dataOffset = parseNextInt(ra, n) # should have the actual data, left-justified
        ra.skipBytes(4 - n) # if any left to skip up to 12 total for the tag entry, may skip none
      tags[name] = dataOffset
      print "tag:", name, dataType, dataCount, dataOffset
    else:
      ra.skipBytes(10) # 2 were for the tagId, 12 total for each tag entry
  nextIFDoffset = parseNextInt(ra, 4)
  return tags, nextIFDoffset
  

if filepath.endswith("tif"):
  try:
    ra = RandomAccessFile(filepath, 'r')
    # TIFF file format can have metadata at the end after the images, so the above approach can fail
    # TIFF file header is 8-bytes long:
    # (See: http://paulbourke.net/dataformats/tiff/tiff_summary.pdf )
    #
    # Bytes 1 and 2: identifier. Either the value 4949h (II) or 4D4Dh (MM),
    #                            meaning little-ending and big-endian, respectively.
    # All data encountered past the first two bytes in the file obey
    # the byte-ordering scheme indicated by the identifier field.
    b1, b2 = ra.read(), ra.read() # as two java int, each one byte sized
    bigEndian = chr(b1) == 'M'
    parseNextInt = parseNextIntBigEndian if bigEndian else parseNextIntLittleEndian
    # Bytes 3 and 4: Version: Always 42
    ra.skipBytes(2)
    # Bytes 5,6,7,8: IFDOffset: offset to first image file directory (IFD), the metadata entry for the first image.
    firstIFDoffset = parseNextInt(ra, 4)
    ra.skipBytes(firstIFDoffset - ra.getFilePointer()) # minus the current position: all offsets are absolute
    firstTags, _ = parseIFD(ra, parseNextInt)
    # Correct headerSize for TIFF files (and then assuming images are contiguous and in order,
    # which they don't have to be either in TIFF)
    headerSize = firstTags["offset"]
    # Sanity check:
    if width != firstTags["width"] or height != firstTags["height"] or bitDepth != firstTags["samples_per_pixel"] * 8:
      print "TIFF header disagrees with ChannelSeparator's parsing of metadata."
  finally:
    ra.close()


"""

# Try to read the header size using OME as per Curtis Rueden's suggestion

from loci.common import RandomAccessInputStream, Location
ira = None
cs = None
try:
  #rais = RandomAccessInputStream(filepath)
  #Location.mapFile("my-rais", rais)
  cs = ChannelSeparator()
  cs.setId(filepath)
  Location.mapFile("my-rais", cs)
  ira = Location.getHandle("my-rais")
  print "IRA file pointer:", ira.getFilePointer()
except:
  print sys.exc_info()
finally:
  cs.close()
  if ira: ira.close()

"""


from ij import IJ

# Various approaches to open slice 10 only from a stack
slice_index = 6 # 1-based
num_slices = 3 # change to e.g. 3 to open 3 consecutive slices as a stack
slice_offset = width * height * (bitDepth / 8) * (slice_index -1)


# Approach 1: using the "Raw" command with macro parameters for its dialog
IJ.run("Raw...", "open=%s image=%i-bit width=%i height=%i number=%i offset=%i big-endian"
                 % (filepath, bitDepth, width, height, num_slices, headerSize + slice_offset))



# Approach 2: using LOCI bio-formats
from loci.plugins.util import BFVirtualStack
from loci.formats import ChannelSeparator
from ij import ImagePlus, ImageStack

try:
  cs = ChannelSeparator()
  cs.setId(filepath)
  bfvs = BFVirtualStack(filepath, cs, False, False, False)
  stack = ImageStack(width, height)
  for index in xrange(slice_index, slice_index + num_slices):
    stack.addSlice(bfvs.getProcessor(index))
  title = os.path.split(filepath)[1] + " from slice %i" % slice_index
  imp = ImagePlus(title, stack)
  imp.show()
finally:
  cs.close()



# Approach 3: using low-level ImageJ libraries
from ij.io import FileInfo, FileOpener

fi = FileInfo()
fi.width = width
fi.height = height
fi.offset = headerSize + slice_offset
# ASSUMES images aren't ARGB, which would also have 32 as bit depth
# (There are other types: see FileInfo javadoc)
fi.fileType = { 8: FileInfo.GRAY8,
               16: FileInfo.GRAY16_UNSIGNED,
               24: FileInfo.RGB,
               32: FileInfo.GRAY32_UNSIGNED}[bitDepth]
fi.samplesPerPixel = 1
fi.nImages = num_slices
directory, filename = os.path.split(filepath)
fi.directory = directory
fi.fileName = filename

imp = FileOpener(fi).openImage() # returns an ImagePlus
imp.show()


# Approach 4: with low-level java libraries
from ij import ImagePlus, ImageStack
from ij.process import ByteProcessor, ShortProcessor, FloatProcessor
from java.io import RandomAccessFile
from jarray import zeros
from java.nio import ByteBuffer, ByteOrder

try:
  ra = RandomAccessFile(filepath, 'r')
  ra.skipBytes(headerSize + slice_offset)
  stack = ImageStack(width, height)
  slice_n_bytes = width * height * (bitDepth / 8)
  # ASSUMES images aren't RGB or ARGB
  image_type = { 8: ('b', None, ByteProcessor),
                16: ('h', "asShortBuffer", ShortProcessor),
                32: ('f', "asFloatBuffer", FloatProcessor)}
  pixel_type, convertMethod, constructor = image_type[bitDepth]
  for i in xrange(num_slices):
    bytes = zeros(slice_n_bytes, 'b') # an empty byte[] array
    ra.read(bytes)
    bb = ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN)
    if convertMethod: # if not 8-bit
      pixels = zeros(width * height, pixel_type) # an empty short[] or float[] array
      getattr(bb, convertMethod).get(pixels) # e.g. bb.asShortBuffer().get(pixels)
    else:
      pixels = bytes
    stack.addSlice(constructor(width, height, pixels, None))
    ra.skipBytes(slice_n_bytes)
  #
  imp = ImagePlus(os.path.split(filepath)[1] + " from slice %i" % slice_index, stack)
  imp.show()
finally:
  ra.close()



# Approach 5: with low-level java libraries, straight into ImgLib2 images
from ij import ImagePlus, ImageStack
from net.imglib2.img.basictypeaccess.array import ByteArray, ShortArray, FloatArray
from net.imglib2.img.planar import PlanarImg # a stack of 2D images
from net.imglib2.type.numeric.integer import UnsignedByteType, UnsignedShortType
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.util import Fraction
from java.io import RandomAccessFile
from jarray import zeros
from java.nio import ByteBuffer, ByteOrder
from bdv.util import BdvFunctions
from net.imglib2.img.display.imagej import ImageJFunctions as IL

try:
  ra = RandomAccessFile(filepath, 'r')
  ra.skipBytes(headerSize + slice_offset)
  slices = []
  slice_n_bytes = width * height * (bitDepth / 8)
  # ASSUMES images aren't RGB or ARGB
  image_type = { 8: ('b', None, ByteArray, UnsignedByteType),
                16: ('h', "asShortBuffer", ShortArray, UnsignedShortType),
                32: ('f', "asFloatBuffer", FloatArray, FloatType)}
  pixel_type, convertMethod, constructor, ptype = image_type[bitDepth]
  for i in xrange(num_slices):
    bytes = zeros(slice_n_bytes, 'b') # an empty byte[] array
    ra.read(bytes)
    bb = ByteBuffer.wrap(bytes).order(ByteOrder.BIG_ENDIAN)
    if convertMethod: # if not 8-bit
      pixels = zeros(width * height, pixel_type) # an empty short[] or float[] array
      getattr(bb, convertMethod).get(pixels) # e.g. bb.asShortBuffer().get(pixels)
    else:
      pixels = bytes
    slices.append(constructor(pixels))
    ra.skipBytes(slice_n_bytes)
  #
  img = PlanarImg(slices, [width, height, len(slices)], Fraction(1, 1))
  img.setLinkedType(ptype().getNativeTypeFactory().createLinkedType(img))
  title = os.path.split(filepath)[1] + " from slice %i" % slice_index
  
  # Show in the BigDataViewer
  BdvFunctions.show(img, title)
  
  # Or show as an ImageJ stack (virtual, but all loaded in RAM)
  imp = IL.wrap(img, title)
  imp.show()
finally:
  ra.close()


