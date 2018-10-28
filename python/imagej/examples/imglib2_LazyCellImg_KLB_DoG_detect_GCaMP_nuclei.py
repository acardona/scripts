# Open a series of 3D stacks as a virtual 4D volume

from net.imglib2.img.cell import LazyCellImg, CellGrid, Cell
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.util import Intervals, IntervalIndexer
from ij import IJ
from net.imagej import ImgPlus

# Cache
import os
from collections import OrderedDict
from synchronize import make_synchronized

# VirtualStack
from net.imglib2.view import Views
from net.imglib2.img.array import ArrayImgs
from net.imglib2.img.basictypeaccess import ShortAccess
from ij import VirtualStack, ImagePlus, CompositeImage
from jarray import zeros, array


# Proxy
from ij.process import ShortProcessor

#from net.imglib2.algorithm.math import ImgSource
#from net.imglib2.algorithm.math.ImgMath import compute, into
from fiji.scripting import Weaver
from net.imglib2 import Cursor
from net.imglib2.type.numeric.integer import UnsignedShortType

from bdv.util import BdvFunctions

# Source directory containing a list of files, one per stack
src_dir = "/home/albert/lab/scripts/data/4D-series/" # "/mnt/ssd-512/MVD_Results/"

# Each timepoint is a path to a 3D stack file
timepoint_paths = sorted(os.path.join(src_dir, name) for name in os.listdir(src_dir) if name.endswith(".klb"))


# DEBUG:
timepoint_paths = timepoint_paths[0:2]



# Attempt to load the KLB library
# Must have enabled the "SiMView" update site from the Keller lab at Janelia
try:
  from org.janelia.simview.klb import KLB 
  klb = KLB.newInstance()
except:
  print "Could not import KLB file format reader."
  klb = None

class Memoize:
  def __init__(self, fn, maxsize=100):
    self.fn = fn
    self.m = OrderedDict()
    self.maxsize = maxsize
  @make_synchronized
  def __call__(self, key):
    o = self.m.get(key, None)
    if o:
      # Remove
      self.m.pop(key)
    else:
      # Invoke the memoized function
      o = self.fn(key)
    # Store
    self.m[key] = o
    # Trim cache
    if len(self.m) > self.maxsize:
      # Remove first entry (the oldest)
      self.m.popitem(last=False)
    return o

def openStack(filepath):
  if filepath.endswith(".klb"):
    return klb.readFull(filepath)
  else:
    return IJ.openImage(filepath)

getStack = Memoize(openStack)

class ProxyShortAccess(ShortAccess):
  def __init__(self, rai, dimensions):
    self.rai = rai
    self.dimensions = dimensions
    self.ra = rai.randomAccess()
    self.position = zeros(rai.numDimensions(), 'l')
    
  def getValue(self, index):
    IntervalIndexer.indexToPosition(index, self.dimensions, self.position)
    self.ra.setPosition(self.position)
    return self.ra.get().get() # a short int value if rai's type is UnsignedShortType
    
  def setValue(self, index, value):
    pass

def extractDataAccess(img, dimensions):
  if isinstance(img, ImgPlus):
    return extractDataAccess(img.getImg(), dimensions)
  try:
    return img.update(None)
  except:
    return ProxyShortAccess(img, dimensions)

def extractCalibration(img):
  # an ImgPlus has an axis(int dimension) method that returns a DefaultLinearAxis
  # which has relevant methods scale() and unit(), among others
  # See: https://javadoc.scijava.org/ImageJ/net/imagej/axis/DefaultLinearAxis.html
  if isinstance(img, ImgPlus):
    return [img.axis(d).scale() for d in img.numDimensions()]
  return [1.0 for d in img.numDimensions()]

class TimePointGet(LazyCellImg.Get):
  def __init__(self, timepoint_paths):
    self.timepoint_paths = timepoint_paths
    self.cell_dimensions = None
  def get(self, index):
    img = getStack(self.timepoint_paths[index])
    if not self.cell_dimensions:
      self.cell_dimensions = [img.dimension(0), img.dimension(1), img.dimension(2), 1]
    return Cell(self.cell_dimensions,
                [0, 0, 0, index],
                extractDataAccess(img, self.cell_dimensions))


first = getStack(timepoint_paths[0])
# One cell per time point
dimensions = [1 * first.dimension(0),
              1 * first.dimension(1),
              1 * first.dimension(2),
              len(timepoint_paths)]

