from net.imglib2.algorithm.math.ImgMath import compute, block, div, offset, add
from net.imglib2.algorithm.math.abstractions import Util
from net.imglib2.algorithm.integral import IntegralImg
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.img.array import ArrayImgs
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.type.numeric.integer import UnsignedByteType, UnsignedShortType, UnsignedLongType
from net.imglib2.view import Views
from net.imglib2.util import Intervals
from ij import IJ

imp = IJ.getImage() # e.g. EM of Drosophila neurons 180-220-sub512x512-30.tif
#imp = IJ.openImage("/home/albert/lab/TEM/abd/microvolumes/Seg/180-220-sub/180-220-sub512x512-30.tif")
img = compute(IL.wrap(imp)).intoImg(UnsignedShortType()) # in 16-bit

alg = IntegralImg(img, UnsignedLongType(), Util.genericIntegerTypeConverter())
alg.process()
integralImg = alg.getResult()
imgE = Views.extendBorder(integralImg)

width = img.dimension(0)
min_width = 32

# Create an image pyramid with ImgMath and imglib2
# which amounts to scale area averaging sped up by the integral image
blockSide = 1
pyramid = [] # level 0 is the image itself, not added
corners = [[0, 0], [1, 0], [0, 1], [1, 1]]
while width > min_width:
  blockSide *= 2
  width /= 2
  # Scale the corner coordinates to make the block larger
  cs = [[c * blockSide for c in corner] for corner in corners]
  blockRead = div(block(imgE, cs), pow(blockSide, 2)) # the op
  # a RandomAccessibleInterval view of the op, computed with shorts but seen as bytes
  view = blockRead.view(UnsignedShortType(), UnsignedByteType())
  # Views.subsample by 2 turns a 512-pixel width to a 257 width, so crop to proper interval 256
  level = Views.interval(Views.subsample(view, blockSide),
                         [0] * img.numDimensions(),
                         [img.dimension(d) / blockSide -1 for d in xrange(img.numDimensions())])
  pyramid.append(level)

for i, level in enumerate(pyramid):
  IL.wrap(level, str(i)).show()
