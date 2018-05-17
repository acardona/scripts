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
from net.imglib2.algorithm.neighborhood import HyperSphereNeighborhood
from net.imglib2.algorithm.region.hypersphere import HyperSphere, HyperSphereCursor
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.img.array import ArrayImgFactory
from net.imglib2.img.display.imagej import ImageJFunctions
from net.imglib2.view import Views
from itertools import imap
from java.lang import System
from net.imglib2.roi import EllipseRegionOfInterest
from net.imglib2 import Point, RealPoint


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

# Measure mean intensity at every peak
sphereFactory = HyperSphereNeighborhood.factory()
radius = 2
intensities1 = []
copy2 = Views.extendValue(copy, FloatType(0))
ra = copy2.randomAccess()

t1 = System.currentTimeMillis()

for peak in peaks:
  sphere = sphereFactory.create([int(peak[0]), int(peak[1]), int(peak[2])], radius, ra)
  s = sum(imap(FloatType.getRealFloat, sphere.cursor()))
  intensities1.append(float(s) / sphere.size())

t2 = System.currentTimeMillis()

print "Elapsed time:", (t2 - t1), "ms"

#print intensities1

# Try now with HyperSphereCursor
hs = HyperSphere(copy2, Point(3), radius)
size = hs.size()
intensities2 = []
hsc = hs.cursor()

t3 = System.currentTimeMillis()

for peak in peaks:
  hsc.updateCenter([int(peak[0]), int(peak[1]), int(peak[2])])
  s = sum(imap(FloatType.getRealFloat, hsc))
  intensities2.append(float(s) / size)

t4 = System.currentTimeMillis()

print "Elapsed time:", (t4 - t3), "ms"

#print intensities2

# Try now with the deprecated ellipse
sphere = EllipseRegionOfInterest(RealPoint(3), [radius, radius, radius])
ii = sphere.getIterableIntervalOverROI(copy2)
size = ii.size()
intensities3 = []

t5 = System.currentTimeMillis()

for peak in peaks:
  sphere.setOrigin([int(peak[0]), int(peak[1]), int(peak[2])])
  s = sum(imap(FloatType.getRealFloat, ii.cursor()))
  intensities3.append(float(s) / size)

t6 = System.currentTimeMillis()

print "Elapsed time:", (t6 - t5), "ms"

#print intensities3

# Results: 2, 1 and 6 ms. Second option with HyperSphere is the winner. All show identical results.




# Convert the peaks into points in calibrated image space
#ps = []  
#for peak in peaks:  
#  p = Point3f(peak)  
#  p.scale(cal.pixelWidth * 1/scale2D)  
#  ps.append(p)

# Show the peaks as spheres in 3D, along with orthoslices:  
#univ = Image3DUniverse(512, 512)  
#univ.addIcospheres(ps, Color3f(1, 0, 0), 2, cell_diameter/2, "Cells").setLocked(True)  
#univ.addOrthoslice(imp).setLocked(True)  
#univ.show()