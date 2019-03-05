import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.converter import makeCompositeToRealConverter, convert
from lib.ui import showStack
from ij import IJ
from net.imglib2.img.display.imagej import ImageJVirtualStack, ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2.img.array import ArrayImgs
from net.imglib2.util import Intervals, ImgUtil
from net.imglib2.algorithm.math.ImgMath import compute, maximum
from java.lang import Math

imp = IJ.getImage()
stack = imp.getStack()

# Grab the underlying ImgLib2 object, or wrap into one
if isinstance(stack, ImageJVirtualStack):
  srcF = ImageJVirtualStack.getDeclaredField("source")
  srcF.setAccessible(True)
  img4D = srcF.get(stack)
else:
  img4D = IL.wrap(imp)


def projectLastDimension(img, showEarly=False):
  """
  Project the last dimension, e.g. a 4D image becomes a 3D image,
  using the provided reducing function (e.g. min, max, sum).
  """
  last_dimension = img.numDimensions() -1
  # The collapsed image
  imgC = ArrayImgs.unsignedShorts([img.dimension(d) for d in xrange(last_dimension)])

  if showEarly:
    showStack(imgC, title="projected") # show it early, will be updated progressively

  if img.dimension(last_dimension) > 10:
    # one by one
    print "One by one"
    for i in xrange(img.dimension(last_dimension)):
      print i
      compute(maximum(imgC, Views.hyperSlice(img, last_dimension, i))).into(imgC)
  else:
    # Each sample of img3DV is a virtual vector over all time frames at that 3D coordinate:
    imgV = Views.collapseReal(img)
    # Reduce each vector to a single scalar, using a Converter
    # The Converter class
    reduce_max = makeCompositeToRealConverter(reducer_class=Math,
                                              reducer_method="max",
                                              reducer_method_signature="(DD)D")
    img3DC = convert(imgV, reduce_max.newInstance(), img.randomAccess().get().getClass())
    ImgUtil.copy(ImgView.wrap(imgV, img.factory()), imgC)

  return imgC

img3D = projectLastDimension(img4D, showEarly=True)

showStack(img3D, title="projected")
