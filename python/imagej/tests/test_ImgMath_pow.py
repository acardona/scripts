

from net.imglib2.type.numeric.real import FloatType

ft = FloatType(10)
ft.pow(2)

print ft

from net.imglib2.algorithm.math.ImgMath import compute, add, power
from net.imglib2.img.array import ArrayImgs
from net.imglib2.img.display.imagej import ImageJFunctions as IL

img = ArrayImgs.floats([10, 10, 10])

compute(add(img, 5)).into(img) # in place

compute(power(img, 2)).into(img) # in place

print 25 * 10 * 10 * 10 == sum(t.get() for t in img.cursor())

IL.wrap(img, "5 squared").show()