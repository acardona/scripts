# Example script: illustrate how to map pixels from one image to another.

from ij import IJ, ImageStack, ImagePlus
from ij.process import ColorProcessor, ImageProcessor
from mpicbg.models import AffineModel2D
from jarray import zeros

# Open the Drosophila larval brain sample RGB image stack
#imp = IJ.openImage("https://samples.imagej.net/samples/first-instar-brain.zip")
imp = IJ.getImage()
stack1 = imp.getStack() # of ColorProcessor

# Scale up by 1.5x
scale = 1.5
model = AffineModel2D()
model.set(scale, 0, 0, scale, 0, 0)
# An arbitrary affine, obtained from Plugins - Transform - Interactive Affine (push enter key to print it)
#model.set(1.16, 0.1484375, -0.375, 1.21875, 38.5, -39.5)

# New stack, larger
stack2 = ImageStack(int(imp.getWidth()  * scale),
                    int(imp.getHeight() * scale))
for index in xrange(1, stack1.getSize() + 1):
  stack2.addSlice(ColorProcessor(stack2.getWidth(), stack2.getHeight()))
imp2 = ImagePlus("larger (push)", stack2)

# Map data from stack to stack2 using the model transform
position = zeros(2, 'd')


# First approach: push (WRONG!)
width1, height1 = stack1.getWidth(), stack1.getHeight()

for index in xrange(1, 3): #stack1.size() + 1):
  cp1 = stack1.getProcessor(index)
  cp2 = stack2.getProcessor(index)
  for y in xrange(height1):
    for x in xrange(width1):
      position[1] = y
      position[0] = x
      model.applyInPlace(position)
      # ImageProcessor.putPixel does array boundary checks
      cp2.putPixel(int(position[0]), int(position[1]), cp1.getPixel(x, y))

imp2.show()

# Second approach: pull (CORRECT!)
imp3 = imp2.duplicate()
imp3.setTitle("larger (pull)")
stack3 = imp3.getStack()
width3, height3 = stack3.getWidth(), stack3.getHeight()

for index in xrange(1, 3): # stack1.size() + 1):
  cp1 = stack1.getProcessor(index)
  cp3 = stack3.getProcessor(index)
  # Ensure interpolation method is set
  cp1.setInterpolate(True)
  cp1.setInterpolationMethod(ImageProcessor.BILINEAR)
  for y in xrange(height3):
    for x in xrange(width3):
      position[1] = y
      position[0] = x
      model.applyInverseInPlace(position)
      # ImageProcessor.putPixel does array boundary checks
      cp3.putPixel(x, y, cp1.getPixelInterpolated(int(position[0]), int(position[1])))

imp3.show()



# Third approach: pull (CORRECT!), and much faster (delegates pixel-wise operations
# to java libraries)
# Defines a list of views (recipes, really) for transforming every stack slice
# and then materializes the view by copying it in a multi-threaded way into an ArrayImg.
from net.imglib2 import FinalInterval
from net.imglib2.converter import Converters, ColorChannelOrder
from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.realtransform import RealViews, AffineTransform2D
from net.imglib2.img.array import ArrayImgs
from net.imglib2.util import Intervals, ImgUtil
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory

img1 = Views.dropSingletonDimensions(IL.wrap(imp))
transform = AffineTransform2D()
transform.set(scale,     0, 0,
                  0, scale, 0)

# Origins and dimensions (hence, interval) of the target image 
interval2 = FinalInterval([int(img1.dimension(0) * scale),
                           int(img1.dimension(1) * scale),
                           img1.dimension(2)])
# Interval of a single stack slice of the target image
sliceInterval = FinalInterval([interval2.dimension(0),
                               interval2.dimension(1)])


slices2 = []
for index in xrange(img1.dimension(2)):
  # One single 2D RGB slice
  imgSlice1 = Views.hyperSlice(img1, 2, index)
  # Views of the 3 color channels, as extended and interpolatable
  channels = [Views.interpolate(Views.extendZero(Converters.argbChannel(imgSlice1, i)),
                                NLinearInterpolatorFactory())
              for i in [1, 2, 3]]
  # ARGBType 2D view of the transformed color channels
  imgSlice2 = Converters.mergeARGB(Views.stack(Views.interval(RealViews.transform(channel, transform),
                                                              sliceInterval)
                                               for channel in channels),
                                   ColorChannelOrder.RGB)
  slices2.append(imgSlice2)

# Transformed view
viewImg2 = Views.stack(slices2)
# Materialized image
img2 = ArrayImgs.argbs(Intervals.dimensionsAsLongArray(interval2))
ImgUtil.copy(viewImg2, img2)

imp4 = IL.wrap(img2, "imglib2-transformed RGB (pull)")
imp4.show()


# Fourth approach: pull (CORRECT!), and much faster (delegates pixel-wise operations
# to java libraries and delegates RGB color handling altogether)
# Defines a list of views (recipes, really) for transforming every stack slice
# and then materializes the view by copying it in a multi-threaded way into an ArrayImg.
# Now without separating the color channels: will use the NLinearInterpolatorARGB
# In practice, it's a tad slower than the third approach: also processes the alpha channel in ARGB
# even though we know it is empty. Its conciseness adds clarity and is a win.
"""
# Procedural code:
slices3 = []
for index in xrange(img1.dimension(2)):
  imgSlice1 = Views.interpolate(Views.extendZero(Views.hyperSlice(img1, 2, index)), NLinearInterpolatorFactory())
  imgSlice3 = Views.interval(RealViews.transform(imgSlice1, transform), sliceInterval)
  slices3.append(imgSlice3)
viewImg3 = Views.stack(slices3)
"""

# Functional code:
viewImg3 = Views.stack([Views.interval( # crop the transformed source image
                          RealViews.transform( # the source image into the target image
                            Views.interpolate( # to subsample the source image
                              Views.extendZero(Views.hyperSlice(img1, 2, index)), # source stack slice with infinite borders
                              NLinearInterpolatorFactory()), # interpolation strategy
                            transform), # the e.g. AffineTransform2D
                          sliceInterval) # of the target image
                        for index in xrange(img1.dimension(2))]) # for every stack slice

# Materialized target image
img3 = ArrayImgs.argbs(Intervals.dimensionsAsLongArray(interval2))
ImgUtil.copy(viewImg3, img3) # multi-threaded copy

imp5 = IL.wrap(img3, "imglib2-transformed ARGB (pull)")
imp5.show()



# Fifth approach: volume-wise transform with a pull (correct, but not always)
# Fast, yet, the interpolator has no way to know that it should restrict
# the inputs of the interpolation operation to pixels in the 2D plane,
# as generally in image stacks the Z resolution is much worse than that of XY.

from net.imglib2.realtransform import AffineTransform3D

transform3D = AffineTransform3D() # all matrix values are zero
transform3D.identity() # diagonal of 1.0
transform3D.scale(scale, scale, 1.0) # only X and Y

viewImg4 = Views.interval(
             RealViews.transform(
               Views.interpolate(
                 Views.extendZero(img1),
                 NLinearInterpolatorFactory()),
               transform3D),
             interval2)

# Materialized target image
img4 = ArrayImgs.argbs(Intervals.dimensionsAsLongArray(interval2))
ImgUtil.copy(viewImg4, img4) # multi-threaded copy

imp5 = IL.wrap(img4, "imglib2-transformed ARGB (pull) volume-wise")
imp5.show()








