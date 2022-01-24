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

# Get this data set of 11 stacks at:
# https://www.dropbox.com/sh/dcp0coglw1ym6nb/AABVY8I1RenMq4kDN1RByLZTa?dl=0
source_dir = "/home/albert/lab/presentations/20201130_I2K_Janelia/data/"
series4D_dir = os.path.join(source_dir, "4D-series/")

# One 3D stack (in KLB format) per time point in this 4D volume
timepoint_paths = sorted(os.path.join(series4D_dir, filename)
                         for filename in os.listdir(series4D_dir)
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
imp.setDisplayRange(16, 510) # min and max
imp.show()


# View in a BigDataViewer
from bdv.util import BdvFunctions, Bdv
from bdv.tools import InitializeViewerState

bdv = BdvFunctions.show(cachedCellImg, "4D volume")
bdv.setDisplayRange(16, 510)




# In N5 format: *much* faster random access loading
# because of both concurrent loading and loading smaller chunks
# instead of entire timepoints.
# And KLB is extra slow because of its strong compression.
try:
  from org.janelia.saalfeldlab.n5.imglib2 import N5Utils
  from org.janelia.saalfeldlab.n5 import N5FSReader, N5FSWriter, GzipCompression, RawCompression
except:
  print "*** n5-imglib2 from github.com/saalfeldlab/n5-imglib2 not installed. ***"
from com.google.gson import GsonBuilder
from java.util.concurrent import Executors
from java.lang import Runtime

# The directory to store the N5 data.
n5path = os.path.join(source_dir, "n5")
# The name of the img data.
dataset_name = "4D series"
if not os.path.exists(n5path):
  # Create directory for storing the dataset in N5 format
  os.mkdir(n5path)
  # An array or list as long as dimensions has the img,
  # specifying how to chop up the img into pieces.
  blockSize = [128, 128, 128, 1] # each block is about 2 MB
  # Compression: 0 means none. 4 is sensible. Can go up to 9.
  # See java.util.zip.Deflater for details
  gzip_compression_level = 4
  # Threads: as many as CPU cores, for parallel writing
  exe = Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors())

  N5Utils.save(cachedCellImg, N5FSWriter(n5path, GsonBuilder()),
               dataset_name, blockSize,
               GzipCompression(gzip_compression_level) if gzip_compression_level > 0 else RawCompression(),
               exe)

  # The above waits until all jobs have run. Then:
  exe.shutdown()

# Interestingly:
# KLB format: 11 stacks, 407 MB total
# N5 format with GZIP compression level 4: 688 files, 584 MB total.

# Open the N5 dataset
imgN5 = N5Utils.open(N5FSReader(n5path, GsonBuilder()), dataset_name)

# ... as a virtual stack
impN5 = IL.wrap(imgN5, "4D volume - N5")
impN5.setDimensions(1, first.dimension(2), len(timepoint_paths))
impN5.setDisplayRange(16, 510) # min and max
impN5.show()

# ... in a BigDataViewer for arbitrary reslicing
bdvN5 = BdvFunctions.show(imgN5, "4D Volume - N5")
bdvN5.setDisplayRange(16, 510)