grid = CellGrid(dimensions, dimensions[0:3] + [1])

vol4d = LazyCellImg(grid,
                    first.randomAccess().get().createVariable(),
                    TimePointGet(timepoint_paths))

print dimensions


# Visualization option 2:
# Create a 4D VirtualStack manually

# Need a fast way to copy pixel-wise
w = Weaver.method("""
  static public final void copy(final Cursor src, final Cursor tgt) {
    while (src.hasNext()) {
      src.fwd();
      tgt.fwd();
      final UnsignedShortType t1 = (UnsignedShortType) src.get(),
                              t2 = (UnsignedShortType) tgt.get();
      t2.set(t1.get());
    }
  }
""", [Cursor, UnsignedShortType])

class Stack4D(VirtualStack):
  def __init__(self, img4d):
    super(VirtualStack, self).__init__(img4d.dimension(0), img4d.dimension(1), img4d.dimension(2) * img4d.dimension(3))
    self.img4d = img4d
    self.dimensions = array([img4d.dimension(0), img4d.dimension(1)], 'l')
    
  def getPixels(self, n):
    # 'n' is 1-based
    aimg = ArrayImgs.unsignedShorts(self.dimensions[0:2])
    #computeInto(ImgSource(Views.hyperSlice(self.img4d, 2, n-1)), aimg)
    nZ = self.img4d.dimension(2)
    fixedT = Views.hyperSlice(self.img4d, 3, int((n-1) / nZ)) # Z blocks
    fixedZ = Views.hyperSlice(fixedT, 2, (n-1) % nZ)
    w.copy(fixedZ.cursor(), aimg.cursor())
    return aimg.update(None).getCurrentStorageArray()
    
  def getProcessor(self, n):
    return ShortProcessor(self.dimensions[0], self.dimensions[1], self.getPixels(n), None)


imp = ImagePlus("vol4d", Stack4D(vol4d))
nChannels = 1
nSlices = first.dimension(2)
nFrames = len(timepoint_paths)
imp.setDimensions(nChannels, nSlices, nFrames)
com = CompositeImage(imp, CompositeImage.GRAYSCALE)
com.show()


# Detect nuclei
from net.imglib2.algorithm.dog import DogDetection
from collections import defaultdict
from ij import ImageListener, ImagePlus
from ij.gui import PointRoi
from java.awt import Color
import sys

# Parameters for a Difference of Gaussian to detect nuclei positions
calibration = [1.0 for i in range(vol4d.numDimensions())] # no calibration: identity
sigmaSmaller = 2.5 # in pixels: a quarter of the radius of a neuron nuclei
sigmaLarger = 5  # pixels: half the radius of a neuron nuclei
minPeakValue = 100 # Maybe raise it to 120

def createDoG(img, calibration, sigmaSmaller, sigmaLarger, minPeakValue):
  # Fixed parameters
  extremaType = DogDetection.ExtremaType.MAXIMA
  normalizedMinPeakValue = False
  # Infinite img
  imgE = Views.extendMirrorSingle(img)
  # In the differece of gaussian peak detection, the img acts as the interval
  # within which to look for peaks. The processing is done on the infinite imgE.
  return DogDetection(imgE, img, calibration, sigmaLarger, sigmaSmaller,
    extremaType, minPeakValue, normalizedMinPeakValue)

def getDoGPeaks(timepoint_index, print_count=True):
  # From the cache
  img = getStack(timepoint_paths[timepoint_index])
  # or from the vol4d (same thing)
  #img = Views.hyperslice(vol4d, 3, i)
  dog = createDoG(img, calibration, sigmaSmaller, sigmaLarger, minPeakValue)
  peaks = dog.getSubpixelPeaks() # could also use getPeaks() in integer precision
  if print_count:
    print "Found", len(peaks), "peaks in timepoint", timepoint_index
  return peaks

# A map of timepoint indices and collections of DoG peaks in local 3D coordinates
nuclei_detections = {ti: getDoGPeaks(ti) for ti in xrange(vol4d.dimension(3))}

# Visualization 1: with a PointRoi for every vol4d stack slice,
#                  automatically updated when browsing through slices.

