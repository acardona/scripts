# The hue of an RGB image as a computation

from ij import IJ, ImagePlus, ImageStack
from ij.process import ByteProcessor, FloatProcessor
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.algorithm.math.ImgMath import let, IF, EQ, LT, THEN, ELSE, add, div, sub, maximum, minimum, compute, img
from net.imglib2.algorithm.math.abstractions.Util import hierarchy
from net.imglib2.converter import Converters
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.view import Views
from net.imglib2.img.array import ArrayImgs
from net.imglib2.util import ImgUtil
from net.imglib2.img import ImgView
from java.lang import System
from jarray import zeros
from itertools import izip

rgb = IL.wrap(IJ.getImage())

red = Converters.argbChannel(rgb, 1)
green = Converters.argbChannel(rgb, 2)
blue = Converters.argbChannel(rgb, 3)

def test(red, green, blue, easy=True):
  saturation = let( "red", red,
                    "green", green,
                    "blue", blue,
                    "max", maximum( "red", "green", "blue" ),
                    "min", minimum( "red", "green", "blue" ),
                    IF ( EQ( 0, "max" ),
                     THEN( 0 ),
                     ELSE( div( sub( "max", "min" ),
                              "max" ) ) ) )

  brightness = div( maximum( red, green, blue ), 255.0 )
  
  hue = IF ( EQ( 0, saturation ),
          THEN( 0 ),
          ELSE( let( "red", red,
                     "green", green,
                     "blue", blue,
                     "max", maximum( "red", "green", "blue" ),
                     "min", minimum( "red", "green", "blue" ),
                     "range", sub( "max", "min" ),
                     "redc", div( sub( "max", "red" ), "range" ),
                     "greenc", div( sub( "max", "green" ), "range" ),
                     "bluec", div( sub( "max", "blue" ), "range" ),
                     "hue", div( IF ( EQ( "red", "max" ),
                                   THEN( sub( "bluec", "greenc" ) ),
                                   ELSE( IF ( EQ( "green", "max" ),
                                           THEN( sub( add( 2, "redc" ), "bluec" ) ),
                                           ELSE( sub( add( 4, "greenc"), "redc" ) ) ) ) ),
                                 6 ),
                     IF ( LT( "hue", 0 ),
                       THEN( add( "hue", 1 ) ),
                       ELSE( "hue" ) ) ) ) )
  
  #print hierarchy(hue)

  #print "hue view:", hue.view( FloatType() ).iterationOrder()
  
  if easy:
    # About 26 ms
    """
    hsb = Views.stack( hue.view( FloatType() ),
                       saturation.view( FloatType() ),
                       brightness.view( FloatType() ) )
    """

    # About 13 ms: half! Still much worse than plain ImageJ,
    # but the source images are iterated 4 times, rather than just once,
    # and the saturation is computed twice,
    # and the min, max is computed 3 and 4 times, respectively.
    hsb = Views.stack( hue.viewDouble( FloatType() ),
                       saturation.viewDouble( FloatType() ),
                       brightness.viewDouble( FloatType() ) )
    
    """
    # Even worse: ~37 ms
    width, height = rgb.dimension(0), rgb.dimension(1)
    h = compute(hue).into(ArrayImgs.floats([width, height]))
    s = compute(saturation).into(ArrayImgs.floats([width, height]))
    b = compute(brightness).into(ArrayImgs.floats([width, height]))
    hsb = Views.stack( h, s, b )
    """

    imp = IL.wrap( hsb, "HSB view" )
  else:
    # Tested it: takes more time (~40 ms vs 26 ms above)
    width, height = rgb.dimension(0), rgb.dimension(1)
    hb = zeros(width * height, 'f')
    sb = zeros(width * height, 'f')
    bb = zeros(width * height, 'f')
    h = ArrayImgs.floats(hb, [width, height])
    s = ArrayImgs.floats(sb, [width, height])
    b = ArrayImgs.floats(bb, [width, height])
    #print "ArrayImg:", b.iterationOrder()
    ImgUtil.copy(ImgView.wrap(hue.view(FloatType()), None), h)
    ImgUtil.copy(ImgView.wrap(saturation.view(FloatType()), None), s)
    ImgUtil.copy(ImgView.wrap(brightness.view(FloatType()), None), b)
    stack = ImageStack(width, height)
    stack.addSlice(FloatProcessor(width, height, hb, None))
    stack.addSlice(FloatProcessor(width, height, sb, None))
    stack.addSlice(FloatProcessor(width, height, bb, None))
    imp = ImagePlus("hsb", stack)
  return imp


