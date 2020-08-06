from net.imglib2.img.array import ArrayImgs
from org.scijava.vecmath import Point3f
from jarray import zeros, array
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2 import KDTree, RealPoint
from itertools import imap, izip
from functools import partial
import operator
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.neighborsearch import NearestNeighborSearchOnKDTree
from net.imglib2.util import Intervals
from ij import IJ
from net.imglib2.realtransform import RealViews, Scale
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory


img1 = IL.wrap(IJ.openImage("/home/albert/Desktop/bat-cochlea-volume.zip"))
img2 = IL.wrap(IJ.openImage("/home/albert/Desktop/mri-stack-mask.zip"))

# Make any non-zero pixel be 1
for t in img1:
  if 0 != t.getIntegerLong():
    t.setOne()

for t in img2:
  if 0 != t.getIntegerLong():
    t.setOne()


# Make both fit within the same window, centered

dims1 = Intervals.dimensionsAsLongArray(img1)
dims2 = Intervals.dimensionsAsLongArray(img2)
dims3 = [max(a, b) for a, b in izip(dims1, dims2)]

zero = UnsignedByteType(0)
img1E = Views.extendValue(img1, zero)
img2E = Views.extendValue(img2, zero)

img1M = Views.interval(img1E, [(dim1 - dim3) / 2 for dim1, dim3 in izip(dims1, dims3)],
                              [dim1 + (dim3 - dim1) / 2 -1 for dim1, dim3 in izip(dims1, dims3)])

img2M = Views.interval(img2E, [(dim2 - dim3) / 2 for dim2, dim3 in izip(dims2, dims3)],
                              [dim2 + (dim3 - dim2) / 2 -1 for dim2, dim3 in izip(dims2, dims3)])

IL.show(img1M, "img1M")
IL.show(img2M, "img2M")

# Scale by half (too slow otherwise)  -- ERROR: the smaller one (img1) doesn't remain centered.
s = [0.5 for d in xrange(img1.numDimensions())]
img1s = Views.interval(RealViews.transform(Views.interpolate(Views.extendValue(img1M, zero), NLinearInterpolatorFactory()), Scale(s)),
                       [0 for d in xrange(img1M.numDimensions())],
                       [int(img1M.dimension(d) / 2.0 + 0.5) -1 for d in xrange(img1M.numDimensions())])
img2s = Views.interval(RealViews.transform(Views.interpolate(Views.extendValue(img2M, zero), NLinearInterpolatorFactory()), Scale(s)),
                       [0 for d in xrange(img2M.numDimensions())],
                       [int(img2M.dimension(d) / 2.0 + 0.5) -1 for d in xrange(img2M.numDimensions())])

# simplify var names
img1M = img1s
img2M = img2s

# Create interpolates
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
    if 0 == t.getIntegerLong():
      continue
    # Sum neighbors of non-zero pixel: if any is zero, sum is less than 27
    # and we have found an edge pixel
    cursor.localize(pos)
    minimum = map(dec, pos)
    maximum = map(inc, pos) 
    box = Views.interval(imgE, minimum, maximum)
    if sum(imap(UnsignedByteType.getIntegerLong, box)) < 27:
      edge_pix.append(RealPoint(array(list(pos), 'f')))
  return edge_pix

# Generate interpolated image
def makeInterpolatedImage(img1, search1, img2, search2, weight):
  """ weight: float between 0 and 1 """
  img3 = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(img1))
  c1 = img1.cursor()
  c2 = img2.cursor()
  c3 = img3.cursor()
  pos = zeros(img1.numDimensions(), 'l')
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

edge_pix1 = findEdgePixels(img1M)
kdtree1 = KDTree(edge_pix1, edge_pix1)
search1 = NearestNeighborSearchOnKDTree(kdtree1)
edge_pix2 = findEdgePixels(img2M)
kdtree2 = KDTree(edge_pix2, edge_pix2)
search2 = NearestNeighborSearchOnKDTree(kdtree2)

steps = []
for weight in [0.2, 0.4, 0.6, 0.8]:
  steps.append(makeInterpolatedImage(img1M, search1, img2M, search2, weight))

img3 = Views.stack([img1M] + steps + [img2M])
imp3 = IL.wrap(img3, "interpolated " + str(weight))
imp3.setDisplayRange(0, 1)
imp3.show()           