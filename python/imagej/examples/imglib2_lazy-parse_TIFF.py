from net.imglib2.img.cell import LazyCellImg, CellGrid, Cell
from net.imglib2.img.basictypeaccess.array import ByteArray, ShortArray, FloatArray
from net.imglib2.type.numeric.integer import UnsignedByteType, UnsignedShortType
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from jarray import zeros
from java.io import RandomAccessFile
from java.nio import ByteBuffer, ByteOrder
import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(sys.argv[0])), "IsoView-GCaMP"))
from lib.io import parse_TIFF_IFDs, read_TIFF_plane


class TIFFSlices(LazyCellImg.Get):
  def __init__(self, filepath):
    self.filepath = filepath
    self.IFDs = list(parse_TIFF_IFDs(filepath)) # the tags of each IFD
    self.types = {'b': ByteArray,
                  'h': ShortArray,
                  'f': FloatArray}
  def get(self, index):
    """ Assumes:
     - uncompressed image
     - one sample per pixel (one channel only)
    """
    IFD = self.IFDs[index]
    ra = RandomAccessFile(self.filepath, 'r')
    try:
      cell_dimensions = [IFD["width"], IFD["height"], 1]
      cell_position = [0, 0, index]
      pixels = read_TIFF_plane(ra, IFD)
      return Cell(cell_dimensions, cell_position, self.types[pixels.typecode](pixels))
    finally:
      ra.close()

filepath =  "/home/albert/Desktop/t2/bat-cochlea-volume.compressed-packbits.tif"

slices = TIFFSlices(filepath)

for IFD in slices.IFDs:
  print IFD


firstIFD = slices.IFDs[0]
print firstIFD
width, height = firstIFD["width"], firstIFD["height"]
bitDepth = firstIFD["bitDepth"]
pixel_type = { 8: UnsignedByteType,
              16: UnsignedShortType,
              32: FloatType}[bitDepth]
grid = CellGrid([width, height, len(slices.IFDs)],
                [width, height, 1])

# The whole TIFF file as one Cell per slice, independently loadable
imgTIFF = LazyCellImg(grid, pixel_type(), slices)

# The whole file
#imp = IL.wrap(imgTIFF, os.path.basename(filepath))
#imp.show()

# Pick only from slices 3 to 6
view_3_to_6 = Views.interval(imgTIFF, [0, 0, 0],
                                      [width -1, height -1, 5])
imp_3_to_6 = IL.wrap(view_3_to_6, "3 to 6")
imp_3_to_6.show()

# Pick only every 3rd slice
#view_every_3 = Views.subsample(imgTIFF, [1, 1, 3])
#imp_every_3 = IL.wrap(view_every_3, "every 3")
#imp_every_3.show()
