from net.imglib2.algorithm.math.ImgMath import compute, block, sub, add, maximum, offset, \
                                               IF, THEN, ELSE, AND, GT, LT, div, let, power, mul
from net.imglib2.algorithm.integral import IntegralImg
from net.imglib2.type.numeric.integer import UnsignedLongType
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.view import Views
from net.imglib2.algorithm.math.abstractions import Util
from net.imglib2.img.array import ArrayImgs
from net.imglib2.util import Intervals
from net.imglib2.realtransform import AffineTransform2D
from net.imglib2.realtransform import RealViews as RV
from net.imglib2.interpolation.randomaccess import NLinearInterpolatorFactory
from itertools import product, repeat
from jarray import array, zeros
from java.util import ArrayList
from math import radians, floor, ceil
from weka.core import SerializationHelper, DenseInstance, Instances, Attribute
from weka.classifiers.functions import SMO, MultilayerPerceptron
from trainableSegmentation import WekaSegmentation
from hr.irb.fastRandomForest import FastRandomForest
from util import numCPUs
import sys
from net.imglib2.img.display.imagej import ImageJFunctions as IL


def shift(corners, dx, dy):
  return [[x + dx, y + dy] for x, y in corners]

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
  cornersV = [[0,     0], [bs -1,      0],  # Vertical
              [0, bl -1], [bs -1, bl - 1]]
  cornersH = [[0,     0], [bl -1,      0],  # Horizontal
              [0, bs -1], [bl -1, bs - 1]]

  # Two adjacent vertical rectangles 4x8 - 4x8 centered on the pixel
  blockVL = block(imgE, shift(cornersV, -bs, -bl/2))
  blockVR = block(imgE, shift(cornersV,   0, -bl/2))
  op1 = let("VL", blockVL,
            "VR", blockVR,
            IF(GT("VL", "VR"),
               THEN(div("VR", "VL")),
               ELSE(div("VL", "VR"))))
  #op1 = sub(blockVL, blockVR)
  
  #op2 = sub(blockVR, blockVL)

  # Two adjacent horizontal rectangles 8x4 - 8x4 centered on the pixel
  blockHT = block(imgE, shift(cornersH, -bs, -bl/2))
  blockHB = block(imgE, shift(cornersH, -bs,     0))
  op3 = let("HT", blockHT,
            "HB", blockHB,
            IF(GT("HT", "HB"),
               THEN(div("HB", "HT")),  # div works better than sub
               ELSE(div("HT", "HB"))))
  #op3 = sub(blockHT, blockHB)
  #op4 = sub(blockHB, blockHT)

  # Two bright-black-bright vertical features 4x8 - 4x8 - 4x8
  block3VL = block(imgE, shift(cornersV, -bs -bs/2, -bl/2))
  block3VC = block(imgE, shift(cornersV,     -bs/2, -bl/2))
  block3VR = block(imgE, shift(cornersV,      bs/2, -bl/2))
  op5 = let("3VL", block3VL,
            "3VC", block3VC,
            "3VR", block3VR,
            IF(AND(GT("3VL", "3VC"),
                   GT("3VR", "3VC")),
               THEN(sub(add("3VL", "3VR"), "3VC")), # like Viola and Jones 2001
               ELSE(div(add("3VL", "3VC", "3VR"), 3)))) # average block value
  # Purely like Viola and Jones 2001: work poorly for EM membranes
  #op5 = sub(block3VC, block3VL, block3VR) # center minus sides
  #op6 = sub(add(block3VL, block3VR), block3VC) # sides minus center

  # Two bright-black-bright horizontal features 8x4 / 8x4 / 8x4
  block3HT = block(imgE, shift(cornersH, -bl/2, -bs -bs/2))
  block3HC = block(imgE, shift(cornersH, -bl/2,     -bs/2))
  block3HB = block(imgE, shift(cornersH, -bl/2,      bs/2))
  op7 = let("3HT", block3HT,
            "3HC", block3HC,
            "3HB", block3HB,
            IF(AND(GT("3HT", "3HC"),
                   GT("3HB", "3HC")),
               THEN(sub(add("3HT", "3HB"), "3HC")), # like Viola and Jones 2001
               ELSE(div(add("3HT", "3HC", "3HB"), 3)))) # average block value
  # Purely like Viola and Jones 2001: work poorly for EM membranes
  #op7 = sub(block3HC, block3HT, block3HB) # center minus top and bottom
  #op8 = sub(add(block3HT, block3HB), block3HC) # top and bottom minus center

  # Combination of vertical and horizontal edge detection
  #op9 = maximum(op1, op3)
  #op10 = maximum(op6, op8)
  #op10 = maximum(op5, op7)


  """
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
  """

  # Combination of vertical, horizontal and oblique edge detection
  #op13 = maximum(op1, op3, op6, op8, op11, op12)
  #op13 = maximum(op1, op3, op5, op7, op11, op12) # combinations are terrible for RandomForest

  # Edge detectors: sum of 3 adjacent pixels (not dividing by the other 6
  # to avoid penalizing Y membrane configurations)
  """
  op14 = maximum(add(offset(op13, [-1, -1]), op13, offset(op13, [ 1, 1])),
                 add(offset(op13, [ 0, -1]), op13, offset(op13, [ 0, 1])),
                 add(offset(op13, [ 1, -1]), op13, offset(op13, [-1, 1])),
                 add(offset(op13, [-1,  0]), op13, offset(op13, [ 1, 0])))
  """

  #opMean, opVariance = filterBankBlockStatistics(img, integralImgE=imgE, sumType=sumType, converter=converter)

  # Return an ordered list of all ops
  #return [op1, op2, op3, op4, op5, op6, op7, op8, op9, op10, op11, op12, op13, op14]
  #return [op1, op3, op5, op7, opMean, opVariance]
  return [op1, op3, op5, op7]


