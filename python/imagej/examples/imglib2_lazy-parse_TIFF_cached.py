from net.imglib2.cache import CacheLoader
from net.imglib2.type import PrimitiveType

from net.imglib2.img.cell import Cell
from net.imglib2.img.basictypeaccess.array import ByteArray, ShortArray, FloatArray
from net.imglib2.type.numeric.integer import UnsignedByteType, UnsignedShortType
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from jarray import zeros
from java.io import RandomAccessFile
import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(sys.argv[0])), "IsoView-GCaMP"))
from lib.io import parse_TIFF_IFDs, read_TIFF_plane, lazyCachedCellImg


class TIFFSlices(CacheLoader):
  """ Supports only UnsignedByteType, UnsignedShortType and FloatType. """
  types = { 8: (ByteArray, PrimitiveType.BYTE, UnsignedByteType),
           16: (ShortArray, PrimitiveType.SHORT, UnsignedShortType),
           32: (FloatArray, PrimitiveType.FLOAT, FloatType)}
  
  def __init__(self, filepath):
    self.filepath = filepath
    self.IFDs = list(parse_TIFF_IFDs(filepath)) # the tags of each IFD
    # Assumes all TIFF slices have the same dimensions and type
    self.cell_dimensions = [self.IFDs[0]["width"], self.IFDs[0]["height"], 1]
  
  def get(self, index):
    IFD = self.IFDs[index]
    ra = RandomAccessFile(self.filepath, 'r')
    try:
      cell_position = [0, 0, index]
      pixels = read_TIFF_plane(ra, IFD)
      access = TIFFSlices.types[IFD["bitDepth"]][0]
      return Cell(self.cell_dimensions, cell_position, access(pixels))
    finally:
      ra.close()
  
  def asLazyCachedCellImg(self):
    access, primitiveType, pixelType = TIFFSlices.types[self.IFDs[0]["bitDepth"]]
    return lazyCachedCellImg(self, self.cell_dimensions[:-1] + [len(self.IFDs)],
                             self.cell_dimensions, pixelType, primitiveType)
    

filepath =  "/home/albert/Desktop/t2/bat-cochlea-volume.compressed-packbits.tif"

# The whole TIFF file as one Cell per slice, independently loadable
slices = TIFFSlices(filepath)
imgLazyTIFF = slices.asLazyCachedCellImg()

# The whole file
#imp = IL.wrap(imgTIFF, os.path.basename(filepath))
#imp.show()

width, height, _ = slices.cell_dimensions

# Pick only from slices 3 to 6
view_3_to_6 = Views.interval(imgLazyTIFF, [0, 0, 0],
                                          [width -1, height -1, 5])
imp_3_to_6 = IL.wrap(view_3_to_6, "3 to 6")
imp_3_to_6.show()

# Pick only every 3rd slice
#view_every_3 = Views.subsample(imgTIFF, [1, 1, 3])
#imp_every_3 = IL.wrap(view_every_3, "every 3")
#imp_every_3.show()