# For the test, transfer converted views into arrays
ared = compute(img(red)).into(ArrayImgs.unsignedBytes([rgb.dimension(0), rgb.dimension(1)]))
agreen = compute(img(green)).into(ArrayImgs.unsignedBytes([rgb.dimension(0), rgb.dimension(1)]))
ablue = compute(img(blue)).into(ArrayImgs.unsignedBytes([rgb.dimension(0), rgb.dimension(1)]))

def timeit(fn, *args, **kwargs):
  n_iterations = 20
  times = []
  for i in xrange(n_iterations):
    t0 = System.nanoTime()
    imp = fn(*args, **kwargs)
    t1 = System.nanoTime()
    times.append(t1 - t0)
  print "min: %.2f ms, max: %.2f ms, mean: %.2f ms" % (min(times) / 1000000.0, max(times) / 1000000.0, sum(times)/(len(times) * 1000000.0))

# Tested: takes ~26 ms
timeit(test, ared, agreen, ablue, easy=True)

# Compare with ImageJ:
def testImageJ(imp):
  return ImagePlus("HSB stack", imp.getProcessor().getHSBStack())

# Tested: takes ~0.7 ms
timeit(testImageJ, IJ.getImage())


# Test that easy=False shows the correct image
imp = test(ared, agreen, ablue, easy=False)
imp.show()


# Conclusion: the execution time is at least 30 times slower with ImgMath than plan ImageJ.
# To be fair, ImgMath computes some things twice, and some 3 times, because it can't share
# computation results across hue, saturation and brightness.
# At least the results are correct

# Compare with plain jython
def testJython(imgred, imggreen, imgblue):
  width, height = rgb.dimension(0), rgb.dimension(1)
  hb = zeros(width * height, 'f')
  sb = zeros(width * height, 'f')
  bb = zeros(width * height, 'f')
  cred = imgred.cursor()
  cgreen = imggreen.cursor()
  cblue = imgblue.cursor()
  i = 0
  while cred.hasNext():
    r = cred.next().getRealFloat()
    g = cgreen.next().getRealFloat()
    b = cblue.next().getRealFloat()
    cmax = max(r, g, b)
    cmin = min(r, g, b)
    bb[i] = cmax / 255.0
    if 0 != cmax:
      sb[i] = (cmax - cmin) / cmax
    # Else leave sb[i] at zero
    if 0 == sb[i]:
      h = 0
    else:
      span = cmax - cmin
      redc = (cmax - r) / span
      greenc = (cmax - g) / span
      bluec = (cmax - b) / span
      if r == cmax:
        h = bluec - greenc
      elif g == cmax:
        h = 2.0 + redc - bluec
      else:
        h = 4.0 + greenc - redc
      h /= 6.0
      if h < 0:
        h += 1.0
      hb[i] = h
    i += 1

  hh = ArrayImgs.floats(hb, [width, height])
  ss = ArrayImgs.floats(sb, [width, height])
  bb = ArrayImgs.floats(bb, [width, height])
  return Views.stack(hh, ss, bb)

# Takes: 214 ms. Almost 10x that of ImgMath, and 300x plain ImageJ.
#timeit(testJython, ared, agreen, ablue)

IL.wrap(testJython(ared, agreen, ablue), "HSB jython").show()