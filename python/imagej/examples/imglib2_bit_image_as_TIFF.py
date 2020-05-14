import sys, os, tempfile, operator
from datetime import datetime
from jarray import array
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(sys.argv[0])), "IsoView-GCaMP"))
from lib.io import TIFFSlices
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2.img import ImgView
from net.imglib2.img.array import ArrayImgs
from net.imglib2.type.logic import BitType
from itertools import chain
from net.imglib2.util import Intervals, ImgUtil
from java.io import RandomAccessFile
from java.nio import ByteBuffer
from net.imglib2.roi.geom import GeomMasks
from net.imglib2.roi import Masks, Regions
from collections import deque
from itertools import imap


# A binary image whose pixel values can only take as value either zero or one
# and which is stored in a bit-packed way in a long array:
# each of the 64-bits of a single long in the long[] is a pixel,
# which gives us efficient storage
# (otherwise, the smallest possible would be byte[] with each 1-bit pixel
# being stored using an 8-bit byte, wasting 7 bytes of storage per pixel)
img = ArrayImgs.bits([512, 512, 5])
bitDepth = 1

pixel_array = img.update(None).getCurrentStorageArray()
img_size = reduce(operator.mul, Intervals.dimensionsAsLongArray(img))
array_size = len(pixel_array)
print array_size, "<", img_size
print "Proportion:", array_size / float(img_size), "AKA", img_size / array_size, "x"

# Add some data to it
center = img.dimension(0) / 2, img.dimension(1) / 2
for z in xrange(img.dimension(2)):
  radius = img.dimension(0) * 0.5 / (z + 1)
  circle = GeomMasks.openSphere(center, radius)
  # Works, explicit iteration of every pixel
  #for t in Regions.sample(circle, Views.hyperSlice(img, 2, z)):
  #  t.setOne()
  # Works: about twice as fast -- measured with: from time import time .... t0 = time(); ... t1 = time()
  deque(imap(BitType.setOne, Regions.sample(circle, Views.hyperSlice(img, 2, z))), maxlen=0)
  

# Write as TIFF file
filepath = os.path.join(tempfile.gettempdir(),  
                        "bit-img-" + datetime.now().strftime("%Y-%m-%d-%H:%M:%S") + ".tif") 
ra = RandomAccessFile(filepath, 'rw')
try:
  # Header: big endian (4D, 4D) or (M, M), magic number (42, 42), and offset of 9 bytes to first IFD
  # Note:
  # bin(int("4D", 16))[2:].zfill(8) == '01001101'
  # int("4D", 16) == 77
  ra.write(array([77, 77, 0, 42, 0, 0, 0, 8], 'b'))
  # A tmp plane img to copy into it each 2D slice for saving later as the pixel data of each IFD
  plane_img = ArrayImgs.bits([img.dimension(0), img.dimension(1)])
  plane_array = plane_img.update(None).getCurrentStorageArray() # a long[]
  bb = ByteBuffer.allocate(len(plane_array) * 8) # each long primitive has 8 bytes
  # Each IFD and image data
  # Use either short (3) or int (4) for the DataType, so that ImageJ's ij.io.TiffDecoder can read it
  tags = {256: (4, 4, img.dimension(0)), # signed int (32-bit), 4 bytes, width
          257: (4, 4, img.dimension(1)), # signed int (32-bit), 4 bytes, height
          258: (4, 4, bitDepth), # signed byte, 1 byte, bitDepth (BitsPerSample)
          259: (4, 4, 1), # signed byte, 1 byte, compression: 1 means uncompressed: it's true, in a way
          277: (4, 4, 1), # signed byte, 1 byte, SamplesPerPixel: 1 channel
          278: (4, 4, 1), # signed byte, 1 byte, RowsPerStrip
          279: (4, 4, bb.capacity())} # signed int (32-bit), StripByteCounts
  # Pending to append: variable tag ID 273: ?, # StripOffsets, taking 12 bytes like each of the other tags,
                                               # limiting offset value to within 4 bytes maximum (32-bit unsigned value).
  def asBytes(ID, entry):
    b = ByteBuffer.allocate(12) # (2 + 2 + 4 + 4)
    b.putShort(ID) # TagId
    b.putShort(entry[0]) # DataType
    b.putInt(1) # DataCount
    # DataOffset can contain the data when it fits in 4 bytes, but left-justified: must shift leftwards
    b.putInt(entry[2] << ((4 - entry[1]) * 8))
    return b.array()
  # Copy all fixed tags into a byte[]
  tags_bytes = array(chain.from_iterable(asBytes(ID, entry) for ID, entry in tags.iteritems()), 'b')
  n_bytes_IFD = 2 + len(tags_bytes) + 12 + 4 # NumDirEntries + num tags * 12 + NextIFDOffset, in number of bytes
  offset = 8 # size of TIFF header prior to any IFD
  # Write each image slice (2D plane) as an IFD + pixel data
  for z in xrange(img.dimension(2)):
    # Write IFD
    # Write NumDirEntries as 2 bytes: the number of tags
    ra.writeShort(8) # 7 in tags dict plus tag 273 added later
    # Write each tag as 12 bytes each:
    # First all non-changing tags, constant for all IFDs
    ra.write(tags_bytes)
    # Size of IFD dict in number of bytes
    # Then the variable 273 tag: the offset to the image data array, just after the IFD definition
    ra.write(asBytes(273, (9, 4, offset + n_bytes_IFD)))
    # Write NextIFDOffset as 4 bytes
    offset += n_bytes_IFD + tags[279][2] # i.e. StripByteCounts: the size of the image data in number of bytes
    ra.writeInt(0 if img.dimension(2) - 1 == z else offset)
    # Write image plane
    # The long[] array doesn't necessarily end sharply at image plane boundaries
    # Therefore must copy plane into another, 2D ArrayImg of bit type
    ImgUtil.copy(ImgView.wrap(Views.hyperSlice(img, 2, z), None), plane_img)
    bb.rewind() # bring mark to zero
    bb.asLongBuffer().put(plane_array) # a LongBuffer view of the ByteBuffer, writes to the ByteBuffer
    ra.write(bb.array())
finally:
  ra.close()


# Now read the file back as a stack
slices = TIFFSlices(filepath, types={1: TIFFSlices.types[64][:2] + (BitType,)})
img = slices.asLazyCachedCellImg()
IL.wrap(img, "bit img").show()
