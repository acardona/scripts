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
# in the VIB's vib.BinaryInterpolator class, for ij.ImagePlus.
#
#
# Note that a java-based implementation would be significantly faster.

from net.imglib2.img.array import ArrayImgs
from org.scijava.vecmath import Point3f
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2.type.numeric.integer import UnsignedByteType
from jarray import zeros
from net.imglib2.algorithm.morphology.distance import DistanceTransform


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


# Second 3D mask: three small cubes
img2 = ArrayImgs.unsignedBytes([100, 100, 100])
for t in Views.interval(img2, [10, 10, 10], [29, 29, 29]):
  t.setOne()
for t in Views.interval(img2, [70, 10, 70], [89, 29, 89]):
  t.setOne()
for t in Views.interval(img2, [40, 70, 40], [59, 89, 59]):
  t.setOne()

imp2 = IL.wrap(img2, "cube")
imp2.setDisplayRange(0, 1)
imp2.show()


steps = []
for weight in [0.2, 0.4, 0.6, 0.8]:
  interpolated = ArrayImgs.unsignedBytes([100, 100, 100])
  DistanceTransform.binaryTransform(img1, interpolated, img2, DistanceTransform.DISTANCE_TYPE.EUCLIDIAN, [weight for d in xrange(img1.numDimensions())])
  steps.append(interpolated)

imp3 = IL.wrap(Views.stack([img1] + steps + [img2]), "interpolations")
imp3.setDisplayRange(0, 1)
imp3.show()
