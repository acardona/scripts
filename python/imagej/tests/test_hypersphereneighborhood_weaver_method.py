# Load an image of the Drosophila larval fly brain and segment  
# the 5-micron diameter cells present in the red channel.  
  
from script.imglib.analysis import DoGPeaks  
from script.imglib.color import Red  
from script.imglib.algorithm import Scale2D  
from script.imglib.math import Compute  
from script.imglib import ImgLib  
#from ij3d import Image3DUniverse  
#from javax.vecmath import Color3f, Point3f  
from ij import IJ
from net.imglib2.algorithm.region.hypersphere import HyperSphere, HyperSphereCursor
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.img.array import ArrayImgFactory
from net.imglib2.img.display.imagej import ImageJFunctions
from net.imglib2.view import Views
from itertools import imap
from java.lang import System, Double
from net.imglib2 import Point, RealPoint, Cursor
from fiji.scripting import Weaver


cell_diameter = 5  # in microns  
minPeak = 40 # The minimum intensity for a peak to be considered so.  
imp = IJ.getImage() #IJ.openImage("http://pacific.mpi-cbg.de/samples/first-instar-brain.zip")

# Scale the X,Y axis down to isotropy with the Z axis  
cal = imp.getCalibration()
scale2D = cal.pixelWidth / cal.pixelDepth  
iso = Compute.inFloats(Scale2D(Red(ImgLib.wrap(imp)), scale2D))
#ImgLib.wrap(iso).show()

# Find peaks by difference of Gaussian  
sigma = (cell_diameter  / cal.pixelWidth) * scale2D  
peaks = DoGPeaks(iso, sigma, sigma * 0.5, minPeak, 1)  
print "Found", len(peaks), "peaks"

# Copy ImgLib1 iso image into ImgLib2 copy image
copy = ArrayImgFactory().create([iso.getDimension(0), iso.getDimension(1), iso.getDimension(2)], FloatType())
c1 = iso.createCursor()
c2 = copy.cursor()
while c1.hasNext():
  c1.fwd()
  c2.fwd()
  c2.get().set(c1.getType().getRealFloat())

#ImageJFunctions.show(copy)

radius = 2
copy2 = Views.extendValue(copy, FloatType(0))

# Measure mean intensity at every peak
hs = HyperSphere(copy2, Point(3), radius)
size = hs.size()
intensities2 = []
hsc = hs.cursor()

t1 = System.currentTimeMillis()

for i in xrange(100):
  for peak in peaks:
    hsc.updateCenter([int(peak[0]), int(peak[1]), int(peak[2])])
    s = sum(imap(FloatType.getRealFloat, hsc)) # ~1.5x faster than for t in hsc: s += t.getRealFloat
    #intensities2.append(float(s) / size)

t2 = System.currentTimeMillis()

print "Elapsed time:", (t2 - t1), "ms"

o = Weaver.method("""
  static public double sum(final HyperSphereCursor<FloatType> hsc) {
    double sum = 0;
    while (hsc.hasNext()) {
  	  hsc.fwd();
  	  sum += hsc.get().getRealFloat();
    }
    return sum;
  }
  """,
  [FloatType, HyperSphereCursor], True)

t3 = System.currentTimeMillis()

for i in xrange(100):
  for peak in peaks:
    hsc.updateCenter([int(peak[0]), int(peak[1]), int(peak[2])])
    s = o.sum(hsc)
    #intensities2.append(float(s) / size)

t4 = System.currentTimeMillis()

print "Elapsed time:", (t4 - t3), "ms"

# RESULT: the Weaver.inline version runs 2x to 6x faster
