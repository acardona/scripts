from ij import IJ, ImagePlus

# Fetch an RGB image stack
imp_rgb = IJ.getImage() # IJ.openImage("http://imagej.nih.gov/ij/images/flybrain.zip")

# Define a threshold for the red channel: any values at or above
#    in the green channel will be placed into a new image
threshold = 119


# Example 1: with ImageCalculator
from ij.process import ImageProcessor
from ij.plugin import ChannelSplitter, ImageCalculator

# Split color channels
red, green, blue = ChannelSplitter().split(imp_rgb) # 3 ImagePlus
# Set threshold for each slice
for index in xrange(1, red.getNSlices() + 1):
  bp = red.getStack().getProcessor(index)
  #bp.setThreshold(threshold, 255, ImageProcessor.BLACK_AND_WHITE_LUT)
  bp.threshold(threshold) # mask is 0, background is 255
# Apply threshold: convert each slice to a mask (only 0 or 255 pixel values)
#IJ.run(red, "Convert to Mask", "method=Default background=Dark black")
red.show()

green_under_red_mask = ImageCalculator().run("and create stack", red, green)

green_under_red_mask.show()

"""
# Example 2: with ImgLib2 LoopBuilder
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.converter import Converters
from net.imglib2.img.array import ArrayImgs
from net.imglib2.util import Intervals
from net.imglib2.loops import LoopBuilder

img = IL.wrap(imp_rgb) # an ARGBType Img
red   = Converters.argbChannel(img, 1) # a view of the ARGB red channel
green = Converters.argbChannel(img, 2) # a view of the ARGB green channel
img_sub = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(img))    # the img to store the result

class Consumer(LoopBuilder.TriConsumer):
  def accept(self, r, g, s):
    s.setInteger(g.getInteger() if r.getInteger() >= threshold else 0)

LoopBuilder.setImages(red, green, img_sub).forEachPixel(Consumer())

IL.wrap(img_sub, "LoopBuilder").show()
"""

# Example 2b: with ImgLib2 LoopBuilder using a clojure-defined TriConsumer
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.converter import Converters
from net.imglib2.img.array import ArrayImgs
from net.imglib2.util import Intervals
from net.imglib2.loops import LoopBuilder
from org.scijava.plugins.scripting.clojure import ClojureScriptEngine

img = IL.wrap(imp_rgb) # an ARGBType Img
red   = Converters.argbChannel(img, 1) # a view of the ARGB red channel
green = Converters.argbChannel(img, 2) # a view of the ARGB green channel
img_sub = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(img))    # the img to store the result

code = """
(deftype Consumer [^long threshold]
  %s
  (accept [self red green result] ; can't type-hint, doesn't find matching method
    (let [^%s r red
          ^%s g green
          ^%s s result]
      (.setInteger s (if (>= (.getInteger r) threshold)
                       (.getInteger g)
                       0)))))
""" % ((LoopBuilder.TriConsumer.getName(),) \
      + tuple(a.randomAccess().get().getClass().getName() for a in [red, green, img_sub]))

clj = ClojureScriptEngine()
Consumer = clj.eval(code) # returns a class

LoopBuilder.setImages(red, green, img_sub).forEachPixel(Consumer(threshold))

IL.wrap(img_sub, "LoopBuilder").show()
# Takes 10 seconds!! An eternity compared to the other two fast methods



# Example 3: with Imglib2 ImgMath
from net.imglib2.algorithm.math.ImgMath import compute, IF, THEN, ELSE, greaterThan
from net.imglib2.algorithm.math.abstractions import Util
from net.imglib2.converter import Converters
from net.imglib2.img.array import ArrayImgs
from net.imglib2.util import Intervals
from net.imglib2.img.display.imagej import ImageJFunctions as IL

img = IL.wrap(imp_rgb) # an ARGBType Img
red   = Converters.argbChannel(img, 1) # a view of the ARGB red channel
green = Converters.argbChannel(img, 2) # a view of the ARGB green channel

operation = IF(greaterThan(red, threshold -1),
               THEN(green),
               ELSE(0))

print Util.hierarchy(operation)

IL.wrap(operation.view(), "ImgMath view").show()

img_sub = compute(operation).into(ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(img)))

IL.wrap(img_sub, "ImgMath img").show()