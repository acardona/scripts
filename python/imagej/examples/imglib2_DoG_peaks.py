from ij import IJ
from ij.gui import PointRoi
from ij.measure import ResultsTable
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2.algorithm.dog import DogDetection
from jarray import zeros

# Load a greyscale single-channel image (of any dimensions)
imp = IJ.getImage()

# Access its pixel data from an ImgLib2 data structure: a RandomAccessibleInterval
img = IL.wrapReal(imp)

# View as an infinite image, mirrored at the edges which is ideal for Gaussians
imgE = Views.extendMirrorSingle(img)

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
p = zeros(img.numDimensions(), 'i')
for peak in peaks:
  # Read peak coordinates into an array of integers
  peak.localize(p)
  roi.addPoint(imp, p[0], p[1])

imp.setRoi(roi)

# Now, iterate each peak, defining a small interval centered at each peak,
# and measure the sum of total pixel intensity.
table = ResultsTable()

for peak in peaks:
  # Read peak coordinates into an array of integers
  peak.localize(p)
  # Define limits of the interval around the peak.
  # sigmaSmaller is half the radius of the embryo
  minC = [p[i] - sigmaSmaller for i in range(img.numDimensions())]
  maxC = [p[i] + sigmaSmaller for i in range(img.numDimensions())]
  # View the interval around the peak, as a flat iterable (like an array)
  fov = Views.flatIterable(Views.interval(img, minC, maxC))
  # Compute sum of pixel intensity values of the interval
  # (The t is the Type that gates access to the pixels, via its get* methods)
  s = sum(t.getInteger() for t in fov)
  # Add to results table
  table.incrementCounter()
  table.addValue("x", p[0])
  table.addValue("y", p[1])
  table.addValue("sum", s)

table.show("Embryo intensities at peaks")