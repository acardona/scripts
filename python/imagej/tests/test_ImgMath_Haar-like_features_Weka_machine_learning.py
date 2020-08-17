from net.imglib2.algorithm.math.ImgMath import compute, block, sub, add, maximum, offset
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.algorithm.integral import IntegralImg
from net.imglib2.type.numeric.integer import UnsignedLongType
from net.imglib2.type.numeric.real import FloatType, DoubleType
from net.imglib2.view import Views
from net.imglib2.algorithm.math.abstractions import Util
from ij import IJ, WindowManager
import re


def shift(corners, dx, dy):
  return [[x + dx, y + dy] for x, y in corners]


def filterBank(img, sumType=UnsignedLongType(), converter=Util.genericRealTypeConverter()):
  """ Haar-like features from Viola and Jones
      tuned to identify neuron membranes in electron microscopy. """
  # Create the integral image, stored as 64-bit
  alg = IntegralImg(img, sumType, converter)
  alg.process()
  integralImg = alg.getResult()
  imgE = Views.extendBorder(integralImg)

  # corners of a 4x8 or 8x4 rectangular block where 0,0 is the top left
  bs = 4 # short side
  bl = 8 # long side
  cornersV = [[0,     0], [bs -1,      0],  # Vertical
              [0, bl -1], [bs -1, bl - 1]]
  cornersH = [[0,     0], [bl -1,      0],  # Horizontal
              [0, bs -1], [bl -1, bs - 1]]

  # Two adjacent vertical rectangles 4x8 - 4x8 centered on the pixel
  blockVL = block(imgE, shift(cornersV, -bs, -bl/2))
  blockVR = block(imgE, shift(cornersV,   0, -bl/2))
  op1 = sub(blockVL, blockVR)
  op2 = sub(blockVR, blockVL)

  # Two adjacent horizontal rectangles 8x4 - 8x4 centered on the pixel
  blockHT = block(imgE, shift(cornersH, -bs, -bl/2))
  blockHB = block(imgE, shift(cornersH, -bs,     0))
  op3 = sub(blockHT, blockHB)
  op4 = sub(blockHB, blockHT)

  # Two bright-black-bright vertical features 4x8 - 4x8 - 4x8
  block3VL = block(imgE, shift(cornersV, -bs -bs/2, -bl/2))
  block3VC = block(imgE, shift(cornersV,     -bs/2, -bl/2))
  block3VR = block(imgE, shift(cornersV,      bs/2, -bl/2))
  op5 = sub(block3VC, block3VL, block3VR) # center minus sides
  op6 = sub(add(block3VL, block3VR), block3VC) # sides minus center

  # Two bright-black-bright horizontal features 8x4 / 8x4 / 8x4
  block3HT = block(imgE, shift(cornersH, -bl/2, -bs -bs/2))
  block3HC = block(imgE, shift(cornersH, -bl/2,     -bs/2))
  block3HB = block(imgE, shift(cornersH, -bl/2,      bs/2))
  op7 = sub(block3HC, block3HT, block3HB) # center minus top and bottom
  op8 = sub(add(block3HT, block3HB), block3HC) # top and bottom minus center

  # Combination of vertical and horizontal edge detection
  op9 = maximum(op1, op3)
  op10 = maximum(op6, op8)

  # corners of a square block where 0,0 is at the top left
  cornersS = [[0,  0], [bs,  0],
              [0, bs], [bs, bs]]

  # 2x2 squares for oblique edge detection
  blockSTL = block(imgE, shift(cornersS, -bs, -bs)) # top left
  blockSTR = block(imgE, shift(cornersS,   0, -bs)) # top right
  blockSBL = block(imgE, shift(cornersS, -bs,   0)) # bottom left
  blockSBR = block(imgE, cornersS)                  # bottom right
  op11 = sub(add(blockSTL, blockSBR), blockSTR, blockSBL)
  op12 = sub(add(blockSTR, blockSBL), blockSTL, blockSBR)

  # Combination of vertical, horizontal and oblique edge detection
  op13 = maximum(op1, op3, op6, op8, op11, op12)

  # Edge detectors: sum of 3 adjacent pixels (not dividing by the other 6
  # to avoid penalizing Y membrane configurations)
  op14 = maximum(add(offset(op13, [-1, -1]), op13, offset(op13, [ 1, 1])),
                 add(offset(op13, [ 0, -1]), op13, offset(op13, [ 0, 1])),
                 add(offset(op13, [ 1, -1]), op13, offset(op13, [-1, 1])),
                 add(offset(op13, [-1,  0]), op13, offset(op13, [ 1, 0])))

  # Return a list of all ops
  #return [ob for name, ob in vars().iteritems() if re.match(r"^op\d+$", name)]
  # Ordered
  return [op1, op2, op3, op4, op5, op6, op7, op8, op9, op10, op11, op12, op13, op14]


