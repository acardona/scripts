from net.imglib2.algorithm.math.ImgMath import compute, IF, THEN, ELSE, AND, OR, XOR, NOT, LT
from net.imglib2.img.array import ArrayImgFactory
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from java.lang import System
from jarray import array,zeros

pixels1 = array([0, 0, 0, 0,
                 0, 1, 0, 0,
                 0, 0, 1, 0,
                 0, 0, 0, 0], 'b')
pixels2 = array([1, 0, 0, 0,
                 0, 1, 1, 0,
                 0, 1, 1, 0,
                 0, 0, 0, 1], 'b')
pixels3 = array([1, 0, 0, 0, # XOR of 1 and 2
                 0, 0, 1, 0,
                 0, 1, 0, 0,
                 0, 0, 0, 1], 'b')
pixels4 = array([1, 1, 1, 1, # NOT or 1
                 1, 0, 1, 1,
                 1, 1, 0, 1,
                 1, 1, 1, 1], 'b')

def intoImg(pixels):
  img = ArrayImgFactory(UnsignedByteType()).create([4, 4])
  System.arraycopy(pixels, 0, img.update(None).getCurrentStorageArray(), 0, len(pixels))
  return img

img1 = intoImg(pixels1)
img2 = intoImg(pixels2)
img3 = intoImg(pixels3)
img4 = intoImg(pixels4)


def same(img1, img2):
  c1 = img1.cursor()
  c2 = img1.cursor()
  while c1.hasNext():
    if c1.next().get() != c2.next().get():
      return False
  return True

imgAND = compute(AND(img1, img2)).intoArrayImg()
#IL.wrap(img, "AND").show()
print "AND:", same(img1, imgAND)

imgOR = compute(OR(img1, img2)).intoArrayImg()
print "OR:", same(img2, imgOR)

imgXOR = compute(XOR(img1, img2)).intoArrayImg()
print "XOR:", same(img3, imgXOR)

imgNOT = compute(NOT(img1)).intoArrayImg()
print "NOT:", same(img4, imgNOT)


# Test LogicalAndBoolean
imgIFAND = compute(IF(AND(LT(img1, 1), LT(img2, 1)),
                     THEN(1),
                     ELSE(0))).intoArrayImg()

pixels5 = zeros(len(pixels1), 'b')
for i in xrange(len(pixels5)):
  pixels5[i] = 1 if pixels1[i] < 1 and pixels2[i] < 1 else 0
imgTEST = intoImg(pixels5)
#IL.wrap(imgIFAND, "IFAND").show()
print "IFAND", same(imgTEST, imgIFAND)
