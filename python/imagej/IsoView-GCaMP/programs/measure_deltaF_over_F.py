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
from net.imglib2.algorithm.math import ImgMath
from net.imglib2.view import Views
from java.lang import Double, System
from java.util.stream import StreamSupport
from java.util.function import Function, BinaryOperator
from ij import IJ
from itertools import imap


# Each subfolder contains 1000 TIFF stacks of the deltaF/F
# see subfolders therein starting with "t_"
srcLSM = "/home/albert/zstore1/data_WillBishop/"

srcCSV = "/home/albert/lab/projects/20231219_Nadine_Randel_measure_intensities_3D_4D/"

landmarksCSV = "landmarksLM-EMonly.csv"

# Calibration
pixelWidth = 406.5041 # nanometers per pixel
pixelHeight = 406.5041
pixelDepth = 1700

radius = 2000 # in nanometers
rX = radius / pixelWidth
rY = radius / pixelHeight
rZ = radius / pixelDepth

print "Radii used (in pixels): %f, %f, %f" % (rX, rY, rZ)

# List of lists of 3D coordinates in pixel space
points = []

# Read 3D coordinates (in nanometers) from the CSV file and calibrate them into pixel space
csvPath = os.path.join(srcCSV, landmarksCSV)
with open(csvPath, 'r') as f:
  reader = csv.reader(f, delimiter=',', quotechar="\"")
  header = reader.next() # skip first line
  for row in reader:
    # Columns at index 2, 3, 4 are the X, Y, Z of a coordinate in the LSM volume
    points.append([float(row[2]) / pixelWidth,
                   float(row[3]) / pixelHeight,
                   float(row[4]) / pixelDepth])
    print points[-1]

# List of OpenSphere ROIs, each centered on an integer-rounded 3D coordinate
# NOTE if the volume to measure is not a sphere, then use a openSuperEllipsoid instead of an openSphere.
# The GeomMasks.openSuperEllipsoid takes the point, the list of 3 radii, and an exponent of 2.
if rX == rY and rY == rZ:
  rois = [GeomMasks.openSphere(point, radius) for point in points]
else:
  rois = [GeomMasks.openSuperEllipsoid(point, [rX, rY, rZ], 2) for point in points]

# Find all time points, one 3D volume for each.
# Doesn't matter if they aren't sorted
timepoint_paths = []
for root, folders, filenames in os.walk(srcLSM):
  for filename in filenames:
    timepoint_paths.append(os.path.join(root, filename))


# Copied from lib.io
class ImageJLoader(CacheLoader):
  def get(self, i):
    System.out.println(i)
    imgPlanar = self.load(timepoint_paths[i])
    cell_dimensions = [imgPlanar.dimension(i) for i in xrange(imgPlanar.numDimensions())] + [1]
    # Copy to ArrayImg
    img = ImgMath.computeIntoArrayImg(ImgMath.img(imgPlanar))
    return Cell(cell_dimensions,
                [0, 0, 0, i],
                img.update(None))
  def load(self, path):
    return IL.wrap(IJ.openImage(path))

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
  primitiveType = primitiveType if primitiveType else pixelType().getNativeTypeFactory().getPrimitiveType()
  cache = SoftRefLoaderCache() if 0 == maxRefs else BoundedSoftRefLoaderCache(maxRefs)
  return CachedCellImg(CellGrid(volume_dimensions, cell_dimensions),
                       pixelType(),
                       cache.withLoader(loader),
                       ArrayDataAccessFactory.get(primitiveType, AccessFlags.setOf(AccessFlags.VOLATILE)))


# Open the first image as an Img
first = ImageJLoader().load(timepoint_paths[0])
volume_dimensions = [first.dimension(i) for i in xrange(first.numDimensions())] + [len(timepoint_paths)]
cell_dimensions = volume_dimensions[0:-1] + [1]
pixelType = type(first.createLinkedType()) # a class

# Work around jython limitations: can't use a static method as a Stream Function
class GetValue(Function):
  apply = pixelType.getDeclaredMethod("get").invoke # 'get' returns a floating-point number
  
class DoubleSum(BinaryOperator):
  apply = Double.sum

# Load 4D image, lazily and with a cache (even though the measurement is only done once)
img4D = lazyCachedCellImg(ImageJLoader(), volume_dimensions, cell_dimensions, pixelType)
imp4D = IL.show(img4D)

with open(os.path.join(srcCSV, "measurements.csv"), 'w') as f:
  # Write the header of the CSV file
  header = ["timepoint"] + ['"%f::%f::%f"' % (x,y,z) for (x,y,z) in points] # each point is a 3d list
  f.write(", ".join(header))
  f.write("\n")
  for t, path in enumerate(timepoint_paths):
    # Grab the 3D volume at timepoint t
    img3D = Views.hyperSlice(img4D, 3, t)
    # Assumes the ROI is small enough that the sum won't lose accuracy
    measurements = [StreamSupport.stream(Regions.sample(roi, img3D).spliterator(), False).map(GetValue()).reduce(0, DoubleSum())
                    for roi in rois]
    # Write a row to the CSV file
    f.write("%s, " % path)
    f.write(", ".join(imap(str, measurements)))
    f.write("\n")

    
      
  
  
  
  
  