"""
for name, op in ((name, eval(name)) for name in vars() if re.match(r"^op\d+$", name)):
  # For development:
  if WindowManager.getImage(name):
    continue # don't open
  #
  opimp = IL.wrap(op.view(FloatType()), name)
  opimp.getProcessor().resetMinAndMax()
  opimp.show()
"""


# Create synthetic training data: blurred edges of the same thickness as membranes
from java.util import Arrays
from ij.process import FloatProcessor, ImageProcessor
from ij import ImagePlus, ImageStack
from ij.plugin.filter import GaussianBlur
from ij.gui import Line

def syntheticEM(fillLineIndices,
                width, height,
                lineValue, backgroundValue,
                sigma=1.4,
                noise=False,
                noise_sd=25.0,
                show=False):
  ip = FloatProcessor(width, height)
  pixels = ip.getPixels()
  # Fill background
  Arrays.fill(pixels, backgroundValue)
  # Paint black horizontal line
  for i in fillLineIndices:
    Arrays.fill(pixels, i * width, (i + 1) * height, lineValue)
  # Blur
  GaussianBlur().blurFloat(ip, 0, sigma, 0.02)
  if noise:
    ip.noise(noise_sd)
  ip.setMinAndMax(0, 255)
  imp = ImagePlus("synth", ip)
  if show:
    imp.show()
  return imp


width, height = 32, 32
fillValue = 0
backgroundValue = 172

synthMembrane = syntheticEM(xrange(14, 17), width, height, fillValue, backgroundValue)
synthMitochondriaBoundary = syntheticEM(xrange(0, 16), width, height, fillValue, backgroundValue)


def generateRotations(imp, backgroundValue, degrees=90):
  # Generate stack of rotations with noise
  ip = imp.getProcessor()
  rotations = ImageStack(ip.getWidth(), ip.getHeight())
  for i in xrange(degrees / 10 + 1):
    ipr = ip.duplicate()
    ipr.setInterpolationMethod(ImageProcessor.BILINEAR)
    ipr.setBackgroundValue(backgroundValue)
    ipr.rotate(i * 10)
    ipr.noise(25) # sd = 25
    rotations.addSlice(ipr)
  return rotations

imp_membrane = ImagePlus("synth rot membrane", generateRotations(synthMembrane, 172, degrees=170))
imp_mit_boundary = ImagePlus("synth rot mitochondria boundary",
                             generateRotations(synthMitochondriaBoundary, 172, degrees=350))

imp_membrane.show()
imp_mit_boundary.show()



# Use these to train an SVM (support vector machine)
from weka.core import Attribute, Instances, DenseInstance
from weka.classifiers.functions import SMO
from weka.core import SerializationHelper
from jarray import zeros
from java.util import ArrayList
from net.imglib2.img.array import ArrayImgs
from net.imglib2 import FinalInterval
from net.imglib2.util import Intervals


# Turn all stack slices of synthetic data each into an ArrayImg
def slicesAsArrayImgs(imp):
  stack = imp.getStack()
  return [IL.wrap(ImagePlus("", stack.getProcessor(i+1)))
          for i in xrange(stack.getSize())]

synth_imgs_membrane = slicesAsArrayImgs(imp_membrane)
synth_imgs_mit_boundary = slicesAsArrayImgs(imp_mit_boundary)


