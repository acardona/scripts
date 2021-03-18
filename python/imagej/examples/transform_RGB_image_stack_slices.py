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
interval2 = FinalInterval([int(img1.dimension(0) * scale),
                           int(img1.dimension(1) * scale),
                           img1.dimension(2)])

slices2 = []
for index in xrange(img1.dimension(2)):
  # One single 2D RGB slice
  imgSlice1 = Views.hyperSlice(img1, 2, index)
  # Views of the 3 color channels, as extended and interpolatable
  channels = [Views.interpolate(Views.extendZero(Converters.argbChannel(imgSlice1, i)), # TODO can interpolate ARGBType directly?
                                NLinearInterpolatorFactory())
              for i in [1, 2, 3]]
  # ARGBType 2D view of the transformed color channels
  imgSlice2 = Converters.mergeARGB(Views.stack(Views.interval(RealViews.transform(channel, transform),
                                                              FinalInterval([interval2.dimension(0),
                                                                             interval2.dimension(1)]))
                                               for channel in channels),
                                   ColorChannelOrder.RGB)
  slices2.append(imgSlice2)

# Transformed view
viewImg2 = Views.stack(slices2)
# Materialized image
img2 = ArrayImgs.argbs(Intervals.dimensionsAsLongArray(interval2))
ImgUtil.copy(viewImg2, img2)

imp4 = IL.wrap(img2, "imglib2-transformed (pull)")
imp4.show()