def filterBankBlockStatistics(img, block_width=5, block_height=5,
                              integralImgE=None,
                              sumType=UnsignedLongType(),
                              converter=Util.genericRealTypeConverter()):
  # corners of a block centered at the pixel
  block_width = int(block_width)
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
  if not integralImgE:
    alg = IntegralImg(img, sumType, converter)
    alg.process()
    integralImgE = Views.extendBorder(alg.getResult())
  
  # Create the integral image of squares, stored as 64-bit
  sqimg = compute(power(img, 2)).view(sumType)
  algSq = IntegralImg(sqimg, sumType, converter)
  algSq.process()
  integralImgSqE = Views.extendBorder(algSq.getResult())

  # block mean: creates holes in blurred membranes
  opMean = div(block(integralImgSqE, corners), block_width * block_height)
  
  # block variance: sum of squares minus square of sum
  opVariance = sub(block(integralImgSqE, corners), power(block(integralImgE, corners), 2))
  opVarianceNonZero = let("var", opVariance,
                          IF(LT("var", 0),
                             THEN(0),
                             ELSE("var")))

  return [opMean, opVarianceNonZero]


def rotatedView(img, angle, enlarge=True, extend=Views.extendBorder):
  """ Return a rotated view of the image, around the Z axis,
      with an expanded (or reduced) interval view so that all pixels are exactly included.

      img: a RandomAccessibleInterval
      angle: in degrees
  """
  cx = img.dimension(0) / 2.0
  cy = img.dimension(1) / 2.0
  toCenter = AffineTransform2D()
  toCenter.translate(-cx, -cy)
  rotation = AffineTransform2D()
  # Step 1: place origin of rotation at the center of the image
  rotation.preConcatenate(toCenter)
  # Step 2: rotate around the Z axis
  rotation.rotate(radians(angle))
  # Step 3: undo translation to the center
  rotation.preConcatenate(toCenter.inverse())
  rotated = RV.transform(Views.interpolate(extend(img),
                                           NLinearInterpolatorFactory()), rotation)
  if enlarge:
    # Bounds:
    bounds = repeat((sys.maxint, 0)) # initial upper- and lower-bound values  
                                     # for min, max to compare against  
    transformed = zeros(2, 'f')
    for corner in product(*zip(repeat(0), Intervals.maxAsLongArray(img))):
      rotation.apply(corner, transformed)
      bounds = [(min(vmin, int(floor(v))), max(vmax, int(ceil(v))))
                for (vmin, vmax), v in zip(bounds, transformed)]
    minC, maxC = map(list, zip(*bounds)) # transpose list of 2 pairs
                                         # into 2 lists of 2 values
    imgRot = Views.zeroMin(Views.interval(rotated, minC, maxC))
  else:
    imgRot = Views.interval(rotated, img)
  return imgRot


