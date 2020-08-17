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



imp = WindowManager.getImage("180-220-sub512x512-30.tif") # IJ.getImage() # e.g. 8-bit EM of Drosophila neurons 180-220-sub512x512-30.tif
#imp = IJ.openImage("/home/albert/lab/TEM/abd/microvolumes/Seg/180-220-sub/180-220-sub512x512-30.tif")
img = IL.wrap(imp)

# Classify pixels as membrane or not
from weka.core import SerializationHelper, DenseInstance, Instances, Attribute
from jarray import array
from java.util import ArrayList
from net.imglib2.view import Views
from net.imglib2.img.array import ArrayImgs

classifier = SerializationHelper.read("/tmp/svm-em-mem-mit")

attributes = ArrayList()
for name in classifier.attributeNames()[0][1]:
  attributes.add(Attribute(name))
attributes.add(Attribute("class", ["membrane", "mit-boundary", "mit-inside", "cytoplasm"]))
info = Instances("structure", attributes, 1)
info.setClassIndex(len(attributes) -1)

opImgs = [compute(op).into(ArrayImgs.floats([img.dimension(0), img.dimension(1)])) for op in filterBank(img)]
cs_opImgs = Views.collapse(Views.stack(opImgs))

result = ArrayImgs.floats([img.dimension(0), img.dimension(1)])
cr = result.cursor()
cop = Views.iterable(cs_opImgs).cursor()

while cr.hasNext():
  tc = cop.next()
  vector = array((tc.get(i).getRealDouble() for i in xrange(len(opImgs))), 'd')
  di = DenseInstance(1.0, vector)
  di.setDataset(info) # the list of attributes
  cr.next().setReal(classifier.classifyInstance(di))

IL.wrap(result, "result").show()

