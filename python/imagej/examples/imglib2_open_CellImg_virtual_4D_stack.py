# Open a series of 3D stacks as a virtual 4D volume

from net.imglib2.img.cell import LazyCellImg, CellGrid, Cell
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2.util import Intervals, IntervalIndexer
from net.imglib2.img.basictypeaccess import ShortAccess
from net.imglib2 import Cursor
from net.imglib2.type.numeric.integer import UnsignedShortType
from net.imglib2.img.array import ArrayImgs
from ij import IJ, VirtualStack, ImagePlus, CompositeImage
from ij.process import ShortProcessor
from jarray import zeros, array
import os
from collections import OrderedDict
from net.imagej import ImgPlus
#from net.imglib2.algorithm.math import ImgSource
#from net.imglib2.algorithm.math.ImgMath import compute, into
from fiji.scripting import Weaver

# Source directory containing a list of files, one per stack
src_dir = "/mnt/ssd-512/MVD_Results/"

# Each timepoint is a path to a 3D stack file
timepoint_paths = sorted(os.path.join(src_dir, name) for name in os.listdir(src_dir) if name.endswith(".klb"))

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

class TimePointGet(LazyCellImg.Get):
  def __init__(self, timepoint_paths):
    self.timepoint_paths = timepoint_paths
    self.cell_dimensions = None
  def get(self, index):
    img = getStack(self.timepoint_paths[index])
    if not self.cell_dimensions:
      self.cell_dimensions = Intervals.dimensionsAsIntArray(img)
    return Cell(self.cell_dimensions,
                [0, 0, index * self.cell_dimensions[2]],
                extractDataAccess(img, self.cell_dimensions))


first = getStack(timepoint_paths[0])
# One cell per time point
dimensions = [1 * first.dimension(0),
              1 * first.dimension(1),
              len(timepoint_paths) * first.dimension(2)]

grid = CellGrid(dimensions, dimensions[0:2] + [first.dimension(2)])

vol4d = LazyCellImg(grid,
                    first.randomAccess().get().createVariable(),
                    TimePointGet(timepoint_paths))

print dimensions

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
    super(VirtualStack, self).__init__(img4d.dimension(0), img4d.dimension(1), img4d.dimension(2))
    self.img4d = img4d
    self.dimensions = array([img4d.dimension(0), img4d.dimension(1)], 'l')
    
  def getPixels(self, n):
    # 'n' is 1-based
    aimg = ArrayImgs.unsignedShorts(self.dimensions)
    #computeInto(ImgSource(Views.hyperSlice(self.img4d, 2, n-1)), aimg)
    w.copy(Views.hyperSlice(self.img4d, 2, n-1).cursor(), aimg.cursor())
    return aimg.update(None).getCurrentStorageArray()
    
  def getProcessor(self, n):
    return ShortProcessor(self.dimensions[0], self.dimensions[1], self.getPixels(n), None)


#IL.wrap(vol4d, "Volume 4D").show()

imp = ImagePlus("vol4d", Stack4D(vol4d))
imp.setDimensions(1, first.dimension(2), len(timepoint_paths))
com = CompositeImage(imp, CompositeImage.GRAYSCALE)
com.show()



