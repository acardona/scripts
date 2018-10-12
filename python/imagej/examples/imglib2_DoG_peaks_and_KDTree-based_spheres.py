from ij import IJ
from ij.gui import PointRoi
from ij.measure import ResultsTable
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2.algorithm.dog import DogDetection
from jarray import zeros

# Load a greyscale single-channel image: the "Embryos" sample image
#imp = IJ.openImage("https://imagej.nih.gov/ij/images/embryos.jpg")
imp = IJ.getImage()
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

peaks = dog.getPeaks()

# Create a PointRoi from the DoG peaks, for visualization
roi = PointRoi(0, 0)
# A temporary array of integers, one per dimension the image has
p = zeros(img.numDimensions(), 'i')
# Load every peak as a point in the PointRoi
for peak in peaks:
  # Read peak coordinates into an array of integers
  peak.localize(p)
  roi.addPoint(imp, p[0], p[1])

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
  minC = [p[i] - sigmaSmaller for i in range(img.numDimensions())]
  maxC = [p[i] + sigmaSmaller for i in range(img.numDimensions())]
  # View the interval around the peak, as a flat iterable (like an array)
  fov = Views.interval(img, minC, maxC)
  # Compute sum of pixel intensity values of the interval
  # (The t is the Type that mediates access to the pixels, via its get* methods)
  s = sum(t.getInteger() for t in fov)
  # Add to results table
  table.incrementCounter()
  table.addValue("x", p[0])
  table.addValue("y", p[1])
  table.addValue("sum", s)

table.show("Embryo intensities at peaks")

# Now show an image with white circles for every embryo found
# We'll use a sparse image: an image that doesn't have a data point for each pixel
# but instead has a function for generating pixel data from the x,y coordinates of each embryo

from net.imglib2 import KDTree, RealPoint, RealRandomAccess, RealRandomAccessible
from net.imglib2.neighborsearch import NearestNeighborSearchOnKDTree
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.type.numeric.integer import UnsignedByteType
from java.util import AbstractList

inside = UnsignedByteType(255)
outside = UnsignedByteType(0)
radius = 30 # = sigmaLarger, where sigmaLarger is the radius of the embryo
centers = dog.getSubpixelPeaks() # in floating-point coordinates

class ConstantValueList(AbstractList):
  def __init__(self, constantvalue, count):
    self.constantvalue = constantvalue
    self.count = count
  def get(self, index):
    return self.constantvalue
  def size(self):
    return self.count

kdtree = KDTree(ConstantValueList(inside, len(centers)), centers)

class RRA(RealPoint, RealRandomAccess):
  def __init__(self, n_dimensions, kdtree, radius, inside, outside):
    super(RealPoint, self).__init__(n_dimensions)
    self.kdtree = kdtree
    self.search = NearestNeighborSearchOnKDTree(kdtree)
    self.radius = radius
    self.radius_sq = radius * radius
    self.inside = inside
    self.outside = outside
  def copyRealRandomAccess(self):
    return RRA(self.numDimensions(), self.kdtree, self.radius, self.inside, self.outside)
  def get(self):
    self.search.search(self) # hilariously symmetric
    if self.search.getSquareDistance() < self.radius_sq:
      return self.inside # Same: self.kdtree.getSampler().get()
    return self.outside

# Partial implementation, methods not needed were not implemented
class Circles(RealRandomAccessible):
  def realRandomAccess(self):
    return RRA(2, kdtree, radius, inside, outside)
  def numDimensions(self):
    return 2

# 'img' here is used as the Interval within which the RRA is defined
circles = Views.interval(Views.raster(Circles()), img)
IL.wrap(circles, "Circles").show()
