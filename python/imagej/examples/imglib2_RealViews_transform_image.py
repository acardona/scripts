from net.imglib2.realtransform import RealViews as RV
from net.imglib2.realtransform import Scale, AffineTransform
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from ij import IJ
from net.imglib2.view import Views
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from java.awt.geom import AffineTransform as Affine2D
from java.awt import Rectangle
from Jama import Matrix
from math import radians

# Load an image (of any dimensions)
imp = IJ.getImage()

# Access its pixel data from an ImgLib2 data structure: a RandomAccessibleInterval
img = IL.wrapReal(imp)

# View as an infinite image, with value zero outside of where the image is defined
#t = img.randomAccess().get().createVariable()
#t.set(0)
#imgE = Views.extendValue(img, t)
# Easier:
imgE = Views.extendZero(img)

# Or view mirroring the data beyond the edges
#imgE = Views.extendMirrorSingle(img)

# View the pixel data as a RealRandomAccessible with the help of an interpolator
imgR = Views.interpolate(imgE, NLinearInterpolatorFactory())

print type(imgR)
print dir(imgR)

# Obtain a view of the 2D image twice as big
s = [2.0 for d in range(img.numDimensions())] # as many 2.0 as dimensions the image has
bigger = RV.transform(imgR, Scale(s))

# Obtain a rasterized view (with integer coordinates for its pixels)
# NOT NEEDED
#imgRA = Views.raster(bigger)

# Define the interval we want to see: the original image, enlarged by 2X
# E.g. from 0 to 2*width, from 0 to 2*height, etc. for every dimension
# Notice the -1 in maxC: the interval is inclusive of the largest coordinate.
minC = [0 for d in range(img.numDimensions())]
maxC = [int(img.dimension(i) * scale) -1 for i, scale in enumerate(s)]
imgI = Views.interval(bigger, minC, maxC)

# Visualize the bigger view
imp2x = IL.wrap(imgI, imp.getTitle() + " - 2X") # an ImagePlus
imp2x.show()

# Define a rotation by +30º relative to the image center in the XY axes
# (not explicitly XY but the first two dimensions)
angle = radians(30)
rot2d = Affine2D.getRotateInstance(angle, img.dimension(0) / 2, img.dimension(1) / 2)
ndims = img.numDimensions()
matrix = Matrix(ndims, ndims + 1)
matrix.set(0, 0, rot2d.getScaleX())
matrix.set(0, 1, rot2d.getShearX())
matrix.set(0, ndims, rot2d.getTranslateX())
matrix.set(1, 0, rot2d.getShearY())
matrix.set(1, 1, rot2d.getScaleY())
matrix.set(1, ndims, rot2d.getTranslateY())
for i in range(2, img.numDimensions()):
  matrix.set(i, i, 1.0)

from pprint import pprint
pprint([list(row) for row in matrix.getArray()])

# Define a rotated view of the image
rotated = RV.transform(imgR, AffineTransform(matrix))

# View the image rotated, without enlarging the canvas
minC = [0 for i in range(img.numDimensions())]
maxC = [img.dimension(i) -1 for i in range(img.numDimensions())]
imgRot2d = IL.wrap(Views.interval(rotated, minC, maxC), imp.getTitle() + " - rot2d")
imgRot2d.show()

# View the image rotated, enlarging the canvas to fit it.
# We compute the bounds of the enlarged canvas by transforming a rectangle, 
# then define the interval min and max coordinates by subtracting 
# and adding as appropriate to exactly capture the complete rotated image.
bounds = rot2d.createTransformedShape(Rectangle(img.dimension(0), img.dimension(1))).getBounds()
minC[0] = (img.dimension(0) - bounds.width) / 2
minC[1] = (img.dimension(1) - bounds.height) / 2
maxC[0] += abs(minC[0]) -1
maxC[1] += abs(minC[1]) -1
imgRot2dFit = IL.wrap(Views.interval(rotated, minC, maxC), imp.getTitle() + " - rot2dFit")
imgRot2dFit.show()
