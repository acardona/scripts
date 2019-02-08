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


# The target, single-timepoint image
img3D = ArrayImgs.unsignedShorts(Intervals.dimensionsAsLongArray(img3DV))

last_dimension = img4D.numDimensions() -1

if img4D.dimension(last_dimension) > 10:
  # one by one
  for i in xrange(img4D.dimension(last_dimension)):
    compute(maximum(img3D, Views.hyperSlice(img4D, last_dimension, i))).into(img3D)

else:
  # Each sample of img3DV is a virtual vector over all time frames at that 3D coordinate:
  img3DV = Views.collapseReal(img4D)
  # Reduce each vector to a single scalar, using a Converter
  # The Converter class
  reduce_max = makeCompositeToRealConverter(reducer_class=Math,
                                            reducer_method="max",
                                            reducer_method_signature="(DD)D")
  img3DC = convert(img3DV, reduce_max.newInstance(), img4D.randomAccess().get().getClass())
  ImgUtil.copy(ImgView.wrap(img3DC, img3D.factory()), img3D)

showStack(img3D, "projected")
