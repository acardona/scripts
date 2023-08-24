from ij import IJ, ImagePlus
from ij.process import FloatProcessor
from ij.gui import OvalRoi, Roi
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from itertools import izip
from net.imglib2.algorithm.math.ImgMath import compute, block, IF, THEN, ELSE, LT, \
                                               sub, div, let, power, mul
from net.imglib2.algorithm.integral import IntegralImg
from net.imglib2.type.numeric.integer import UnsignedLongType, UnsignedByteType
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.view import Views
from net.imglib2.algorithm.math.abstractions import Util
from net.imglib2.img.array import ArrayImgs
from jarray import array
from java.util import ArrayList
from weka.core import SerializationHelper, DenseInstance, Instances, Attribute
from weka.classifiers.functions import SMO


# Synthetic training data: a bright blob on a black background
width, height = 64, 64
fp = FloatProcessor(width, height)
synth = ImagePlus("synth blob", fp)

fp.setColor(0)
fp.fill()
fp.setColor(255)
oval = OvalRoi(width/4, height/4, width/2, height/2)
fp.fill(oval)
fp.noise(25)

synth.show()

def asIntCoords(roi, asFloat=True, limit=-1):
  """ asFloat: enables sampling the ROI at e.g. 1.0 pixels intervals.
      limit: crop the number of points. """
  pol = roi.getInterpolatedPolygon(1.0, False) if asFloat else roi.getPolygon()
  coords = [map(int, points) for points in [pol.xpoints, pol.ypoints]]
  return coords[0][:limit], coords[1][:limit]

# Positive examples: an oval one pixel smaller in radius to sample
# from the inside boundary, to ensure nearby touching blobs are segmented separately
bounds = oval.getBounds()
oval_inside = OvalRoi(bounds.x + 1, bounds.y + 1, bounds.width - 1, bounds.height - 1)
blob_boundary = asIntCoords(oval_inside, asFloat=False)
print len(blob_boundary[0])

# Negative examples: as many as positive ones,
# well oustide the oval but also far from the border
margin = min(width/8, height/8)
background_roi = Roi(margin, margin, width - margin, height - margin)
background = asIntCoords(background_roi, asFloat=True, limit=len(blob_boundary[0]))

class_names = ["background", "boundary"]

def examples():
  """ """
  for class_index, (xs, ys) in enumerate([background, blob_boundary]):
    for x, y in izip(xs, ys):
      yield [x, y], class_index



def filterBankBlockStatistics(img, block_width=5, block_height=5,
                              sumType=UnsignedLongType(),
                              converter=Util.genericRealTypeConverter()):
  # corners of a block centered at the pixel
  block_width  = int(block_width)
  block_height = int(block_height)
  w0 = -block_width/2  # e.g. -2 when block_width == 4 and also when block_width == 5
  h0 = -block_height/2
  decX = 1 if 0 == block_width  % 2 else 0
  decY = 1 if 0 == block_height % 2 else 0
  w1 = block_width/2  - decX # e.g. 2 when block_width == 5 but 1 when block_width == 4
  h1 = block_height/2 - decY
  
  corners = [[w0, h0], [w1, h0],
             [w0, h1], [w1, h1]]

  # Create the integral image, stored as 64-bit
  alg = IntegralImg(img, sumType, converter)
  alg.process()
  integralImgE = Views.extendBorder(alg.getResult())
  
  # Create the integral image of squares, stored as 64-bit
  sqimg = compute(power(img, 2)).view(sumType)
  algSq = IntegralImg(sqimg, sumType, converter)
  algSq.process()
  integralImgSqE = Views.extendBorder(algSq.getResult())

  # block mean: creates holes in blurred membranes
  # TODO: this should use integralImgE, not integralImgSqE ! Yet it works better this way with the mean of squares.
  opMean = div(block(integralImgSqE, corners), block_width * block_height)
  
  # block variance: sum of squares minus square of sum
  opVariance = sub(block(integralImgSqE, corners), power(block(integralImgE, corners), 2))
  opVarianceNonZero = let("var", opVariance,
                          IF(LT("var", 0),
                             THEN(0),
                             ELSE("var")))

  return [opMean, opVarianceNonZero]


