from __future__ import with_statement
from ij import IJ
from ij.gui import PointRoi
from ij.measure import ResultsTable
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2.algorithm.dog import DogDetection
from jarray import zeros
from net.imglib2.roi.geom import GeomMasks
from net.imglib2.roi import Masks, Regions
from net.imglib2.util import Intervals
from math import sqrt, pi

# Load a greyscale single-channel image: the "Embryos" sample image
imp = IJ.getImage() # IJ.openImage("https://imagej.nih.gov/ij/images/embryos.jpg")
# Convert it to 8-bit
IJ.run(imp, "8-bit", "")

# Access its pixel data from an ImgLib2 data structure: a RandomAccessibleInterval
img = IL.wrapReal(imp)

# View as an infinite image, mirrored at the edges which is ideal for Gaussians
imgE = Views.extendMirrorSingle(img)

# Parameters for a Difference of Gaussian to detect embryo positions
calibration = [1.0 for i in range(img.numDimensions())] # no calibration: identity
sigmaSmaller = 15 # in pixels: a quarter of the radius of an embryo
sigmaLarger = 30  # pixels: half the radius of an embryo
extremaType = DogDetection.ExtremaType.MAXIMA
minPeakValue = 10
normalizedMinPeakValue = False

# In the differece of gaussian peak detection, the img acts as the interval
# within which to look for peaks. The processing is done on the infinite imgE.
dog = DogDetection(imgE, img, calibration, sigmaSmaller, sigmaLarger,
  extremaType, minPeakValue, normalizedMinPeakValue)

peaks = dog.getSubpixelPeaks()

# Create a PointRoi from the DoG peaks, for visualization
roi = PointRoi(0, 0)
# A temporary array of integers, one per dimension the image has
p = zeros(img.numDimensions(), 'd')
# Load every peak as a point in the PointRoi
for peak in peaks:
  # Read peak coordinates into an array of integers
  peak.localize(p)
  roi.addPoint(imp, int(p[0]), int(p[1]))

imp.setRoi(roi)

# Now, iterate each peak, defining a small interval centered at each peak,
# and measure the sum of total pixel intensity,
# and display the results in an ImageJ ResultTable.
table = ResultsTable()

for peak in peaks:
  # Read peak coordinates into an array of integers
  peak.localize(p)
  # Define limits of the interval around the peak:
  # (sigmaSmaller is half the radius of the embryo)
  minC = [int(p[i] - sigmaSmaller) for i in xrange(img.numDimensions())]
  maxC = [int(p[i] + sigmaSmaller) for i in xrange(img.numDimensions())]
  # View the interval around the peak, as a flat iterable (like an array)
  square = Views.flatIterable(Views.zeroMin(Views.interval(img, minC, maxC)))
  s1 = sum(t.getInteger() for t in square)
  area1 = Intervals.numElements(square)
  # Use a sphere instead
  radius = sqrt(area1 / pi) # same area for both
  print sigmaSmaller, radius
  circle = Masks.toIterableRegion(GeomMasks.closedSphere(p, radius))
  s2 = sum(t.getInteger() for t in Regions.sample(circle, imgE))
  area2 = Intervals.numElements(circle)

  print area1, area2
  
  # Compute sum of pixel intensity values of the interval
  # (The t is the Type that mediates access to the pixels, via its get* methods)
  
  # Add to results table
  table.incrementCounter()
  table.addValue("x", p[0])
  table.addValue("y", p[1])
  table.addValue("avg square", float(s1) / area1)
  table.addValue("avg circle", float(s2) / area2)

table.show("Embryo intensities at peaks")