# Create a listener that, on slice change, updates the ROI
class PointRoiRefresher(ImageListener):
  def __init__(self, imp, nuclei_detections):
    self.imp = imp
    # A map of slice indices and 2D points, over the whole 4d volume
    self.nuclei = defaultdict(list)  # Any query returns at least an empty list
    p = zeros(3, 'f')
    for ti, peaks in nuclei_detections.iteritems():
      # Slice index offset, 0-based, for the whole timepoint 3D volume
      zOffset = ti * vol4d.dimension(2)
      for peak in peaks: # peaks are float arrays of length 3
        peak.localize(p)
        self.nuclei[zOffset + int(p[2])].append(p[0:2])
  def imageOpened(self, imp):
    pass
  def imageClosed(self, imp):
    if imp == self.imp:
      imp.removeImageListener(self)
  def imageUpdated(self, imp):
    if imp == self.imp:
      self.updatePointRoi()
  def updatePointRoi(self):
    # Surround with try/except to prevent blocking
    #   ImageJ's stack slice updater thread in case of error.
    try:
      # Update PointRoi
      self.imp.killRoi()
      points = self.nuclei[self.imp.getSlice() -1] # map 1-based slices to 0-based nuclei Z coords
      if 0 == len(points):
        IJ.log("No points for slice " + str(self.imp.getSlice()))
        return
      roi = PointRoi()
      # Style: large, red dots
      roi.setSize(4) # ranges 1-4
      roi.setPointType(2) # 2 is a dot (filled circle)
      roi.setFillColor(Color.red)
      roi.setStrokeColor(Color.red)
      # Add points
      for point in points: # points are floats
        roi.addPoint(self.imp, int(point[0]), int(point[1]))
      self.imp.setRoi(roi)
    except:
      IJ.error(sys.exc_info())

listener = PointRoiRefresher(com, nuclei_detections)
ImagePlus.addImageListener(listener)


# Visualization 2: with a 2nd channel where each each detection is painted as a sphere

from net.imglib2 import KDTree, RealPoint, RealRandomAccess, RealRandomAccessible, FinalInterval
from net.imglib2.neighborsearch import NearestNeighborSearchOnKDTree
from net.imglib2.type.numeric.integer import UnsignedShortType

# A KDTree is a data structure for fast lookup of e.g. neareast spatial coordinates
# Here, we create a KDTree for each timepoint 3D volume
# ('i' is the timepoint index
kdtrees = {i: KDTree(peaks, peaks) for i, peaks in nuclei_detections.iteritems()}

radius = 5.0 # pixels

inside = UnsignedShortType(255) # 'white'
outside = UnsignedShortType(0)  # 'black'

# The definition of one sphere in 3D space for every nuclei detection
class Spheres(RealPoint, RealRandomAccess):
  def __init__(self, kdtree, radius, inside, outside):
    super(RealPoint, self).__init__(3) # 3-dimensional
    self.search = NearestNeighborSearchOnKDTree(kdtree)
    self.radius = radius
    self.radius_squared = radius * radius # optimization for the search
    self.inside = inside
    self.outside = outside
  def copyRealRandomAccess(self):
    return Spheres(3, self.kdtree, self.radius, self.inside, self.outside)
  def get(self):
    self.search.search(self)
    if self.search.getSquareDistance() < self.radius_squared:
      return self.inside
    return self.outside


# Testing out a speed up: define the Spheres class in java
ws = Weaver.method("""
public final class Spheres extends RealPoint implements RealRandomAccess {
	private final KDTree kdtree;
	private final NearestNeighborSearchOnKDTree search;
	private final double radius,
	                     radius_squared;
	private final UnsignedShortType inside,
	                                outside;

	public Spheres(final KDTree kdtree,
	               final double radius,
	               final UnsignedShortType inside,
	               final UnsignedShortType outside)
	{
	    super(3); // 3 dimensions
		this.kdtree = kdtree;
		this.radius = radius;
		this.radius_squared = radius * radius;
		this.inside = inside;
		this.outside = outside;
		this.search = new NearestNeighborSearchOnKDTree(kdtree);
	}

	public final Spheres copyRealRandomAccess() { return copy(); }

	public final Spheres copy() {
		return new Spheres(this.kdtree, this.radius, this.inside, this.outside);
	}

	public final UnsignedShortType get() {
		this.search.search(this);
		if (this.search.getSquareDistance() < this.radius_squared) {
			return inside;
		}
		return outside;
	}
}

public final Spheres createSpheres(final KDTree kdtree,
                                   final double radius,
	                               final UnsignedShortType inside,
	                               final UnsignedShortType outside)
{
	return new Spheres(kdtree, radius, inside, outside);
}

""", [RealPoint, RealRandomAccess, KDTree, NearestNeighborSearchOnKDTree, UnsignedShortType])


