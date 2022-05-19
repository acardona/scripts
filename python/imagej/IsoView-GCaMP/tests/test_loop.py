from net.imglib2.img.array import ArrayImgs
import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from random import random
from net.imglib2.loops import LoopBuilder
from net.imglib2.type.numeric.real import FloatType
from lib.loop import createBiConsumerTypeSet, createBiConsumerTypeSet2, binaryLambda
from java.util.function import BiConsumer


img1 = ArrayImgs.floats([10, 10, 10])
cursor = img1.cursor()
for t in img1:
  t.setReal(random())

img2 = ArrayImgs.floats([10, 10, 10])

#copyIt = createBiConsumerTypeSet(FloatType) # works well
#copyIt = createBiConsumerTypeSet2(FloatType) # works well
#LoopBuilder.setImages(img1, img2).forEachPixel(copyIt)

copyIt = binaryLambda(FloatType, "set", FloatType,
                      interface=BiConsumer, interface_method="accept").newInstance()

ra1 = img1.randomAccess()
ra2 = img2.randomAccess()

print "Before copy:", ra1.get(), ra2.get()

# For binaryLambda, need to reverse the order of the images
# because the type of first one is the base object on which the "set" method is invoked
# with the type of the second one as its arg.
LoopBuilder.setImages(img2, img1).forEachPixel(copyIt)

pos = [3, 2, 5]
ra1.setPosition(pos)
ra2.setPosition(pos)

print "After copy:", ra1.get(), ra2.get()

print ra1.get() == ra2.get()
