# Test LabKit API

import os
from sc.fiji.labkit.ui.segmentation import SegmentationTool
from net.imagej import ImgPlus
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from sc.fiji.labkit.pixel_classification.utils import SingletonContext
from sc.fiji.labkit.ui.segmentation.weka import TrainableSegmentationSegmenter
from ij import IJ, Prefs
from net.imglib2.img.array import ArrayImgs
from net.imglib2.util import Intervals
from sc.fiji.labkit.pixel_classification.classification import Segmenter
from sc.fiji.labkit.pixel_classification.gson import GsonUtils
from sc.fiji.labkit.pixel_classification.classification import ClassifierSerialization


folder = "/home/albert/lab/projects/20240625_segment_FIBSEM_neural_tissue_vs_background/"
model_path = folder + "labkit/MR1.4-3_section1+6000_0.025.labkit.classifier"
test_imp = IJ.openImage(os.path.join(folder, "MR1.4-3_section_9000_0.025.tif"))
imgP = ImgPlus(IL.wrap(test_imp), test_imp.getTitle())

"""
# First approach
# Control the number of threads indirectly:
Prefs.setThreads(1)
st = SegmentationTool()
st.openModel(model_path)
st.setUseGpu(False)
labels = st.segment(imgP) # as an ImgPlus<UnsignedByteType>

IL.wrap(labels, "labels 2").show()


# Second approach: directly
segmenter = TrainableSegmentationSegmenter(SingletonContext.getInstance())
segmenter.openModel(model_path)
segmenter.setUseGpu(False)
field = TrainableSegmentationSegmenter.getDeclaredField("segmenter")
field.setAccessible(True)
seg2 = field.get(segmenter)
seg2.getClassifier().setNumThreads(1) # it's a FastRandomForest instance
labels = ArrayImgs.unsignedBytes(Intervals.dimensionsAsLongArray(imgP))
segmenter.segment(imgP, labels)

IL.wrap(labels, "labels 2").show()
"""

# Both work equally well, and internally the first calls the second.
# It's confusing that there are two different Segmenter interfaces.


# Third approach: without having to reload the model every time from scratch
json = GsonUtils.read(model_path)
# Has to decode it every time, but at least isn't loading it from the file system
seg = Segmenter.fromJson(SingletonContext.getInstance(), json)
seg.getClassifier().setNumThreads(1)
# Instead,could build it here:
# fastrandomforest = ClassifierSerialization.jsonToWeka(json)
labels = seg.segment(IL.wrap(test_imp))
IL.wrap(labels, "labels 3").show()


