from mpicbg.ij.integral import BlockStatistics
from ij import IJ, ImagePlus

imp = IJ.getImage() # e.g. the blobs sample image

fp = imp.getProcessor().convertToFloat()
radius = 5

# Works only with FloatProcessor
bs = BlockStatistics(fp)

# Write the mean for the given radius, in place:
bs.mean(radius) # or bs.mean(radius, radius) for different radii in X, Y

blurred = ImagePlus("blurred", fp)
blurred.show()

# see also methods:
# bs.std(radius)
# bs.variance(radius)
# bs.sampleVariance(radius)