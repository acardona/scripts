from net.imglib2.algorithm.math.ImgMath import compute, add, offset, mul, minimum, maximum
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.view import Views
from ij import IJ, ImagePlus

img = IL.wrap(IJ.getImage()) # E.g. blobs sample image
imgE = Views.extendBorder(img)

def as2DKernel(imgE, weights):
  """ imgE: a RandomAccessible, such as an extended view of a RandomAccessibleInterval.
      weights: an odd-length list defining a square convolution kernel
               centered on the pixel, with columns moving slower than rows.
			Returns an ImgMath op.
  """
  # Check preconditions: validate kernel
  if 1 != len(weights) % 2:
    raise Error("list of kernel weights must have an odd length.")
  side = int(pow(len(weights), 0.5)) # sqrt
  if pow(side, 2) != len(weights):
    raise Error("kernel must be a square.")
  half = side / 2
  # Generate ImgMath ops
  # Note that multiplications by weights of value 1 or 0 will be erased automatically
  # so that the hierarchy of operations will be the same as in the manual approach above.
  return add([mul(weight, offset(imgE, [index % side - half, index / side - half]))
              for index, weight in enumerate(weights) if 0 != weight])


# All 4 edge detectors (left, right, top, bottom)
opTop = as2DKernel(imgE, [-1]*3 + [0]*3 + [1]*3)
opBottom = as2DKernel(imgE, [1]*3 + [0]*3 + [-1]*3)
opLeft = as2DKernel(imgE, [-1, 0, 1] * 3)
opRight = as2DKernel(imgE, [1, 0, -1] * 3)

# Now joined, in one of two ways: (can't add up: would cancel out to zero)
def combine(op, title, *ops):
  edges_img = img.factory().imgFactory(FloatType()).create(img)
  compute(op(*ops)).into(edges_img)
  imp = IL.wrap(edges_img, title)
  imp.getProcessor().resetMinAndMax()
  imp.show()
  return imp

imp_max = combine(maximum, "max edges", opTop, opBottom, opLeft, opRight)
imp_min = combine(minimum, "min edges", opTop, opBottom, opLeft, opRight)

# Create a mask for blobs that don't contact the edges of the image
imp_mask = ImagePlus("blobs mask", imp_max.getProcessor())
IJ.run(imp_mask, "Convert to Mask", "") # result has inverted LUT
IJ.run(imp_mask, "Fill Holes", "")
IJ.run(imp_mask, "Invert LUT", "") # revert to non-inverted LUT
imp_mask.show()

"""
edges1 = minimum(opTop, opBottom, opLeft, opRight)
edges2 = maximum(opTop, opBottom, opLeft, opRight)    

min_edges = img.factory().imgFactory(FloatType()).create(img)
compute(edges1).into(min_edges)
imp_min = IL.wrap(min_edges, "edges min")
imp_min.getProcessor().resetMinAndMax()
imp_min.show()

max_edges = min_edges.factory().create(img)
compute(edges2).into(max_edges)
imp_max = IL.wrap(max_edges, "edges max")
imp_max.getProcessor().resetMinAndMax()
imp_max.show()
"""