import sys
from itertools import product, repeat
from net.imglib2.realtransform import RealViews as RV
from net.imglib2.realtransform import AffineTransform3D
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from ij import IJ
from net.imglib2.view import Views
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.util import Intervals
from math import radians, floor, ceil
from jarray import zeros
from pprint import pprint


# Load an image (of any dimensions)
imp = IJ.getImage()

# Access its pixel data as an ImgLib2 RandomAccessibleInterval
img = IL.wrapReal(imp)

# View as an infinite image, with value zero beyond the image edges
imgE = Views.extendZero(img)

# View the pixel data as a RealRandomAccessible
# (that is, accessible with sub-pixel precision)
# by using an interpolator
imgR = Views.interpolate(imgE, NLinearInterpolatorFactory())

# Define a rotation by +30 degrees relative to the image center in the XY axes
angle = radians(30)
toCenter = AffineTransform3D()
cx = img.dimension(0) / 2.0  # X axis
cy = img.dimension(1) / 2.0  # Y axis
toCenter.setTranslation(-cx, -cy, 0.0) # no translation in the Z axis
rotation = AffineTransform3D()
# Step 1: place origin of rotation at the center of the image
rotation.preConcatenate(toCenter)
# Step 2: rotate around the Z axis
rotation.rotate(2, angle)  # 2 is the Z axis, or 3rd dimension
# Step 3: undo translation to the center
rotation.preConcatenate(toCenter.inverse()) # undo translation to the center

# Define a rotated view of the image
rotated = RV.transform(imgR, rotation)

# View the image rotated, without enlarging the canvas
# so we define the interval (here, the field of view of an otherwise infinite image)
# as the original image dimensions by using "img", which in itself is an Interval.
imgRot2d = IL.wrap(Views.interval(rotated, img), imp.getTitle() + " - rot2d")
imgRot2d.show()

# View the image rotated, enlarging the interval to fit it.
# (This is akin to enlarging the canvas.)

# We define each corner of the nth-dimensional volume as a combination,
# namely the 'product' (think nested loop) of the pairs of possible values
# that each dimension can take in every corner coordinate, zipping each
# with the value zero (hence the repeat(0) to provide as many as necessary),
# and then unpacking the list of pairs by using the * in front of 'zip'
# so that 'product' receives the pairs as arguments rather than a list of pairs.
# Then we apply the transform to each corner, reading out the transformed coordinates
# by using the 'transformed' float array.

# We compute the bounds by, for every corner, checking if the floor of each dimension
# of a corner coordinate is smaller than the previously found minimum value,
# and by checking if the ceil of each corner coordinate is larger than the
# previously found value, packing the new pair of minimum and maximum values
# into the list of pairs that is 'bounds'.

# Notice the min coordinates can have negative values, as the rotated image
# has pixels now somewhere to the left and up from the top-left 0,0,0 origin
# of coordinates. That's why we use Views.zeroMin, to ensure that downstream
# uses of the transformed image see it as fitting within bounds that start at 0,0,0.

bounds = repeat((sys.maxint, 0)) # initial upper- and lower-bound values for min, max to compare against
transformed = zeros(img.numDimensions(), 'f')

for corner in product(*zip(repeat(0), Intervals.maxAsLongArray(img))):
  rotation.apply(corner, transformed)
  bounds = [(min(vmin, int(floor(v))), max(vmax, int(ceil(v))))
            for (vmin, vmax), v in zip(bounds, transformed)]

minC, maxC = map(list, zip(*bounds)) # transpose list of lists
imgRot2dFit = IL.wrap(Views.zeroMin(Views.interval(rotated, minC, maxC)),
  imp.getTitle() + " - rot2dFit")
imgRot2dFit.show()

matrix = rotation.getRowPackedCopy()
pprint([list(matrix[i:i+4]) for i in xrange(0, 12, 4)])
