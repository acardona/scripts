from net.imglib2.img.array import ArrayImgs
import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from random import random
from net.imglib2.loops import LoopBuilder
from net.imglib2.type.numeric.real import FloatType
from lib.loop import createBiConsumerTypeSet #2 as createBiConsumerTypeSet # both work

img1 = ArrayImgs.floats([10, 10, 10])
cursor = img1.cursor()
for t in img1:
  t.setReal(random())

img2 = ArrayImgs.floats([10, 10, 10])

copyIt = createBiConsumerTypeSet(FloatType)

LoopBuilder.setImages(img1, img2).forEachPixel(copyIt)

ra1 = img1.randomAccess()
ra2 = img2.randomAccess()

pos = [3, 2, 5]
ra1.setPosition(pos)
ra2.setPosition(pos)

print ra1.get() == ra2.get()