def filterBankRotations(img,
                        angles=xrange(0, 46, 9), # sequence, in degrees
                        filterBankFn=filterBank, # function that takes an img as sole positional argument
                        outputType=FloatType()):
  """ img: a RandomAccessibleInterval.
      filterBankFn: the function from which to obtain a sequence of ImgMath ops.
      angles: a sequence of angles in degrees.
      outputType: for materializing rotated operations and rotating them back.

      For every angle, will prepare a rotated view of the image,
      then create a list of ops on the basis of that rotated view,
      then materialize each op into an image so that an unrotated view
      can be returned back.

      returns a list of unrotated views, each containing the values of applying
      each op to the rotated view. 
  """
  ops_rotations = []
  
  for angle in angles:
    imgRot = img if 0 == angle else rotatedView(img, angle)
    ops = filterBankFn(imgRot)

    # Materialize these two combination ops and rotate them back (rather, a rotated view)
    interval = Intervals.translate(img, [(imgRot.dimension(d) - img.dimension(d)) / 2
                                         for d in xrange(img.numDimensions())])
    for op in ops:
      imgOpRot = compute(op).intoArrayImg(outputType)
      if 0 == angle:
        ops_rotations.append(imgOpRot)
        continue
      # Rotate them back and crop view
      imgOpUnrot = rotatedView(imgOpRot, -angle, enlarge=False)
      imgOp = Views.zeroMin(Views.interval(imgOpUnrot, interval))
      #if angle == 0 or angle == 45:
      #  IL.wrap(imgOpRot, "imgOpRot angle=%i" % angle).show()
      #  IL.wrap(imgOpUnrot, "imgOpUnrot angle=%i" % angle).show()
      #  IL.wrap(imgOp, "imgOp angle=%i" % angle).show()
      ops_rotations.append(imgOp)
  
  return ops_rotations


