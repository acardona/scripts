# I2K 2022 example script: illustrate use of ImgLib2 CellImg
# Albert Cardona 2022

import os
from net.imglib2.cache import CacheLoader
from net.imglib2.img.cell import Cell
from net.imglib2.img.basictypeaccess.array import ShortArray
from net.imglib2.img.cell import CellGrid
from net.imglib2.type.numeric.integer import UnsignedShortType
from net.imglib2.img.basictypeaccess import ArrayDataAccessFactory
from java.lang import Short
from net.imglib2.img.basictypeaccess import AccessFlags
from net.imglib2.cache.img import CachedCellImg
from net.imglib2.cache.ref import SoftRefLoaderCache
from ij import IJ
from net.imglib2.type import PrimitiveType
from net.imglib2.img.display.imagej import ImageJFunctions as IL



class Loader(CacheLoader):
  """ Load 2D images on demand from a list of file paths,
      returning each as a Cell instance. """
  def __init__(self, filepaths, access_type):
    """
       filepaths: a list of files to load, each one representing a 2D slice.
       access_type: a DataAccess subclass such as e.g., ByteArray, ShortArray, FloatArray
    """
    # assumes all filepaths lead to images of identical pixel type and dimensions
    self.filepaths = filepaths
    self.access_type = access_type
    
  def get(self, index):
    # Load one image: one slice of this virtual stack
    imp = IJ.openImage(self.filepaths[index])
    # If the pixel type was different than that of others, could be converted here
    #
    # If image is to be filtered prior to showing it, here is the place
    #
    # Wrap the image in an ImgLib2 Cell
    # Dimensions: one stack slice, so z=1
    cell_dimensions = [imp.getWidth(), imp.getHeight(), 1]
    # Position: at origin of coordinates for  X,Y and at index for Z
    cell_position = [0, 0, index]
    # Pixel DataAccess: wrap the pixel array
    access = self.access_type(imp.getProcessor().getPixels())
    # 
    return Cell(cell_dimensions, cell_position, access)


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



# A directory of images to load, each as a slice in a virtual stack
srcDir = "/home/albert/Desktop/t2/189/section189-images/"
filepaths = findFilePaths(srcDir, ".tif")

# A Loader that reads 16-bit images
loader = Loader(filepaths, ShortArray)
cache_loader = SoftRefLoaderCache().withLoader(loader)  # SoftReference

# Load the first image via the loader so that it's cached
# and read the dimensions
first = cache_loader.get(0)  # a Cell that wraps the ShortArray for the image pixels of the slice at index 0
width = first.dimension(0)
height = first.dimension(1)
depth = len(filepaths) # assumption: all files have the same dimensions and pixel type

volume_dimensions = [width, height, depth]
cell_dimensions = [width, height, 1] # just one image, one stack slice

# The layout of cells: in this case, each Cell is a stack slice
grid = CellGrid(volume_dimensions, cell_dimensions)

img = CachedCellImg(grid, # the data layout
                    UnsignedShortType(), # for 16-bit images, each with a short[] native arrays
                    cache_loader, # the loader, with a SoftReference cache
                    ArrayDataAccessFactory.get(PrimitiveType.SHORT, AccessFlags.setOf(AccessFlags.VOLATILE)))

IL.show(img, "Virtual stack: lazy-loading cached CellImg of a whole directory of images")









