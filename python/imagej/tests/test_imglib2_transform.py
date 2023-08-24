from ij import IJ, ImagePlus
from net.imglib2 import RandomAccessibleInterval
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.realtransform import RealViews, AffineTransform2D
from net.imglib2.view import Views
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from math import sin, cos, radians, sqrt
from java.awt.geom import AffineTransform

imp = IJ.getImage() # e.g. the leaf sample image


def viewTransformed(image, transformation, title=None, interval=None, show=True):
  if isinstance(image, ImagePlus):
    img = IL.wrap(image) # ImagePlus to ImgLib2 RandomAccessibleInterva & IterableInterval aka Img
  elif isinstance(image, RandomAccessibleInterval):
    img = image
  else:
    return None
  # Make the image be defined anywhere by infinitely padding with zeros.
  imgInfinite = Views.extendZero(img)
  # Make the image be defined at arbitrarily precise subpixel coordinates
  # by using n-dimensional linear interpolation
  imgInterpolated = Views.interpolate(imgInfinite, NLinearInterpolatorFactory())
  # Make the image be seen as a transformed view of the source image
  imgTransformed = RealViews.transform(imgInterpolated, transformation)
  # Define an interval within which we want the transformed image to be defined
  # (such as that of the source img itself; an img in ImgLib2 also happens to be an Interval
  # and can therefore be used as an interval, which is convenient here because we
  # expect the original field of view--the interval--to be where image data can still be found)
  interval = interval if interval else img # every Img is also an Interval because each Img is bounded
  # Make the image finite by defining it as the content within the interval
  imgBounded = Views.interval(imgTransformed, interval) # same as original
  # Optionally show the transformed, bounded image in an ImageJ VirtualStack
  # (Note that anytime one of the VirtualStack's ImageProcessor will have to
  # update its pixel data, it will incur in executing the transformation again;
  # no pixel data is cached or copied anywhere other than for display purposes)
  if show:
    title = title if title else imp.getTitle()
    imp = IL.wrap(imgBounded, title) # as an ImagePlus
    imp.show() # in an ImageJ ImageWindow
  return imgBounded


# Transform the image in 2D by using an affine matrix
# The identity transform--or no transform--looks like this:
#
# [1.0, 0.0, 0.0,
#  0.0, 1.0, 0.0]
#
# Above, the first row is the X axis
# and the second row is the Y axis

# The application of this transformation matrix to the coordinates
# of each pixel will do nothing: coordinates stay the same.
# The first two columns control scaling, rotation and shear,
# and the third column controls the translation.
#
# What are these values? A matrix is a way of representing a system of equations.
# In this case, there are two variables: the X and Y coordinates.
# Each cell in the matrix is really:
#
# [[cos(angle), sin(angle), translation],
#  [-sin(angle), cos(angle), translation]]
#
# When the angle is 0, the two cos(angle) are 1.0,
# and the two sin(angle) are 0.0. Which is the identity affine transform.
# 
# Where does this matrix representation come from?
# Turns out, the linear mapping (the transformation) is merely the upper left part:
# 
# [[cos(angle, sin(angle)],
#  [-sin(angle, cos(angle)]]
#
# To include the translation along with the linear map into the same matrix
# would allow for a single matrix multiplication to take place, reducing
# computational costs and simplifyig the representation. This is what
# the affine transform accomplishes, by virtue of being an augmented matrix
# (see wikipedia at https://en.wikipedia.org/wiki/Affine_transformation#Augmented_matrix ).
# 
# And so the full matrix would look like this:
#
# [[ cos(angle), sin(angle), translation],
#  [-sin(angle), cos(angle), translation],
#  [          0,         0]            1]]
#
# The extra row is all zeroes with a one at the end;
# the extra column is the translation term, plus a 1 at the end.
# 
# This augmented matrix can now be multipled by other similarly augmented matrices;
# in other words, multiple affine transforms can be concatenated and therefore
# compacted into a single affine transform. This presents the enormous
# advantage of then letting us apply a single transform to the image,
# reducing not only the number of operations per pixel (and therefore gaining
# in speed performance) but also reducing the noise, by avoiding the repeated
# transformation (with its floating-point error from interpolations) of the image.
#
#
# Handling angles by using sin and cos, though, is fidgety and error-prone.
# Instead, let's develop an intuitive understanding first,
# and then show how to use existing convenience methods so that
# we never have to use sin and cos in our own code.


# Flip horizontally:
# Multiply the X axis coordinates by -1,
# and translate X axis coordinates by the image width
# so as to bring the data back into the interval [0, width]
mirrorX = AffineTransform2D()
mirrorX.set(-1.0, 0.0, imp.getWidth(),
             0.0, 1.0, 0.0)