# The RealRandomAccessible that wraps the Spheres, unbounded
# NOTE: partial implementation, unneeded methods were left unimplemented
# NOTE: args are "kdtree, radius, inside, outside", using the * shortcut
#       given that this class is merely a wrapper for the Spheres class
class SpheresData(RealRandomAccessible):
  def __init__(self, *args):
    self.args = args
  def realRandomAccess(self):
    # Performance improvement
    return ws.createSpheres(*self.args) # Arguments get unpacked from the args list
    #return Spheres(*self.args) # Arguments get unpacked from the args list
  def numDimensions(self):
    return 3

# A two color channel virtual stack:
# - odd slices: image data
# - even slices: spheres (nuclei detections)
class Stack4DTwoChannels(VirtualStack):
  def __init__(self, img4d, kdtrees):
    # The last coordinate, Z (number of slices), is the number of slices per timepoint 3D volume
    # times the number of timepoints, times the number of channels: two.
    super(VirtualStack, self).__init__(img4d.dimension(0), img4d.dimension(1),
                                       img4d.dimension(2) * img4d.dimension(3) * 2)
    self.img4d = img4d
    self.dimensions = array([img4d.dimension(0), img4d.dimension(1)], 'l')
    self.kdtrees = kdtrees
    self.dimensions3d = FinalInterval([img4d.dimension(0), img4d.dimension(1), img4d.dimension(2)])
    
  def getPixels(self, n):
    # 'n' is 1-based
    # Target 2D array img to copy data into
    aimg = ArrayImgs.unsignedShorts(self.dimensions[0:2])
    # The number of slices of the 3D volume of a single timepoint
    nZ = self.img4d.dimension(2)
    # The slice_index if there was a single channel
    slice_index = int((n-1) / 2) # 0-based, of the whole 4D series
    local_slice_index = slice_index % nZ # 0-based, of the timepoint 3D volume
    timepoint_index = int(slice_index / nZ) # Z blocks
    if 1 == n % 2:
      # Odd slice index: image channel
      fixedT = Views.hyperSlice(self.img4d, 3, timepoint_index)
      fixedZ = Views.hyperSlice(fixedT, 2, local_slice_index)
      w.copy(fixedZ.cursor(), aimg.cursor())
    else:
      # Even slice index: spheres channel
      sd = SpheresData(self.kdtrees[timepoint_index], radius, inside, outside)
      volume = Views.interval(Views.raster(sd), self.dimensions3d)
      plane = Views.hyperSlice(volume, 2, local_slice_index)
      w.copy(plane.cursor(), aimg.cursor())
    #
    return aimg.update(None).getCurrentStorageArray()
    
  def getProcessor(self, n):
    return ShortProcessor(self.dimensions[0], self.dimensions[1], self.getPixels(n), None)


imp2 = ImagePlus("vol4d - with nuclei channel", Stack4DTwoChannels(vol4d, kdtrees))
nChannels = 2
nSlices = vol4d.dimension(2) # Z dimension of each time point 3D volume
nFrames = len(timepoint_paths) # number of time points
# Test:
if nChannels * nSlices * nFrames == imp2.getStack().size():
  print "Dimensions are correct."
else:
  print "Mismatching dimensions!"
imp2.setDimensions(nChannels, nSlices, nFrames)
com2 = CompositeImage(imp2, CompositeImage.COMPOSITE)
com2.show()


# Visualization 3: two-channels with the BigDataViewer

from bdv.util import BdvFunctions, Bdv
from net.imglib2.view import Views
from net.imglib2 import FinalInterval

# Open a new BigDataViewer window with the 4D image data
bdv = BdvFunctions.show(vol4d, "vol4d")

# Create a bounded 3D volume view from a KDTree
def as3DVolume(kdtree, dimensions3d):
  sd = SpheresData(kdtree, radius, inside, outside)
  vol3d = Views.interval(Views.raster(sd), dimensions3d)
  return vol3d

# Define a 4D volume as a sequence of generative Spheres 3D volumes
dims3d = FinalInterval(map(vol4d.dimension, xrange(3)))
spheres4d = Views.stack([as3DVolume(kdtrees[ti], dims3d) for ti in sorted(kdtrees.iterkeys())])

BdvFunctions.show(spheres4d, "spheres4d", Bdv.options().addTo(bdv))


