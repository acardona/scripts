from ij import CompositeImage
from ij.plugin import Raw
from ij.io import FileInfo
from net.imglib2.img.display.imagej import ImageJFunctions as IL

from net.imglib2.view import Views

from net.imglib2.img.array import ArrayImgs
from net.imglib2 import KDTree, RealPoint, Cursor, RandomAccessible
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.neighborsearch import NearestNeighborSearchOnKDTree
from net.imglib2.util import Intervals
from fiji.scripting import Weaver
from java.util import ArrayList
from net.imglib2.img import Img

# Load 128x128x128 binary mask
# with zero for background and 1 for the mask

fi = FileInfo()
fi.offset = 1024 # header size in bytes
fi.width = 128
fi.height = 128
fi.nImages = 128

baseDir = "/home/albert/lab/scripts/data/cim.mcgill.ca-shape-benchmark/"

bird = IL.wrap(Raw.open(baseDir + "/birdsIm/b21.im", fi))
airplane = IL.wrap(Raw.open(baseDir + "/airplanesIm/b14.im", fi))

# Rotate bird
# Starts with posterior view
# Rotate 180 degrees around Y axis
# Set to dorsal up: 180 degrees
birdY90 = Views.rotate(bird, 2, 0) # 90
birdY180 = Views.rotate(birdY90, 2, 0) # 90 again: 180

c1 = Views.iterable(birdY180).cursor()
img1 = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(birdY180))
c2 = img1.cursor()
while c2.hasNext():
  c2.next().set(c1.next())

# Rotate airplane
# Starts with dorsal view, anterior down
# Set to: coronal view, but dorsal is down
airplaneC = Views.rotate(airplane, 2, 1)
# Set to dorsal up: 180 degrees
airplaneC90 = Views.rotate(airplaneC, 0, 1) # 90
airplaneC180 = Views.rotate(airplaneC90, 0, 1) # 90 again: 180

c1 = Views.iterable(airplaneC180).cursor()
img2 = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(airplaneC180))
c2 = img2.cursor()
while c2.hasNext():
  c2.next().set(c1.next())


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

public void set1as255(final Cursor cursor) {
  while (cursor.hasNext()) {
    final UnsignedByteType t = (UnsignedByteType)cursor.next();
    if (1 == t.getIntegerLong()) t.setReal(255);
  }
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

vol4d = Views.stack([img1] + steps + [img2])

# Convert 1 -> 255
w2.set1as255(Views.iterable(vol4d).cursor())

imp3 = IL.wrap(vol4d, "interpolations")
imp3.setDimensions(1, vol4d.dimension(2), vol4d.dimension(3))
imp3.setDisplayRange(0, 1)
com = CompositeImage(imp3, CompositeImage.GRAYSCALE)
com.show()
