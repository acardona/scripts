from net.imglib2.img.array import ArrayImgs
from net.imglib2.view import Views
from net.imglib2.type.numeric.integer import UnsignedByteType


img1 = ArrayImgs.unsignedBytes([10, 10, 10])
img2 = ArrayImgs.unsignedBytes([10, 10, 10])

stack = Views.stack([img1, img2])

for t in Views.iterable(stack):
  t.setReal(1)

assert 1000 + 1000 == sum(t.get() for t in Views.iterable(stack))