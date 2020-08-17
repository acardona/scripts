from net.imglib2.algorithm.math.ImgMath import compute, block, sub, add, maximum, offset
from net.imglib2.algorithm.integral import IntegralImg
from net.imglib2.type.numeric.integer import UnsignedLongType
from net.imglib2.view import Views
from net.imglib2.algorithm.math.abstractions import Util
from net.imglib2.img.array import ArrayImgs
from weka.core import SerializationHelper, DenseInstance, Instances, Attribute
from hr.irb.fastRandomForest import FastRandomForest
from jarray import array
from java.util import ArrayList
from util import numCPUs


def filterBank(img, bs=4, bl=8, sumType=UnsignedLongType(), converter=Util.genericRealTypeConverter()):
  """ Haar-like features from Viola and Jones using integral images
      tuned to identify neuron membranes in electron microscopy.
      bs: length of the short side of a block
      bl: length of the long side of a block
      sumType: the type with which to add up pixel values in the integral image
      converter: for the IntegralImg, to convert from input to sumType
  """
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

  def shift(corners, dx, dy):
    return [[x + dx, y + dy] for x, y in corners]

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

  # Return an ordered list of all ops
  return [op1, op2, op3, op4, op5, op6, op7, op8, op9, op10, op11, op12, op13, op14]


# Use these to train an SVM (support vector machine)
from weka.core import Attribute, Instances, DenseInstance
from weka.classifiers.functions import SMO
from weka.core import SerializationHelper
from java.util import ArrayList
from net.imglib2.img.array import ArrayImgs
from jarray import array


def createTrainingData(img, samples, class_names, n_samples=0, filterBank=filterBank):
  """ img: a 2D RandomAccessibleInterval.
      samples: a sequence of long[] (or int numeric sequence or Localizable) and class_index pairs; can be a generator.
      n_samples: optional, the number of samples (in case samples is e.g. a generator).
      class_names: a list of class names, as many as different class_index.
      filterBank: optional, the sequence of ImgMath ops to apply to the img.
      save_to_file: optional, a filename for saving the learnt classifier.

      return an instance of WEKA Instances
  """
  ops = filterBank(img)

  if 0 == n_samples:
    n_samples = len(samples)
  
  # Define a WEKA Attribute for each feature (one for op in the filter bank, plus the class)
  attribute_names = ["attr-%i" % (i+1) for i in xrange(len(ops))]
  attributes = ArrayList()
  for name in attribute_names:
    attributes.add(Attribute(name))
  # Add an attribute at the end for the classification classes
  attributes.add(Attribute("class", class_names))

  # Create the training data structure
  training_data = Instances("training", attributes, n_samples)
  training_data.setClassIndex(len(attributes) -1)

  opImgs = [compute(op).into(ArrayImgs.floats([img.dimension(0), img.dimension(1)])) for op in ops]
  ra = Views.collapse(Views.stack(opImgs)).randomAccess()

  for position, class_index in samples:
    ra.setPosition(position)
    tc = ra.get()
    vector = array((tc.get(i).getRealDouble() for i in xrange(len(opImgs))), 'd')
    vector += array([class_index], 'd')
    training_data.add(DenseInstance(1.0, vector))

  return training_data


def trainClassifier(classifier, img, samples, class_names, n_samples=0, filterBank=filterBank, filepath=None):
  classifier.buildClassifier(createTrainingData(img, samples, class_names, n_samples=n_samples, filterBank=filterBank))

  # Save the trained classifier for later
  if filepath:
    SerializationHelper.write(filepath, classifier)

  return classifier

def createSMOClassifier(img, samples, class_names, n_samples=0, filterBank=filterBank, filepath=None):
  """ Create a classifier: support vector machine (SVM, an SMO in WEKA)
      
      img: a 2D RandomAccessibleInterval.
      samples: a sequence of long[] (or int numeric sequence or Localizable) and class_index pairs; can be a generator.
      n_samples: optional, the number of samples (in case samples is e.g. a generator).
      class_names: a list of class names, as many as different class_index.
      filterBank: optional, the sequence of ImgMath ops to apply to the img.
      save_to_file: optional, a filename for saving the learnt classifier.
  """
  return trainClassifier(SMO(), img, samples, class_names, n_samples=n_samples, filterBank=filterBank, filepath=None)


def createRandomForestClassifier(img, samples, class_names, n_samples=0, filterBank=filterBank, filepath=None, params={}):
  rf = FastRandomForest()
  rf.setNumTrees(params.get("n_trees", 200))
  rf.setNumFeatures(params.get("n_features", 2))
  #rf.seed(params.get("seed", 67778))
  rf.setNumThreads(params.get("n_threads", numCPUs()))
  return trainClassifier(rf, img, samples, class_names, n_samples=n_samples, filterBank=filterBank, filepath=filepath)




def classify(img, classifier_filepath, class_names, filterBank=filterBank):
  """ Deserialize a classifier and classify every pixel of the image.
  """
  classifier = SerializationHelper.read(classifier_filepath)
  ops = filterBank(img)
  
  attributes = ArrayList()
  for i in xrange(len(ops)):
    attributes.add(Attribute("attr-%i" % i))
  #for name in classifier.attributeNames()[0][1]:
  #  attributes.add(Attribute(name))
  attributes.add(Attribute("class", class_names))
  
  info = Instances("structure", attributes, 1)
  info.setClassIndex(len(attributes) -1)

  opImgs = [compute(op).into(ArrayImgs.floats([img.dimension(0), img.dimension(1)])) for op in ops]
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

  return result
