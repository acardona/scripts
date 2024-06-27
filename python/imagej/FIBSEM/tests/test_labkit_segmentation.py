# Test LabKit API

from sc.fiji.labkit.ui.segmentation import SegmentationTool
from net.imagej import ImgPlus
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.type.numeric.integer import UnsignedByteType
from sc.fiji.labkit.pixel_classification.utils import SingletonContext
from ij import IJ, Prefs

folder = "/home/albert/lab/projects/20240625_segment_FIBSEM_neural_tissue_vs_background/"
model_path = folder + "labkit/MR1.4-3_section1+6000_0.025.labkit.classifier"
test_imp = IJ.openImage(os.path.join(folder, "MR1.4-3_section_9000_0.025.tif"))
imgP = ImgPlus(IL.wrap(test_imp), test_imp.getTitle())


# Control the number of threads
print Prefs.getThreads()
Prefs.setThreads(1)

st = SegmentationTool()
st.openModel(model_path)
st.setUseGpu(False)
labels = st.segment(imgP, UnsignedByteType) # as an ImgPlus

# Second approach
#segmenter = TrainableSegmentationSegmenter(SingletonContext.getInstance())
#segmenter.openModel(model_path)
#segmenter.setUseGpu(False)
#labels = ArrayImgs.unsignedBytes(imgP)
#segmenter.segment(imgP, labels)


IL.wrap(labels, "labels").show()


