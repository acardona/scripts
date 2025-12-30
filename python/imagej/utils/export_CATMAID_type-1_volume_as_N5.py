import os, sys, math
from ij import IJ, ImagePlus
from ij.process import ByteProcessor
from net.imglib2.img.array import ArrayImgs
from net.imglib2.cache import CacheLoader
from net.imglib2.img.cell import CellGrid, Cell
from net.imglib2.img.display.imagej import ImageJVirtualStackUnsignedByte
from net.imglib2.cache.ref import BoundedSoftRefLoaderCache
from net.imglib2.cache.img import CachedCellImg, ReadOnlyCachedCellImgFactory, ReadOnlyCachedCellImgOptions
from net.imglib2.type.numeric.integer import UnsignedByteType
from java.awt import Toolkit
from java.net import URL

# Seymour ssTEM volume:
# width 28128
# height 31840
# depth 4841
# tile: 512x512 JPG and entirely black ones are omitted

volume_dimensions = [28128, 31840, 4841] # not a multile of 512, TODO correct for that.
cell_dimensions = [512, 512, 1]

class CATMAIDType4Loader(CacheLoader):
  def __init__(self, volume_dimensions, cell_dimensions, base_url="https://flyemdev.mrc-lmb.cam.ac.uk/L1-CNS-tiles", scale_level=0):
    self.volume_dimensions = volume_dimensions
    self.cell_dimensions = cell_dimensions
    self.row_length = int(math.ceil(volume_dimensions[0] / cell_dimensions[0]))
    self.col_length = int(math.ceil(volume_dimensions[1] / cell_dimensions[1]))
    self.n_plane_tiles = self.row_length * self.col_length
    self.base_url = base_url
    self.scale_level = scale_level
    self.black = ByteProcessor(*self.cell_dimensions[0:2])

  def createGrid(self):
  	return CellGrid([self.row_length, self.col_length, self.volume_dimensions[2]], self.cell_dimensions)

  def get(self, index):
    # index is of each tile. So to determine its coordinates:
    z = index % self.n_plane_tiles
    n = index - z * self.n_plane_tiles
    y = n % self.row_length
    x = n - y * self.row_length
    # Compose URL
    # URL like: 
    # https://flyemdev.mrc-lmb.cam.ac.uk/L1-CNS-tiles/1077/0/37_28.jpg
    # ... where:
    # 1077: section index (0-based)
    # 0: scale level
    # 37_28: y_z
    url = "%s/%i/%i/%i_%i.jpg" % (self.base_url, z, self.scale_level, y, z)
    # Fetch the image
    try:
      #imp = IJ.openImage(url) # shows an error when the URL doesn't exist
      imp = ImagePlus(url, Toolkit.getDefaultToolkit().createImage(URL(url)))
      if None == imp:
      	ip = self.black
      ip = imp.getProcessor()
      # Check dimensions
      if imp.getWidth() != self.cell_dimensions[0] or imp.getHeight() != self.cell_dimensions[1]:
        System.out.println("Wrong dimensions for image tile at:\n%s" % url)
        ip = self.black
      # JPEGs can load as RGB
      if imp.getType() != ImagePlus.GRAY8:
        ip = ip.convertToByte(False) # no scaling: as is
    except:
      # Most likely a non-existing tile (black tiles weren't stored). Return black tile.
      ip = self.black
    # Wrap pixels in an ArrayImg
    img = ArrayImgs.unsignedBytes(ip.getPixels(), [ip.getWidth(), ip.getHeight()])
    # Return Cell at the pixel-wise coordinate with the DataAccess pixel array
    return Cell(self.cell_dimensions,
                [x * self.cell_dimensions[0],
                 y * self.cell_dimensions[1],
                 z],
                img.update(None)) # get the underlying DataAccess


# Compose CachedCellImg
cell_loader = CATMAIDType4Loader(volume_dimensions, cell_dimensions)
cache = BoundedSoftRefLoaderCache(20000)
loading_cache = cache.withLoader(cell_loader).unchecked()
cachedCellImg = ReadOnlyCachedCellImgFactory().createWithCacheLoader(
                    volume_dimensions, UnsignedByteType(), loading_cache,
                    ReadOnlyCachedCellImgOptions.options().volatileAccesses(True).cellDimensions(cell_dimensions))

# Test it: let's see the stack
stack = ImageJVirtualStackUnsignedByte.wrap(cachedCellImg)
imp = ImagePlus("CATMAID Type 4 image mirror", stack)
imp.show()
