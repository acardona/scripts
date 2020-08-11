from net.imglib2.algorithm.math.ImgMath import computeIntoFloat, sub, div
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.type.numeric.real import FloatType
from ij import IJ

# Simple example: normalize an image
imp = IJ.getImage()
ip = imp.getProcessor()
minV, maxV = ip.getMin(), ip.getMax()

img = IL.wrap(imp)
op = div(sub(img, minV), maxV - minV + 1)
result = computeIntoFloat(op)

IL.wrap(result, "normalized").show()


# As a view
IL.wrap(op.view(FloatType()), "normalized").show()