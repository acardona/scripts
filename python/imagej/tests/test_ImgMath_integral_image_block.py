from net.imglib2.algorithm.math.ImgMath import compute, block, div
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.algorithm.integral import IntegralImg
from net.imglib2.img.array import ArrayImgs
from net.imglib2.type.numeric.integer import UnsignedByteType, UnsignedShortType, UnsignedLongType
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.view import Views
from net.imglib2.algorithm.math.abstractions import Util
from net.imglib2.util import Intervals
from ij import IJ

imp = IJ.getImage() # an 8-bit image
img = IL.wrap(imp)

converter = Util.genericIntegerTypeConverter()
alg = IntegralImg(img, UnsignedLongType(), converter)
alg.process()
integralImg = alg.getResult()

op = div(block(Views.extendBorder(integralImg), [5, 5]), 100)

#target = ArrayImgs.unsignedShorts(Intervals.dimensionsAsLongArray(img))
target = ArrayImgs.floats(Intervals.dimensionsAsLongArray(img))
compute(op).into(target, None, FloatType(), None)

IL.wrap(target, "integral image 5x5x5 blur").show()