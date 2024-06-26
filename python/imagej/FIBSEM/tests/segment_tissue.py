from __future__ import with_statement
import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.segmentation_em import classify
from ij import IJ
from weka.core import SerializationHelper
from net.imglib2.img.display.imagej import ImageJFunctions as IL

from trainableSegmentation import WekaSegmentation
from weka.core import SerializationHelper


folder = "/home/albert/lab/projects/20240625_segment_FIBSEM_neural_tissue_vs_background/"
test_imp = IJ.openImage(os.path.join(folder, "MR1.4-3_section_9000_0.025.tif"))
print type(test_imp)

n_threads = 1

ws = WekaSegmentation()
model_path = folder + "classifier_1+6000.model"
print "Path exists:", os.path.exists(model_path)
print "Classifier loaded:", ws.loadClassifier(model_path)

classifier = SerializationHelper.read(model_path)
print classifier
ws.setClassifier(classifier)

print ws.getClassLabel(0)
print ws.getClassLabel(1)

print ws.getClassifier()


labels_imp = ws.applyClassifier(test_imp, n_threads, False) # False for labels, True for probability maps
labels_imp.show()

