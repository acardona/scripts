from mpicbg.models import PointMatch, Point
from ij import IJ, ImagePlus
from ij.process import FloatProcessor, ImageProcessor
from jarray import array, zeros
from jitk.spline import ThinPlateR2LogRSplineKernelTransform
from java.util import ArrayList
from ij.gui import Overlay, Line, Arrow
from java.lang.reflect.Array import newInstance as newArray
from java.lang import Double
from ij.process import ShortProcessor
from mpicbg.ij import ThinPlateSplineMapping
from mpicbg.ij import TransformMapping
# Create an image for testing blockmatching-based thin-plate spline elastic non-linear registration.
# The approach: define a grid of pointmatches that don't move, and then move only a few of them,
# so as to create local deformations.


# Define a grid of e.g., 10x10 points on the image, as PointMatch instances
def makeGridPointMatches(gridSide, incX, incY):
  """
  gridSide: how many points on the X and y axis, e.g., for 10 you get a grid of 10x10 = 100 points.
  incX: distance between grid points in the X axis.
  incY: distance between grid points in the Y axis.
  """
  pointmatches = ArrayList()
  for yIndex in xrange(gridSide):
    for xIndex in xrange(gridSide):
      position = [(1 + xIndex) * incX + 1,
                  (1 + yIndex) * incY + 1]
      p1 = Point(array(position, 'd'))
      p2 = Point(array(position, 'd'))
      pointmatches.add(PointMatch(p1, p2))

  return pointmatches


def translatePointMatches(pointmatches, points_to_translate, dx, dy):
  """
  In place.
  
  pointmatches: ArrayList of PointMatch instances
  points_to_translate: list of x,y index coordinate pairs of PointMatch to translate
  dx: displacement in X
  dy: displacement in Y
  """
  for x, y in points_to_translate:
    index = y * gridSide + x
    pm = pointmatches.get(index)
    c1 = pm.getP1().getW()
    c1[0] += dx
    c1[1] += dy
    pointmatches.set(index, PointMatch(pm.getP1(), Point(c1)))

  
def pointMatchesToLists(pointmatches):
  sourcePoints = newArray(Double.TYPE, [2, pointmatches.size()]) # 2D double array
  targetPoints = newArray(Double.TYPE, [2, pointmatches.size()]) # 2D double array
  
  for i, pointmatch in enumerate(pointmatches):
    srcPt = pointmatch.getP1().getL()
    tgtPt = pointmatch.getP2().getW()
    sourcePoints[0][i] = srcPt[0]
    sourcePoints[1][i] = srcPt[1]
    targetPoints[0][i] = tgtPt[0]
    targetPoints[1][i] = tgtPt[1]

  return sourcePoints, targetPoints


def transformImage(imp, transform):
  """
  imp: the ImagePlus to transform.
  transform: the transformation model, such as a thin-plate spline of class ThinPlateR2LogRSplineKernelTransform
  returns an ImagePlus
  """
  width, height = imp.getWidth(), imp.getHeight()
  ip = imp.getProcessor()
  spT = ShortProcessor(width, height)
  ip.setInterpolate(True)
  ip.setInterpolationMethod(ImageProcessor.BILINEAR) # can also use BICUBIC
  position = zeros(2, 'd') # double array
  
  for y in xrange(height):
    for x in xrange(width):
      position[0] = x
      position[1] = y
      transform.applyInPlace(position)
      # ImageProcessor.putPixel does array boundary checks
      spT.putPixel(x, y, ip.getPixelInterpolated(position[0], position[1]))
  
  return ImagePlus("transformed with " + type(transform).getSimpleName(), spT)


def transformImageFaster(imp, transform):
  """
  imp: the ImagePlus to transform.
  transform: the transformation model, such as a thin-plate spline of class ThinPlateR2LogRSplineKernelTransform
  
  returns an ImagePlus.
  
  Runs entirely in java, avoiding jython's slow looping.
  """
  # Create an ImageProcessor of the same kind
  ipT = imp.getProcessor().createProcessor(imp.getWidth(), imp.getHeight())
  
  if isinstance(transform, ThinPlateR2LogRSplineKernelTransform):
    # Somehow, mapInterpolated actually does an inverse transform
    ThinPlateSplineMapping(transform).mapInterpolated(imp.getProcessor(), ipT) # bilinear
  else:
    # Inverse because the transform was computed from source to target,
    # but here we want to pull source into target
    TransformMapping(transform).mapInverseInterpolated(imp.getProcessor(), ipT) # bilinear
  
  return ImagePlus("transformed with " + type(transform).getSimpleName(), ipT)


def createOverlayDisplacementVectors(pointmatches):
  # Show displacement field as an Overlay
  overlay = Overlay() # Set of Line ROI instances, each depicting a displacement vector
  
  for pm in pointmatches:
    p1 = pm.getP1().getW() # a double[] array
    p2 = pm.getP2().getW() # a double[] array
    overlay.add(Line(p1[0], p1[1], p2[0], p2[1])) # or use Arrow instead

  return overlay


# Grab the current image
imp = IJ.getImage()
width  = imp.getWidth()
height = imp.getHeight()

# Parameters:
gridSide = 10  # e.g., for 10, you get 10x10 = 100 grid points in 2D.
# Translate some points, to introduce deformations. Defined as indices in X and Y.
points_to_translate = [[3, 3], [4, 3], [7, 7], [7, 8]]
# Amount of displacement for some select points
dx = 10 # amount of pixels to move a point in X
dy = 10 # amount of pixels to move a point in Y

# Define distance between gridpoints. Adds 2 to set the points an equal distance from the edges of the image.
# (Use the 2 as a float, 2.0, to divide width, which is otherwise an integer, as a float.)
incX = width  / (gridSide + 2.0) # float; distance between grid points in X
incY = height / (gridSide + 2.0) # float; idem in Y

# Define a grid of identical PointMatch instances
pointmatches = makeGridPointMatches(gridSide, incX, incY)

# Define local displacements by moving the second, target point of some PointMatch instances, in place
translatePointMatches(pointmatches, points_to_translate, dx, dy)

# Use the pointmatches to define a thin-plate spline transform
sourcePoints, targetPoints = pointMatchesToLists(pointmatches)
transform = ThinPlateR2LogRSplineKernelTransform(2, sourcePoints, targetPoints)

# Transform the image
impT = transformImage(imp, transform)

# Show the displacements as an overlay
impT.setOverlay(createOverlayDisplacementVectors(pointmatches))

impT.show()
