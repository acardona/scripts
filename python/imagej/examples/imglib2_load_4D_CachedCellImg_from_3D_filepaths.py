import os, re
from jarray import array
# Must have enabled the "SiMView" update site from the Keller lab at Janelia
from org.janelia.simview.klb import KLB
from net.imglib2.img.cell import CellGrid, Cell
from net.imglib2.cache import CacheLoader
from net.imagej import ImgPlus
from net.imglib2.util import Intervals
from net.imglib2.cache.ref import SoftRefLoaderCache
from net.imglib2.img.basictypeaccess.volatiles.array import VolatileByteArray, VolatileShortArray,\
                                                            VolatileFloatArray, VolatileLongArray  
from net.imglib2.cache.img import ReadOnlyCachedCellImgFactory as Factory, \
                                  ReadOnlyCachedCellImgOptions as Options

source_dir = "/home/albert/dropbox/Dropbox (HHMI)/data/4D-series/"

# One 3D stack (in KLB format) per time point in this 4D volume
timepoint_paths = sorted(os.path.join(source_dir, filename)
                         for filename in os.listdir(source_dir)
                         if filename.endswith(".klb"))

pattern = re.compile("(Byte|Short|Float|Long)")

def extractArrayAccess(img):
  # KLB opens images as ImgPlus, which is an Img that wraps an ArrayImg
  if isinstance(img, ImgPlus):
    img = img.getImg()
  # Grab underlying array data access type, e.g. ByteArray
  access = img.update(None)
  # Replace, if needed, with a volatile access
  t = type(access).getSimpleName()
  if -1 != t.find("Volatile"): # e.g. VolatileByteAccess or DirtyVolatileByteAccess
    return access
  m = re.match(pattern, t) # to get the e.g. "Byte" part to compose the volatile class name
  # e.g. if data access type is ByteArray, return VolatileByteArray(bytes, True) 
  return globals()["Volatile%sArray" % m.group(1)](access.getCurrentStorageArray(), True)


class CellLoader(CacheLoader):
  klb = KLB.newInstance()
  def get(self, index):
    img = CellLoader.klb.readFull(timepoint_paths[index]).getImg()
    # Each cell has "1" as its dimension in the last axis (time)
    # and index as its min coordinate in the last axis (time)
    return Cell(Intervals.dimensionsAsIntArray(img) + array([1], 'i'),
                Intervals.minAsLongArray(img) + array([index], 'l'),
                extractArrayAccess(img))

# Load the first one, to read the dimensions and type (won't get cached unfortunately)
first = CellLoader.klb.readFull(timepoint_paths[0]).getImg()
pixel_type = first.randomAccess().get().createVariable()

# One cell per time point
dimensions = Intervals.dimensionsAsLongArray(first) + array([len(timepoint_paths)], 'l')
cell_dimensions = list(dimensions[0:-1]) + [1] # lists also work: will get mapped automatically to arrays

# The grid: how each independent stack fits into the whole continuous volume  
grid = CellGrid(dimensions, cell_dimensions)

# Create the image cache (one 3D image per time point),
# which can load any Cell when needed using CellLoader
loading_cache = SoftRefLoaderCache().withLoader(CellLoader()).unchecked()

# Create a CachedCellImg: a LazyCellImg that caches Cell instances with a SoftReference, for best performance
# and also self-regulating regarding the amount of memory to allocate to the cache.
cachedCellImg = Factory().createWithCacheLoader(
                  dimensions, pixel_type, loading_cache,
                  Options.options().volatileAccesses(True).cellDimensions(cell_dimensions))


# View in a virtual stack window
from net.imglib2.img.display.imagej import ImageJFunctions as IL

imp = IL.wrap(cachedCellImg, "4D volume")
imp.setDimensions(1, first.dimension(2), len(timepoint_paths))
imp.show()


# View in a BigDataViewer
from bdv.util import BdvFunctions, Bdv

bdv = BdvFunctions.show(cachedCellImg, "4D volume")
