# Albert Cardona 2018-10-22
# A method to generate interpolated masks between two 3D masks
# Should work with any number of dimensions.
# Based on the documentation found in class ini.trakem2.imaging.BinaryInterpolation2D
#
# Note that a java-based implementation would be significantly faster.

from net.imglib2.img.array import ArrayImgs
from org.scijava.vecmath import Point3f
from jarray import zeros, array
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2 import KDTree, RealPoint
from itertools import imap
from functools import partial
import operator
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.neighborsearch import NearestNeighborSearchOnKDTree
from net.imglib2.util import Intervals


# First 3D mask: a sphere
img1 = ArrayImgs.unsignedBytes([100, 100, 100])
p = zeros(3, 'l')
cursor = img1.cursor()
middle = Point3f(49.5,49.5, 49.5)
distance_sq = float(30 * 30)

while cursor.hasNext():
  cursor.fwd()
  cursor.localize(p)
  if middle.distanceSquared(Point3f(p[0], p[1], p[2])) < distance_sq:
    cursor.get().setOne()
  else:
    cursor.get().setZero()

imp1 = IL.wrap(img1, "sphere")
imp1.setDisplayRange(0, 1)
imp1.show()


# Second 3D mask: a cube
img2 = ArrayImgs.unsignedBytes([100, 100, 100])
for t in Views.interval(img2, [20, 20, 20], [80, 80, 80]):
  t.setOne()

imp2 = IL.wrap(img2, "cube")
imp2.setDisplayRange(0, 1)
imp2.show()

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
def makeInterpolatedImage(img1, img2, weight):
  """ weight: float between 0 and 1 """
  edge_pix1 = findEdgePixels(img1)
  kdtree1 = KDTree(edge_pix1, edge_pix1)
  search1 = NearestNeighborSearchOnKDTree(kdtree1)
  edge_pix2 = findEdgePixels(img2)
  kdtree2 = KDTree(edge_pix2, edge_pix2)
  search2 = NearestNeighborSearchOnKDTree(kdtree2)
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
    value1 = sign1 * search1.getDistance() * weight
    value2 = sign2 * search2.getDistance() * (1 - weight)
    if value1 + value2 > 0:
      t3.setOne()
  return img3

weight = 0.5
img3 = makeInterpolatedImage(img1, img2, weight)
imp3 = IL.wrap(img3, "interpolated " + str(weight))
imp3.setDisplayRange(0, 1)
imp3.show()