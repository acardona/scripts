# Albert Cardona 2018-10-22
# A method to generate interpolated masks between two 3D masks
# Should work with any number of dimensions.
# Based on the documentation found in class ini.trakem2.imaging.BinaryInterpolation2D
#
# Given two binary images of the same dimensions,
# generate an interpolated image that sits somewhere
# in between, as specified by the weight.
# 
# For each binary image, the edges are found
# and then each pixel is assigned a distance to the nearest edge.
# Inside, distance values are positive; outside, negative.
# Then both processed images are compared, and wherever
# the weighted sum is larger than zero, the result image
# gets a pixel set to true (or white, meaning inside).
# 
# A weight of zero means that the first image is not present at all
# in the interpolated image;
# a weight of one means that the first image is present exclusively.
# 
# The code was originally created by Johannes Schindelin
# in the VIB's vib.BinaryInterpolator class, for ij.ImagePlus,
# but the code below uses a completely different implementation
# strategy based on a KDTree for finding the edges of the masks.
#
#
# Note that a java-based implementation would be significantly faster.

from net.imglib2.img.array import ArrayImgs
from org.scijava.vecmath import Point3f
from jarray import zeros, array
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2 import KDTree, RealPoint, Cursor, RandomAccessible
from itertools import imap
from functools import partial
import operator
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.neighborsearch import NearestNeighborSearchOnKDTree
from net.imglib2.util import Intervals
from fiji.scripting import Weaver
from java.util import ArrayList
from net.imglib2.img import Img


# First 3D mask: a sphere
img1 = ArrayImgs.unsignedBytes([100, 100, 100])
p = zeros(3, 'l')
cursor = img1.cursor()
middle = Point3f(49.5,49.5, 49.5)
distance_sq = float(30 * 30)

w = Weaver.method("""
public void fillSphere(final Cursor cursor, final Point3f middle, final float distance_sq) {
  final long[] p = new long[cursor.numDimensions()];
  while (cursor.hasNext()) {
    cursor.fwd();
    cursor.localize(p);
    final UnsignedByteType t = (UnsignedByteType) cursor.get();
    if (middle.distanceSquared(new Point3f( (float)p[0], (float)p[1], (float)p[2] ) ) < distance_sq) {
      t.setOne();
    } else {
      t.setZero();
    }
  }
}

public void fillOnes(final Cursor cursor) {
  while (cursor.hasNext()) {
    ((UnsignedByteType)cursor.next()).setOne();
  }
}
""", [Cursor, Point3f, UnsignedByteType])

w.fillSphere(img1.cursor(), middle, distance_sq)

imp1 = IL.wrap(img1, "sphere")
imp1.setDisplayRange(0, 1)
imp1.show()


# Second 3D mask: three small cubes
img2 = ArrayImgs.unsignedBytes([100, 100, 100])

w.fillOnes(Views.interval(img2, [10, 10, 10], [29, 29, 29]).cursor())
w.fillOnes(Views.interval(img2, [70, 10, 70], [89, 29, 89]).cursor())
w.fillOnes(Views.interval(img2, [40, 70, 40], [59, 89, 59]).cursor())

imp2 = IL.wrap(img2, "cube")
imp2.setDisplayRange(0, 1)
imp2.show()

w2 = Weaver.method("""
public final ArrayList findEdgePixels(final Img img) {
  final ArrayList edge_pix = new ArrayList();
  final RandomAccessible imgE = Views.extendValue(img, ((UnsignedByteType)img.firstElement()).createVariable());
  final long[] pos = new long[img.numDimensions()];
  final long[] minimum = new long[pos.length],
               maximum = new long[pos.length];
  Cursor cursor = img.cursor();
  while (cursor.hasNext()) {
    final UnsignedByteType t = (UnsignedByteType) cursor.next();
    if (0 == t.getIntegerLong()) continue;
    cursor.localize(pos);
    for (int i=0; i<pos.length; ++i) minimum[i] = pos[i] - 1;
    for (int i=0; i<pos.length; ++i) maximum[i] = pos[i] + 1;
    final Cursor ce =  Views.interval(imgE, minimum, maximum).cursor();
    while (ce.hasNext()) {
      final UnsignedByteType tv = (UnsignedByteType) ce.next();
      if ( 0 == tv.getIntegerLong() ) {
        final float[] fp = new float[pos.length];
        for (int i=0; i<pos.length; ++i) fp[i] = (float) pos[i];
        edge_pix.add(new RealPoint(fp));
        break;
      }
    }
  }
  return edge_pix;
}

public final Img makeInterpolatedImage(final Img img1, final NearestNeighborSearchOnKDTree search1,
                                       final Img img2, final NearestNeighborSearchOnKDTree search2,
                                       final float weight) {
  final Img img3 = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(img1));
  final Cursor c1 = img1.cursor(),
               c2 = img2.cursor(),
               c3 = img3.cursor();
  while (c3.hasNext()) {
    final UnsignedByteType t1 = (UnsignedByteType) c1.next(),
                           t2 = (UnsignedByteType) c2.next(),
                           t3 = (UnsignedByteType) c3.next();
    final double sign1 = (0 == t1.get() ? -1 : 1),
                 sign2 = (0 == t2.get() ? -1 : 1);
    search1.search(c1);
    search2.search(c2);
    final double value1 = sign1 * search1.getDistance() * (1 - weight),
                 value2 = sign2 * search2.getDistance() * weight;
    if (value1 + value2 > 0) {
      t3.setOne();
    }
  }
  return img3;
}

""", [Img, Cursor, ArrayList, UnsignedByteType,
      Views, RandomAccessible, RealPoint,
      NearestNeighborSearchOnKDTree, ArrayImgs,
      Intervals])

edge_pix1 = w2.findEdgePixels(img1)
kdtree1 = KDTree(edge_pix1, edge_pix1)
search1 = NearestNeighborSearchOnKDTree(kdtree1)
edge_pix2 = w2.findEdgePixels(img2)
kdtree2 = KDTree(edge_pix2, edge_pix2)
search2 = NearestNeighborSearchOnKDTree(kdtree2)

steps = []
for weight in [x / 10.0 for x in xrange(2, 10, 2)]:
  steps.append(w2.makeInterpolatedImage(img1, search1, img2, search2, weight))

imp3 = IL.wrap(Views.stack([img1] + steps + [img2]), "interpolations")
imp3.setDimensions(1, img1.dimensions(3), len(steps))
imp3.setDisplayRange(0, 1)
imp3.show()
