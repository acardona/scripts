from net.imglib2.type.numeric.integer import UnsignedByteType, UnsignedShortType, UnsignedLongType
from net.imglib2.type.numeric.real import FloatType, DoubleType

import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.converter import createSamplerConverter
from lib.util import timeit


sampler_conv_floats = createSamplerConverter(UnsignedByteType, FloatType)

sampler_conv_doubles = createSamplerConverter(UnsignedByteType, DoubleType,
            fromMethod="getRealDouble",
            fromMethodReturnType="D",
            toMethod="setReal",
            toMethodArgType="D")

""" # Fails mysteriously with a java.lang.StringIndexOutOfBoundsException: String index out of range: -1 at converters.py:85
sampler_conv_longs = createSamplerConverter(UnsignedShortType, UnsignedLongType,
            fromMethod="getIntegerLong",
            fromMethodReturnType="L",
            toMethod="setInteger",
            toMethodArgType="L")
"""



# Test SamplerConverter:
from net.imglib2.img.array import ArrayImgs
from net.imglib2.converter import Converters
from net.imglib2.util import ImgUtil
from net.imglib2.img import ImgView
from net.imglib2.img.basictypeaccess import FloatAccess
from net.imglib2.converter.readwrite import SamplerConverter

dimensions = [100, 100, 100]
img1 = ArrayImgs.unsignedBytes(dimensions)
c = img1.cursor()
while c.hasNext():
  c.next().setOne()


def testASMFloats():
  img2 = ArrayImgs.floats(dimensions)
  ImgUtil.copy(ImgView.wrap(Converters.convertRandomAccessibleIterableInterval(img1, sampler_conv_floats), img1.factory()), img2)

def testASMDoubles():
  img2 = ArrayImgs.doubles(dimensions)
  ImgUtil.copy(ImgView.wrap(Converters.convertRandomAccessibleIterableInterval(img1, sampler_conv_doubles), img1.factory()), img2)

def testASMLongs():
  img2 = ArrayImgs.unsignedLongs(dimensions)
  ImgUtil.copy(ImgView.wrap(Converters.convertRandomAccessibleIterableInterval(img1, sampler_conv_longs), img1.factory()), img2)

timeit(20, testASMFloats)
timeit(20, testASMDoubles)

  