from net.imglib2.algorithm.math.ImgMath import compute, block, div, offset, add
from net.imglib2.algorithm.math.abstractions import Util
from net.imglib2.algorithm.integral import IntegralImg
from net.imglib2.type.numeric.integer import UnsignedByteType, UnsignedShortType, UnsignedLongType
from net.imglib2.view import Views
from net.imglib2.realtransform import RealViews
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from net.imglib2.realtransform import Scale
from net.imglib2 import FinalInterval


def pyramidAreaAveraging(img,
                         top_level,
                         min_width=32,
                         sumType=UnsignedLongType,
                         mathType=UnsignedLongType,
                         converter=Util.genericIntegerTypeConverter()):
  """ Return a list of image views, one per scale level of the image pyramid,
      except for level zero (the first image) which is the provided img.
      All images are of the same type as the source img.
      Based on an integral image for fast computation.
  """

  img_type = img.randomAccess().get().createVariable()
  
  # Create an integral image in longs
  alg = IntegralImg(img, sumType(), converter)
  alg.process()
  integralImg = alg.getResult()

  # Create an image pyramid as views, with ImgMath and imglib2,
  # which amounts to scale area averaging sped up by the integral image
  # and generated on demand whenever each pyramid level is read.
  width = img.dimension(0)
  imgE = Views.extendBorder(integralImg)
  blockSide = 1
  level_index = 1
  # Corners for level 1: a box of 2x2
  corners = [[0, 0], [1, 0], [0, 1], [1, 1]]
  pyramid = [img]

  while width > min_width and level_index <= top_level:
    blockSide *= 2
    width /= 2
    # Scale the corner coordinates to make the block larger
    cs = [[c * blockSide for c in corner] for corner in corners]
    blockRead = div(block(imgE, cs), pow(blockSide, 2)) # the op
    # a RandomAccessibleInterval view of the op, computed with shorts but seen as bytes
    view = blockRead.view(mathType(), img_type.createVariable())
    # Views.subsample by 2 will turn a 512-pixel width to a 257 width,
    # so crop to proper interval 256
    level = Views.interval(Views.subsample(view, blockSide),
                           [0] * img.numDimensions(), # min
                           [img.dimension(d) / blockSide -1
                            for d in xrange(img.numDimensions())]) # max
    pyramid.append(level)
    level_index += 1 # for next iteration

  return pyramid


def pyramid(img,
            top_level,
            min_width=32,
            ViewOutOfBounds=Views.extendBorder
            interpolation_factory=NLinearInterpolatorFactory()):
  """
  Create an image pyramid as interpolated scaled views of the provided img.
  """
  imgR = Views.interpolate(ViewOutOfBounds(img), interpolation_factory)

  # Create levels of a pyramid as interpolated views
  width = img.dimension(0)
  pyramid = [img]
  scale = 1.0
  level_index = 1
  while width > min_width and level_index <= top_level:
    scale /= 2.0
    width /= 2
    s = [scale for d in xrange(img.numDimensions())]
    scaled = Views.interval(RealViews.transform(imgR, Scale(s)),
                            FinalInterval([int(img.dimension(d) * scale)
                                           for d in xrange(img.numDimensions())]))
    pyramid.append(scaled)
    level_index += 1 # for next iteration
  
  return pyramid


# TODO pyramidGauss a la Saalfeld