def createTrainingData(img, samples, class_names, ops, n_samples=0):
  """ img: a 2D RandomAccessibleInterval.
      samples: a sequence of long[] (or int numeric sequence or Localizable)
               and class_index pairs; can be a generator.
      class_names: a list of class names, as many as different class_index.
      ops: the sequence of ImgMath ops to apply to the img.
      n_samples: optional, the number of samples (in case samples is e.g. a generator).

      Return an instance of WEKA Instances, each consisting in a vector
      of values (one per op) for every sample over the img.
  """
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

  # Populate the training data structure.
  # First create a RandomAccess on a Composite view of FloatType views of every ImgMath op
  # (i.e. no need to compute each op for all pixels of the img!
  #  Will instead compute only for the sampled pixels.)
  opViews = [op.view(FloatType()) for op in ops]
  ra = Views.collapse(Views.stack(opViews)).randomAccess()

  # Then iterate each sample to acquire the vector of values as computed with the ops
  for position, class_index in samples:
    ra.setPosition(position)
    tc = ra.get()
    vector = array((tc.get(i).getRealDouble() for i in xrange(len(opViews))), 'd')
    vector += array([class_index], 'd') # inefficient, but easy
    training_data.add(DenseInstance(1.0, vector))

  return training_data


def trainClassifier(classifier, img, samples, class_names, ops, n_samples=0, filepath=None):
  classifier.buildClassifier(createTrainingData(img, samples, class_names, ops, n_samples=n_samples))

  # Save the trained classifier for later
  if filepath:
    SerializationHelper.write(filepath, classifier)

  return classifier


def createSMOClassifier(img, samples, class_names, ops, n_samples=0, filepath=None):
  """ Create a classifier: support vector machine (SVM, an SMO in WEKA)
      
      img: a 2D RandomAccessibleInterval.
      samples: a sequence of long[] (or int numeric sequence or Localizable)
               and class_index pairs; can be a generator.
      class_names: a list of class names, as many as different class_index.
      ops: a list of ImgMath operations, each one is a filter on the img.
      n_samples: optional, the number of samples (in case samples is e.g. a generator).
      save_to_file: optional, a filename for saving the learnt classifier.
  """
  return trainClassifier(SMO(), img, samples, class_names, ops,
                         n_samples=n_samples, filepath=None)


def classify(img, classifier, class_names, ops, distribution_class_index=-1):
  """ img: a 2D RandomAccessibleInterval.
      classifier: a WEKA Classifier instance, like SMO or FastRandomForest, etc. Any.
                  If it's a string, interprets it as a file path and attempts to deserialize
                  a previously saved trained classifier.
      class_names: the list of names of each class to learn.
      ops: the filter bank of ImgMath ops for the img.
      distribution_class_index: defaults to -1, meaning return the class index for each pixel.
                                When larger than -1, it's interpreted as a class index, and
                                returns instead the floating-point value of each pixel in
                                the distribution of that particular class index. """
  if type(classifier) == str:
    classifier = SerializationHelper.read(classifier)
  
  attributes = ArrayList()
  for i in xrange(len(ops)):
    attributes.add(Attribute("attr-%i" % i))
  attributes.add(Attribute("class", class_names))

  # Umbrella datastructure "Instances" containing the attributes of each "Instance" to classify
  # where an "Instance" will be each pixel in the image.
  info = Instances("structure", attributes, 1)
  info.setClassIndex(len(attributes) -1)

  # Compute all ops and stack them into an imglib2 image of CompositeType
  # where every "pixel" is the vector of all op values for that pixel
  opImgs = [compute(op).into(ArrayImgs.floats([img.dimension(0), img.dimension(1)]))
            for op in ops]
  cs_opImgs = Views.collapse(Views.stack(opImgs))

  classification = ArrayImgs.floats([img.dimension(0), img.dimension(1)])
  cr = classification.cursor()
  cop = Views.iterable(cs_opImgs).cursor()

  while cr.hasNext():
    tc = cop.next()
    vector = array((tc.get(i).getRealDouble() for i in xrange(len(opImgs))), 'd')
    di = DenseInstance(1.0, vector)
    di.setDataset(info) # the list of attributes
    if distribution_class_index > -1:
      cr.next().setReal(classifier.distributionForInstance(di)[distribution_class_index])
    else:
      cr.next().setReal(classifier.classifyInstance(di))

  return classification


# The training image: our synthetic blob
img_training = IL.wrap(synth)

# The test image: the sample image "blobs.gif"
blobs_imp = IJ.openImage("http://imagej.nih.gov/ij/images/blobs.gif")
img_test = IL.wrap(blobs_imp)

# The same filter bank for each
ops_training = filterBankBlockStatistics(img_training)
ops_test = filterBankBlockStatistics(img_test)

# The WEKA support vector machine (SVM) named SMO
classifierSMO = createSMOClassifier(img_training, examples(), class_names, ops_training,
                                    n_samples=len(blob_boundary[0]),
                                    filepath="/tmp/svm-blobs-segmentation")
print classifierSMO.toString()

# Classify pixels as blob boundary or not
resultSMO = classify(img_test, classifierSMO, class_names, ops_test)
IL.wrap(resultSMO, "segmentation via WEKA SVM SMO").show()


# Better display as a stack
stack = Views.stack(img_test,
                    compute(mul(resultSMO, 255)).view(UnsignedByteType()))
IL.wrap(stack, "stack").show()