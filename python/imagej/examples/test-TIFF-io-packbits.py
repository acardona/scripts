import sys, os, tempfile
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import parse_TIFF_IFDs, unpackBits2
from jarray import zeros, array
from java.io import RandomAccessFile
from ij import IJ, ImagePlus
from ij.process import ByteProcessor
from ij.io import ImageReader, FileInfo
from net.sf.ij.jaiio import JAIWriter
from com.sun.media.jai.codec import TIFFEncodeParam
from java.util import Arrays

filepath = os.path.join(tempfile.gettempdir(), "test-packbits.tif")

# Write a test TIFF packbits-compressed image of known pixel values
source_bytes = array([0, 0, 0, 42, 42, 42, 42, 89,
                      20, 20, 20, 20, 20, 20, 20, 20], 'b')
imp = ImagePlus("test-packbits", ByteProcessor(16, 1, source_bytes, None))
writer = JAIWriter()
writer.setFormatName("tiff")
# See doc: https://download.java.net/media/jai/javadoc/1.1.3/jai-apidocs/com/sun/media/jai/codec/TIFFEncodeParam.html
param = TIFFEncodeParam()
param.setCompression(TIFFEncodeParam.COMPRESSION_PACKBITS)
writer.setImageEncodeParam(param)
writer.write(filepath, imp)


# Parse the test file
IFDs = list(parse_TIFF_IFDs(filepath)) # the tags of each IFD

firstIFD = IFDs[0]
print firstIFD

ra = RandomAccessFile(filepath, 'r')
try:
  # Read the image plane, compressed with packbits
  bytes_packedbits = zeros(sum(firstIFD["StripByteCounts"]), 'b')
  index = 0
  for strip_offset, strip_length in zip(firstIFD["StripOffsets"], firstIFD["StripByteCounts"]):
    ra.seek(strip_offset)
    ra.read(bytes_packedbits, index, strip_length)
    index += strip_length
  print "Compressed:", bytes_packedbits
  # unpack
  bytes1 = unpackBits2(bytes_packedbits, firstIFD)
  bytes2 = unpackBits2(bytes_packedbits, firstIFD, use_imagereader=True)
  print "Decompressed jython:", bytes1
  print "Decompressed imagej:", bytes2
  # Check:
  if 0 == sum(a - b for a, b in zip(source_bytes, bytes1)):
    print "Image decompressed successfully by jython."
  if 0 == sum(a - b for a, b in zip(source_bytes, bytes2)):
    print "Image decompressed successfully by imagej."
finally:
  ra.close()
