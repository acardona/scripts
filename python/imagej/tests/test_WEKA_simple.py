# Basic example of machine learning with the WEKA library

from jarray import array
from java.util import ArrayList, Random
from weka.core import Attribute, Instances, DenseInstance,
from weka.classifiers.functions import SMO

# List of attributes: each is a value in a vector for each sample
n_attributes = 3
attributes = ArrayList([Attribute("attr-%i" % (i+1)) for i in xrange(n_attributes)])
# Plus the class, here only two classes with indices 0 and 1
attributes.add(Attribute("class", ["first", "second"]))

# Training data: each sample is a vector of 4 values (3 attributes and the class index).
# Here, two different distributions (two classes) are generated, whose attributes
# take values within [0, 1) (for class index 0) and within [1, 2) (for class index 1)
random = Random()
samples = [random.doubles(n_attributes, k, k+1).toArray() + array([k], 'd') # 3 values and the class index
           for i in xrange(50) # 50 samples per class
           for k in (0, 1)] # two class indices

# The datastructure containing the training data
training_data = Instances("training", attributes, len(samples))
training_data.setClassIndex(len(attributes) -1) # the last one is the class
# Populate the training data, with all samples having the same weight 1.0
for vector in samples:
  training_data.add(DenseInstance(1.0, vector))

# The classifier: an SMO (support vector machine)
classifier = SMO()
classifier.buildClassifier(training_data)

# Test data
test_samples = [[0.5, 0.2, 0.9],   # class index 0
                [0.7, 0.99, 0.98], # class index 0
                [1.0, 1.2, 1.3],   # class index 1
                [1.6, 1.3, 1.1]]   # class index 1
# Umbrella data structure with the list of attributes
info = Instances("test", attributes, 1) # size of 1
info.setClassIndex(len(attributes) -1)

# Classify every test data sample
for vector in test_samples:
  instance = DenseInstance(1.0, vector) # vector list as double[] automatically
  instance.setDataset(info)
  class_index = classifier.classifyInstance(instance)
  print "Classified", sample, "as class", class_index