# Define a WEKA Attribute for each feature (each op, 14 total plus the class)
attribute_names = ["attr-%i" % (i+1) for i in xrange(14)]
attributes = ArrayList()
for name in attribute_names:
  attributes.add(Attribute(name))
# Add an attribute at the end for the classification classes
attributes.add(Attribute("class", ["membrane", "mit-boundary", "mit-inside", "cytoplasm"]))

# Create the training data structure
# which consists of 16 samples for each membrane training image rotation
# and 4 samples for each mitochondrial boundary image rotation
# and times 2 to then add examples of the other, non-membrane class
training_data = Instances("training", attributes,
                          (len(synth_imgs_membrane) * 16 + len(synth_imgs_mit_boundary) * 4) * 2)
training_data.setClassIndex(len(attributes) -1)

def populateInstances(instances, synth_imgs, class_index, mins, maxs):
  # Populate the training data: create the filter bank for each feature image
  # by reading values from the interval defined by mins and maxs
  target = ArrayImgs.floats([width, height])
  interval = FinalInterval(mins, maxs)
  n_samples = Intervals.numElements(interval)
  for img in synth_imgs:
    vectors = [zeros(len(attributes), 'd') for _ in xrange(n_samples)]
    for k, op in enumerate(filterBank(img, sumType=DoubleType())):
      imgOp = compute(op).into(target)
      for i, v in enumerate(Views.interval(imgOp, interval)):
        vectors[i][k] = v.getRealDouble()
    for vector in vectors:
      vector[-1] = class_index
      instances.add(DenseInstance(1.0, vector))

# pick pixels on the black line for class 0 (membrane), 4x4
populateInstances(training_data, synth_imgs_membrane, 0, [14, 14], [17, 17])
# pick pixels in the very center for class 1 (mitochondrial boundary), 2x2
populateInstances(training_data, synth_imgs_mit_boundary, 1, [15, 15], [16, 16])


# Populate the training data for class "other" from two images
# entirely filled with background or foreground plus noise
target = ArrayImgs.floats([width, height])
interval = FinalInterval([14, 14], [17, 17])
n_samples = Intervals.numElements(interval)
for ci, v in enumerate([fillValue, backgroundValue]):
  for _ in xrange(training_data.size() / 4):  # the other 2/4 are the membrane and mit boundary
    other = syntheticEM([], width, height, 0, v, noise=True)
    vectors = [zeros(len(attributes), 'd') for _ in xrange(n_samples)]
    for k, op in enumerate(filterBank(IL.wrap(other), sumType=DoubleType())):
      imgOp = compute(op).into(target)
      for i, v in enumerate(Views.interval(imgOp, interval)):
        vectors[i][k] = v.getRealDouble()
    for vector in vectors:
      vector[-1] = ci + 2 # class index
      training_data.add(DenseInstance(1.0, vector))

# Create a classifier: support vector machine (SVM, an SMO in WEKA)
classifier = SMO()
classifier.buildClassifier(training_data)
print classifier.toString()

# Save the trained classifier for later
SerializationHelper.write("/tmp/svm-em-mem-mit", classifier)


"""
imp = WindowManager.getImage("180-220-sub512x512-30.tif") # IJ.getImage() # e.g. 8-bit EM of Drosophila neurons 180-220-sub512x512-30.tif
#imp = IJ.openImage("/home/albert/lab/TEM/abd/microvolumes/Seg/180-220-sub/180-220-sub512x512-30.tif")
img = IL.wrap(imp)
"""
    



"""
from hr.irb.fastRandomForest import FastRandomForest
from weka.core import Attribute, Instances, DenseInstance

rf = FastRandomForest()
rf.setNumTrees(200)
rf.setNumFeatures(2)
rf.seed(67778)
rf.setNumThreads(2)

# Construct numeric attributes
names = ["vertical edge", "horizontal edge", "diagonal edge 1", "diagonal edge 2", "class"]
attributes = [Attribute(name) for name in names]

# 100 examples for training 
instances = Instances("segment", attributes, 10)
instances.setClassIndex(len(attributes) -1)
"""







