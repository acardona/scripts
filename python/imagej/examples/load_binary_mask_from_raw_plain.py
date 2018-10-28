from net.imglib2.img.array import ArrayImgs
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2 import KDTree, RealPoint
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.neighborsearch import NearestNeighborSearchOnKDTree
from net.imglib2.util import Intervals
from net.imglib2.algorithm.math.ImgMath import compute, mul
from net.imglib2.algorithm.math import ImgSource
from org.scijava.vecmath import Point3f
from ij3d import Image3DUniverse
from ij import ImagePlus, CompositeImage
from java.io import RandomAccessFile
from java.util.concurrent import Executors, Callable
from java.lang import Runtime
from itertools import imap
from functools import partial
from jarray import zeros, array
import operator, os

# Load 128x128x128 binary mask
# with zero for background and 1 for the mask

baseDir = "/home/albert/lab/scripts/data/cim.mcgill.ca-shape-benchmark/"

def readBinaryMaskImg(filepath, width, height, depth, header_size):
  ra = RandomAccessFile(filepath, 'r')
  try:
    ra.skipBytes(header_size)
    bytes = zeros(width * height * depth, 'b')
    ra.read(bytes)
    return ArrayImgs.unsignedBytes(bytes, [width, height, depth])
  finally:
    ra.close()

bird = readBinaryMaskImg(os.path.join(baseDir, "birdsIm/b21.im"), 128, 128, 128, 1024)
airplane = readBinaryMaskImg(os.path.join(baseDir, "airplanesIm/b14.im"), 128, 128, 128, 1024)

# Rotate bird: starts with posterior view, dorsal down
# Rotate 180 degrees around Y axis
birdY90 = Views.rotate(bird, 2, 0) # 90
birdY180 = Views.rotate(birdY90, 2, 0) # 90 again: 180

# Copy rotated bird into ArrayImg
dims = Intervals.dimensionsAsLongArray(birdY90)
img1 = compute(ImgSource(birdY180)).into(ArrayImgs.unsignedBytes(dims))

# Rotate airplane: starts with dorsal view, anterior down
# Set to: coronal view, but dorsal is still down
airplaneC = Views.rotate(airplane, 2, 1)
# Set to dorsal up: rotate 180 degrees
airplaneC90 = Views.rotate(airplaneC, 0, 1) # 90
airplaneC180 = Views.rotate(airplaneC90, 0, 1) # 90 again: 180

# Copy rotated airplace into ArrayImg
img2 = compute(ImgSource(airplaneC180)).into(ArrayImgs.unsignedBytes(dims))


# Find edges
def findEdgePixels(img):
  edge_pix = []
  zero = img.firstElement().createVariable()
  zero.setZero()
  imgE = Views.extendValue(img, zero)
  pos = zeros(img.numDimensions(), 'l')
  inc = partial(operator.add, 1)
  dec = partial(operator.add, -1)
  cursor = img.cursor()
  while cursor.hasNext():
    t = cursor.next()
    # A pixel is on the edge of the binary mask
    # if it has a non-zero value
    if 0 == t.getByte():
      continue
    # ... and its immediate neighbors ...
    cursor.localize(pos)
    minimum = array(imap(dec, pos), 'l') # map(dec, pos) also works, less performance
    maximum = array(imap(inc, pos), 'l') # map(inc, pos) also works, less performance
    neighborhood = Views.interval(imgE, minimum, maximum)
    # ... have at least one zero value:
    # Good performance: the "if x in <iterable>" approach stops upon finding the first x    
    if 0 in imap(UnsignedByteType.getByte, neighborhood):
      edge_pix.append(RealPoint(array(list(pos), 'f')))
  return edge_pix

# Generate interpolated image
def makeInterpolatedImage(img1, search1, img2, search2, weight):
  """ weight: float between 0 and 1 """
  img3 = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(img1))
  c1 = img1.cursor()
  c2 = img2.cursor()
  c3 = img3.cursor()
  while c3.hasNext():
    t1 = c1.next()
    t2 = c2.next()
    t3 = c3.next()
    sign1 = -1 if 0 == t1.get() else 1
    sign2 = -1 if 0 == t2.get() else 1
    search1.search(c1)
    search2.search(c2)
    value1 = sign1 * search1.getDistance() * (1 - weight)
    value2 = sign2 * search2.getDistance() * weight
    if value1 + value2 > 0:
      t3.setOne()
  return img3

def buildSearch(img):
  edge_pix = findEdgePixels(img)
  kdtree = KDTree(edge_pix, edge_pix)
  return NearestNeighborSearchOnKDTree(kdtree)

# A wrapper for concurrent execution
class Task(Callable):
  def __init__(self, fn, *args):
    self.fn = fn
    self.args = args
  def call(self):
    return self.fn(*self.args) # expand args

n_threads = Runtime.getRuntime().availableProcessors()
exe = Executors.newFixedThreadPool(n_threads)

try:
  # Concurrent construction of the search of the source and target images
  futures = [exe.submit(Task(buildSearch, img)) for img in [img1, img2]] # list: eager
  # Get each search, waiting until both are built
  search1, search2 = (f.get() for f in futures) # parentheses: a generator, lazy
  # Parallelize the creation of interpolation steps
  # Can't iterate decimals, so iterate from 2 to 10 every 2 and multiply by 0.1
  # And notice search instances are copied: they are stateful.
  futures = [exe.submit(Task(makeInterpolatedImage,
                             img1, search1.copy(), img2, search2.copy(), w * 0.1))
             for w in xrange(2, 10, 2)] # list: eager
  # Get each step, waiting until all are built
  steps = [f.get() for f in futures] # list: eager, for concatenation below in Views.stack
finally:
  # This 'finally' block executes even in the event of an error
  # guaranteeing that the executing threads will be shut down no matter what.
  exe.shutdown()


# ISSUE: Does not work with IntervalView from View.rotate,
# so img1 and img2 were copied into ArrayImg
# (The error would occur when iterating vol4d pixels beyond the first element in the 4th dimension.)
vol4d = Views.stack([img1] + steps + [img2])

# Convert 1 -> 255 for easier volume rendering in 3D Viewer
#compute(mul(vol4d, 255)).into(vol4d)
for t in Views.iterable(vol4d):
  if 0 != t.getByte():
    t.setReal(255)

# Construct an ij.VirtualStack from vol4d
virtualstack = IL.wrap(vol4d, "interpolations").getStack()
imp = ImagePlus("interpolations", virtualstack)
imp.setDimensions(1, vol4d.dimension(2), vol4d.dimension(3))
imp.setDisplayRange(0, 255)
# Show as a hyperstack with 4 dimensions, 1 channel
com = CompositeImage(imp, CompositeImage.GRAYSCALE)
com.show()

# Show rendered volumes in 4D viewer: 3D + time axis
univ = Image3DUniverse()
univ.show()
univ.addVoltex(com)