def filterBankOrthogonalEdges(img,
                              bs=4,
                              bl=8,
                              sumType=UnsignedLongType(),
                              converter=Util.genericRealTypeConverter()):
  """ Haar-like features from Viola and Jones using integral images of a set of rotated images
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
  op5 = let("3VL", block3VL,
            "3VC", block3VC,
            "3VR", block3VR,
            IF(AND(GT("3VL", "3VC"),
                   GT("3VR", "3VC")),
               THEN(sub(add("3VL", "3VR"), "3VC")), # like Viola and Jones 2001
               ELSE(div(add("3VL", "3VC", "3VR"), 3)))) # average block value
  # Purely like Viola and Jones 2001: work poorly for EM membranes
  #op5 = sub(block3VC, block3VL, block3VR) # center minus sides
  #op6 = sub(add(block3VL, block3VR), block3VC) # sides minus center

  # Two bright-black-bright horizontal features 8x4 / 8x4 / 8x4
  block3HT = block(imgE, shift(cornersH, -bl/2, -bs -bs/2))
  block3HC = block(imgE, shift(cornersH, -bl/2,     -bs/2))
  block3HB = block(imgE, shift(cornersH, -bl/2,      bs/2))
  op7 = let("3HT", block3HT,
            "3HC", block3HC,
            "3HB", block3HB,
            IF(AND(GT("3HT", "3HC"),
                   GT("3HB", "3HC")),
               THEN(sub(add("3HT", "3HB"), "3HC")),
               ELSE(div(add("3HT", "3HC", "3HB"), 3)))) # average block value TODO make a single block 
  #op7 = sub(block3HC, block3HT, block3HB) # center minus top and bottom
  #op8 = sub(add(block3HT, block3HB), block3HC) # top and bottom minus center

  # Two adjacent horizontal rectanges, 12x12 - 4x4
  bll = bl + bl/2
  cornersLarge = [[0,      0], [bll -1,      0],
                  [0, bll -1], [bll -1, bll -1]]
  cornersSmall = [[0,     0], [bs -1,     0],
                  [0, bs -1], [bs -1, bs -1]]

  # Subtract a large black rectangle from a small bright one - aiming at capturing synapses
  # Bright on the right
  blockLargeL = block(imgE, shift(cornersLarge, -bll, -bll/2))
  blockSmallR = block(imgE, shift(cornersSmall,    0,  -bs/2))
  op9 = sub(blockSmallR, blockLargeL)
  # Bright on the left
  blockLargeR = block(imgE, shift(cornersLarge,   0, -bll/2))
  blockSmallL = block(imgE, shift(cornersSmall, -bs,  -bs/2))
  op10 = sub(blockSmallL, blockLargeR)
  # Bright at the bottom
  blockLargeT = block(imgE, shift(cornersLarge, -bll/2, -bll))
  blockSmallB = block(imgE, shift(cornersSmall,  -bs/2,    0))
  op11 = sub(blockSmallB, blockLargeT)
  # Bright at the top
  blockLargeB = block(imgE, shift(cornersLarge, -bll/2,   0))
  blockSmallT = block(imgE, shift(cornersSmall,  -bs/2, -bs))
  op12 = sub(blockSmallT, blockLargeB)

  return [op1, op2, op3, op4, op5, op7, op9, op10, op11, op12]


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



def filterBankEdges(img):
  """ Return all 4 edge detectors (left, right, top, bottom)
      as 3x3 convolution kernels. """
  imgE = Views.extendBorder(img)
  opTop = as2DKernel(imgE, [-1]*3 + [0]*3 + [1]*3)
  opBottom = as2DKernel(imgE, [1]*3 + [0]*3 + [-1]*3)
  opLeft = as2DKernel(imgE, [-1, 0, 1] * 3)
  opRight = as2DKernel(imgE, [1, 0, -1] * 3)
  return [opTop, opBottom, opLeft, opRight]


def filterBankPatch(img, width=5):
  """ Returns the raw pixel value of a square block of pixels (a patch) centered each pixel.
  """
  half = width / 2 # e.g. for 5, it's 2
  imgE = Views.extendBorder(img)
  ops = [offset(imgE, [x, y]) for x in xrange(-half, half + 1) for y in xrange(-half, half + 1)]
  return ops



def createTrainingData(img, samples, class_names, n_samples=0, ops=None):
  """ img: a 2D RandomAccessibleInterval.
      samples: a sequence of long[] (or int numeric sequence or Localizable) and class_index pairs; can be a generator.
      n_samples: optional, the number of samples (in case samples is e.g. a generator).
      class_names: a list of class names, as many as different class_index.
      ops: optional, the sequence of ImgMath ops to apply to the img, defaults to filterBank(img)

      return an instance of WEKA Instances
  """
  ops = ops if ops else filterBank(img)

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


def trainClassifier(classifier, img, samples, class_names, n_samples=0, ops=None, filepath=None):
  classifier.buildClassifier(createTrainingData(img, samples, class_names, n_samples=n_samples, ops=ops))

  # Save the trained classifier for later
  if filepath:
    SerializationHelper.write(filepath, classifier)

  return classifier


def createSMOClassifier(img, samples, class_names, n_samples=0, ops=None, filepath=None):
  """ Create a classifier: support vector machine (SVM, an SMO in WEKA)
      
      img: a 2D RandomAccessibleInterval.
      samples: a sequence of long[] (or int numeric sequence or Localizable) and class_index pairs; can be a generator.
      n_samples: optional, the number of samples (in case samples is e.g. a generator).
      class_names: a list of class names, as many as different class_index.
      filterBank: optional, the sequence of ImgMath ops to apply to the img.
      save_to_file: optional, a filename for saving the learnt classifier.
  """
  return trainClassifier(SMO(), img, samples, class_names, n_samples=n_samples, ops=ops, filepath=filepath)


def createRandomForestClassifier(img, samples, class_names, n_samples=0, ops=None, filepath=None, params={}):
  rf = FastRandomForest()
  rf.setNumTrees(params.get("n_trees", 200))
  rf.setNumFeatures(params.get("n_features", 2))
  #rf.seed(params.get("seed", 67778))
  rf.setNumThreads(params.get("n_threads", numCPUs()))
  return trainClassifier(rf, img, samples, class_names, n_samples=n_samples, ops=ops, filepath=filepath)


def createPerceptronClassifier(img, samples, class_names, n_samples, ops=None, filepath=None, params={}):
  mp = MultilayerPerceptron()
  if "learning_rate" in params:
    # In (0, 1]
    mp.setLearningRate(params.get("learning_rate", mp.getLearningRate()))
  # Number of nodes per layer: a set of comma-separated values (numbers), or:
  # 'a' = (number of attributes + number of classes) / 2
  # 'i' = number of attributes,
  # 'o' = number of classes
  # 't' = number of attributes + number of classes.
  # See MultilayerPerceptron.setHiddenLayers
  # https://weka.sourceforge.io/doc.dev/weka/classifiers/functions/MultilayerPerceptron.html#setHiddenLayers-java.lang.String-
  mp.setHiddenLayers(params.get("hidden_layers", "10,5"))
  return trainClassifier(mp, img, samples, class_names, n_samples, ops=ops, filepath=filepath)
  


def classify(img, classifier, class_names, ops=None, distribution_class_index=-1):
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
  if type(classifier) == str or type(classifier) == unicode:
    classifier = SerializationHelper.read(classifier)

  ops = ops if ops else filterBank(img)
  
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
    vector += array([0], 'd')
    di = DenseInstance(1.0, vector)
    di.setDataset(info) # the list of attributes
    if distribution_class_index > -1:
      cr.next().setReal(classifier.distributionForInstance(di)[distribution_class_index])
    else:
      cr.next().setReal(classifier.classifyInstance(di))

  return result


def loadClassifier(path):
  """ Parse and return a Weka Classifier. """
  return SerializationHelper.read(path)

def createWekaSegmentation(model_path):
  ws = WekaSegmentation()
  ws.setClassifier(loadClassifier(model_path))
  return ws

def classifyImageTWS(imp, n_threads=1, labels=True, ws=None, classifier=None, model_path=None):
  """ Apply the classifier and return the results ImagePlus with labels as an 8-bit image.
      Use labels=False for the probability map in floating-point.
  """
  if not ws:
    ws = WekaSegmentation()
    if not classifier:
      classifier = loadClassifier(model_path)
    ws.setClassifier(classifier)
  return ws.applyClassifier(imp, n_threads, labels) # False for labels, True for probability maps



