from net.imglib2.algorithm.math.ImgMath import compute, block, div, offset, add
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.array import ArrayImgs
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.view import Views
from net.imglib2.algorithm.math.abstractions import Util
from net.imglib2.util import Intervals
from ij import IJ

imp = IJ.getImage() # an 8-bit image
img = IL.wrap(imp)

converter = Util.genericIntegerTypeConverter()

target = ArrayImgs.unsignedLongs(Intervals.dimensionsAsLongArray(img))
compute(img).into(target) # copy
# Instead of offset, could also use Views.translate(Views.extendZero(target), [1, 0]))
# (Notive the sign change in the translation)
integralX = add(target, offset(Views.extendZero(target), [-1, 0])) # cummulative sum X axis
compute(integralX).into(target)
integralY = add(target, offset(Views.extendZero(target), [0, -1]))
compute(integralY).into(target)

integralImg = target

radius = 5
radii = [radius] * img.numDimensions()
volume = pow(radius * 2, img.numDimensions())

op = div(block(Views.extendBorder(integralImg), radii), volume)

target = ArrayImgs.floats(Intervals.dimensionsAsLongArray(img))
compute(op).into(target, None, FloatType(), None)

IL.wrap(target, "integral image 5x5x5 blur").show()