viewTransformed(imp, mirrorX,
                title=imp.getTitle() + " mirrorX")


# Flip vertically:
# Multiply the Y axis coordinates by -1,
# and translate the Y axis coordinates by the image height
# so as to bring the data back into the interval [0, height]
mirrorY = AffineTransform2D()
mirrorY.set(1.0, 0.0, 0.0,
            0.0, -1.0, imp.getHeight())

viewTransformed(imp, mirrorY,
                title=imp.getTitle() + " mirrorY")


# Flip simultaneously horizontally and vertically
mirrorXY = AffineTransform2D()
mirrorXY.set(-1.0, 0.0, imp.getWidth(),
             0.0, -1.0, imp.getHeight())

viewTransformed(imp, mirrorXY,
                title=imp.getTitle() + " mirrorXY")



# We can think of rotations as simultaneously shearing in the X and Y axes


# 90 degree rotation to the right
# Note that any negative scaling (-1.0) requires
# a compensatory translation (imp.getWidth) in the same axis
# to place the data back into the field of view, i.e. the interval [0, width]
rotate90 = AffineTransform2D()
rotate90.set(0.0, -1.0, imp.getWidth(),
             1.0, 0.0, 0.0)

viewTransformed(imp, rotate90,
                title=imp.getTitle() + " rotate90")

# 90 degree rotation to the left 
rotate270 = AffineTransform2D()
rotate270.set(0.0, 1.0, 0.0,
              -1.0, 0.0, imp.getHeight())

viewTransformed(imp, rotate270,
                title=imp.getTitle() + " rotate270")


# 45 degree rotation to the right around the center of the image.
# which requires computing the translation, otherwise
# leaving as zeros the translation terms would rotate around 0,0,
# that is, around the origin of coordinates.
rotate45 = AffineTransform2D()
sin45 = sin(radians(-45)) # == -sqrt(2) / 2
cos45 = cos(radians(-45)) # ==  sqrt(2) / 2
cx = imp.getWidth() / 2.0
cy = imp.getHeight()/2.0
rotate45.set( cos45, sin45, (1 - cos45) * cx -      sin45  * cy,
             -sin45, cos45,      sin45  * cx + (1 - cos45) * cy)

viewTransformed(imp, rotate45,
                title=imp.getTitle() + " rotate45")


# Remembering the formulas for the translation to correct
# for the origin of transformation (e.g. the center) isn't easy,
# and the fidgety of it all makes it error prone.

# For 2D, java offers an AffineTransform class that addresses this issue
# quite trivially, with the method rotate that takes an origin of rotation
# as argument.
# BEWARE that positive angles rotate to the right (rather than to the left)
# in the AffineTransform, so we use radians(45) instead of radians(-45).
# And BEWARE that AffineTransform.getMatrix fills a double[] array in
# an order that you wouldn't expect (see the javadoc), so instead
# we call each value of the matrix, one by one, to fill our matrix.

aff = AffineTransform() # initialized as the identity transform
cx = imp.getWidth() / 2.0
cy = imp.getHeight() / 2.0
aff.rotate(radians(45), cx, cy)
rotate45easy = AffineTransform2D()
rotate45easy.set(aff.getScaleX(), aff.getShearX(), aff.getTranslateX(),
                 aff.getShearY(), aff.getScaleY(), aff.getTranslateY())

print rotate45easy

viewTransformed(imp, rotate45easy,
                title=imp.getTitle() + " rotate45easy")


# An alternative that works also for 3D transformations exploits
# a nice property of transformation matrices: that they can be combined.
# That is, instead of applying a transform to an image, an then applying
# a second transform to the resulting image, instead the transformation
# matrices can be multiplied, and a single transform applied to the image.
# This is desirable not only for performance reasons, but primarily
# because it avoids the accumulation of interpolation errors.
# In addition, ImgLib2 realtransform classes offer a "rotate" method
# which simplies operations further: no more explicit sin and cos!
# BEWARE that, like java.awt.geom.AffineTransform, ImgLib2's affine classes
# use positive angles to mean clockwise rotations, so we use radians(45)
# to rotate to the right.

cx = imp.getWidth() / 2.0
cy = imp.getHeight() / 2.0

translateToCenter = AffineTransform2D()
translateToCenter.set(1.0, 0.0, -cx,
                      0.0, 1.0, -cy)

rotate45 = AffineTransform2D()
rotate45.set(1.0, 0.0, 0.0,
             0.0, 1.0, 0.0) # initialize to identity
rotate45.rotate(radians(45))

translateBack = translateToCenter.inverse()

combined = AffineTransform2D()
combined.set(translateToCenter)
combined.preConcatenate(rotate45)
combined.preConcatenate(translateBack)

viewTransformed(imp, combined,
                title=imp.getTitle() + " combined")

