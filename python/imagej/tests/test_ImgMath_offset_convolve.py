from net.imglib2.algorithm.math.ImgMath import compute, add, offset, mul, minimum, maximum
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.type.numeric.integer import UnsignedByteType, ShortType
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.view import Views
from net.imglib2.algorithm.math.abstractions import Util
from ij import IJ

img = IL.wrap(IJ.getImage()) # blobs sample image
imgE = Views.extendBorder(img)

# Convolve with 3x3 kernel:
# -1 0 1
# -1 0 1
# -1 0 1
left_edges = add(mul(-1, offset(imgE, [-1, -1])),
                 mul(-1, offset(imgE, [-1,  0])),
                 mul(-1, offset(imgE, [-1,  1])),
                 offset(imgE, [1, -1]),
                 offset(imgE, [1, 0]),
                 offset(imgE, [1, 1]))

target = img.factory().imgFactory(FloatType()).create(img)
compute(left_edges).into(target)

IL.wrap(target, "left edges").show()


def as2DKernel(imgE, weights):
  """ imgE: a RandomAccessible, such as an extended view of a RandomAccessibleInterval.
      weights: an odd-length list defining a square convolution kernel
               centered on the pixel, with columns moving slower than rows.
  """
  # Check preconditions: validate kernel
  if 1 != len(weights) % 2:
    raise Error("kernel weights must have an odd length.")
  side = int(pow(len(weights), 0.5)) # sqrt
  if pow(side, 2) != len(weights):
    raise Error("kernel must be a square.")
  # Generate ImgMath ops
  # Note that multiplications by weights of value 1 or 0 will be erased automatically
  # so that the hierarchy of operations will be the same as in the manual approach above.
  return add([mul(weight, offset(imgE, [index % side, index / side]))
              for index, weight in enumerate(weights) if 0 != weight])

left_edges2 = as2DKernel(imgE, [-1, 0, 1,
                               -1, 0, 1,
                               -1, 0, 1])


target2 = img.factory().imgFactory(FloatType()).create(img)
compute(left_edges2).into(target2)

IL.wrap(target2, "left edges").show()


# All 4 edge detectors (left, right, top, bottom)
opTop = as2DKernel(imgE, [-1]*3 + [0]*3 + [1]*3)
opBottom = as2DKernel(imgE, [1]*3 + [0]*3 + [-1]*3)
opLeft = as2DKernel(imgE, [-1, 0, 1] * 3)
opRight = as2DKernel(imgE, [1, 0, -1] * 3)

# Now joined, in one of two ways: (can't add up: would cancel out to zero)
edges1 = minimum(opTop, opBottom, opLeft, opRight)
edges2 = maximum(opTop, opBottom, opLeft, opRight)    

target1 = img.factory().imgFactory(FloatType()).create(img)
compute(edges1).into(target1)
IL.wrap(target1, "edges min").show()

target2 = img.factory().imgFactory(FloatType()).create(img)
compute(edges2).into(target2)
IL.wrap(target2, "edges max").show()


                               
