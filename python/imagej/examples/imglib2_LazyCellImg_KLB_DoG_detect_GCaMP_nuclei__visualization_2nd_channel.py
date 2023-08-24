# Open a series of 3D stacks as a virtual 4D volume

from net.imglib2.img.cell import LazyCellImg, CellGrid, Cell
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.util import Intervals, IntervalIndexer
from ij import IJ
from net.imagej import ImgPlus

# Cache
import os
from collections import OrderedDict

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


# Detect and visualize nuclei as spheres in a second channel
from net.imglib2.algorithm.dog import DogDetection
from net.imglib2 import KDTree, RealPoint, RealRandomAccess, RealRandomAccessible
from net.imglib2.neighborsearch import NearestNeighborSearchOnKDTree
from net.imglib2.type.numeric.integer import UnsignedByteType

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

# A list of KDTree instances, one per timepoint
kdtrees = []

p = zeros(3, 'i')

# For every timepoint 3D volume, find DoG peaks and store in a KDTree
for i in xrange(vol4d.dimension(3)):
  # Slice index offset, 0-based
  zOffset = i * vol4d.dimension(2)
  # From the cache
  img = getStack(timepoint_paths[i])
  # or from the vol4d (same thing)
  #img = Views.hyperslice(vol4d, 3, i)
  dog = createDoG(img, calibration, sigmaSmaller, sigmaLarger, minPeakValue)
  # Peaks in floating-point, subpixel precision
  peaks = dog.getSubpixelPeaks()
  print "Found", len(peaks), " peaks in timepoint", i
  # KDTree for timepoint 'i'
  kdtrees.append(KDTree(peaks, peaks))

# TODO !!
  
