# Albert Cardona 2023-12-19
# Load a 4D stack and measure pixel intensity
# within spheres centered on a given list of 3D landmarks.
# Works as a standalone script for Fiji

from __future__ import with_statement
import sys, os, csv
from net.imglib2.roi.geom import GeomMasks
from net.imglib2.roi import Masks, Regions
from net.imglib2.cache.ref import SoftRefLoaderCache, BoundedSoftRefLoaderCache
from net.imglib2.cache import CacheLoader
from net.imglib2.cache.img import CachedCellImg
from net.imglib2.img.basictypeaccess import AccessFlags, ArrayDataAccessFactory
from net.imglib2.img.cell import CellGrid, Cell
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from java.lang import Float
from ij import IJ


# Each subfolder contains 1000 TIFF stacks of the deltaF/F
# see subfolders therein starting with "t_"
srcLSM = "/home/albert/zstore1/data_WillBishop/"

srcCSV = "/home/albert/lab/projects/20231219_Nadine_Randel_measure_intensities_3D_4D/"

radius = 2 # TODO choose a sensible radius
# NOTE if the volume to measure is not a sphere, then use a openSuperEllipsoid instead of an openSphere.
# The GeomMasks.openSuperEllipsoid takes the point, the list of 3 radii, and an exponent of 2.

# List of lists of 3D coordinates in floating-point precision
points = []

# Read 3D coordinates from CSV file
csvPath = os.path.join(srcCSV, "landmarksLM-EMonly.csv")
with open(csvPath, 'r') as f:
  reader = csv.reader(f, delimiter=',', quotechar="\"")
  header = reader.next() # skip first line
  for row in reader:
    # Columns at index 2, 3, 4 are the X, Y, Z of a coordinate in the LSM volume
    points.append(map(float, row[2:5]))
    print points[-1]
  
# List of OpenSphere ROIs, each centered on an integer-rounded 3D coordinate
rois = [GeomMasks.openSphere(point, radius) for point in points]

# Find all time points, one 3D volume for each.
# Doesn't matter if they aren't sorted
timepoint_paths = []
for root, folders, filenames in os.walk(src):
  for filename in filenames:
    timepoint_paths.append(os.path.join(root, filename))


# Copied from lib.io
class ImageJLoader(CacheLoader):
  def get(self, path):
    return IL.wrap(IJ.openImage(path))
  def load(self, path):
    return self.get(path)

# Copied from lib.io
def lazyCachedCellImg(loader, volume_dimensions, cell_dimensions, pixelType, primitiveType=None, maxRefs=0):
  """ Create a lazy CachedCellImg, backed by a SoftRefLoaderCache,
      which can be used to e.g. create the equivalent of ij.VirtualStack but with ImgLib2,
      with the added benefit of a cache based on SoftReference (i.e. no need to manage memory).

      loader: a CacheLoader that returns a single Cell for each index (like the Z index in a VirtualStack).
      volume_dimensions: a list of int or long numbers, with the last dimension
                         being the number of Cell instances (i.e. the number of file paths).
      cell_dimensions: a list of int or long numbers, whose last dimension is 1.
      pixelType: e.g. UnsignedByteType (a class)
      primitiveType: e.g. BYTE
      maxRefs: defaults to zero which means unbounded, that is, soft references may have been garbage collected
               but entries in the cache table are still around. When maxRefs larger > 0, then only that many references
               will be kept as entries by using a BoundedSoftRefLoaderCache.

      Returns a CachedCellImg.
  """
  primitiveType = primitiveType if primitiveType else pixelType.getNativeTypeFactory().getPrimitiveType()
  cache = SoftRefLoaderCache() if 0 == maxRefs else BoundedSoftRefLoaderCache(maxRefs)
  return CachedCellImg(CellGrid(volume_dimensions, cell_dimensions),
                       pixelType(),
                       cache.withLoader(loader),
                       ArrayDataAccessFactory.get(primitiveType, AccessFlags.setOf(AccessFlags.VOLATILE)))


# Open the first image
first = ImageJLoader().load(timepoint_paths[0])
volume_dimensions = [first.dimension(i) for i in xrange(first.numDimensions())] + [len(timepoint_paths)]
cell_dimensions = volume_dimensions[0:-1] + [1]
pixelType = type(first.createLinkedType()) # a class
get = pixelType.getDeclaredMethod("get")

# Load 4D image, lazily and with a cache (even though the measurement is only done once)
img4D = lazyCachedCellImg(ImageJLoader(), volume_dimensions, cell_dimensions, pixelType)
imp4D = IL.show(img4D)

with open(os.path.join(srcCSV, "measurements.csv"), 'w') as f:
  # Write the header of the CSV file
  header = ["timepoint"] + ['"%f::%f::%f"' % point for point in points] # each point is a 3d list
  f.write(", ".join(header))
  f.write("\n")
  for t in xrange(len(timepoint_paths))):
    # Grab the 3D volume at timepoint t
    img3D = Views.hyperSlice(img4D, 3, t)
    # Assumes the ROI is small enough that the sum won't lose accuracy
    measurements = [Regions.sample(roi, img3D).cursor().stream().reduce(0, Float.sum)
                    for roi in rois]
    # Write a row to the CSV file
    f.write("%i, " % t)
    f.write(", ".join(measurements))
    f.write("\n")

    
      
  
  
  
  
  