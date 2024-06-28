import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.segmentation_em import classifyImageLabKitSegCached, segThreadCache
from ij import IJ
from net.imglib2.img.display.imagej import ImageJFunctions as IL

folder = "/home/albert/lab/projects/20240625_segment_FIBSEM_neural_tissue_vs_background/"
model_path = folder + "labkit/MR1.4-3_section1+6000_0.025.labkit.classifier"
test_imp = IJ.openImage(os.path.join(folder, "MR1.4-3_section_9000_0.025.tif"))

n_threads = 1 # for the Segmenter
cache_size = 64 # as many as threads to concurrently run each one Segmenter

# One Segmenter per Thread
cache = segThreadCache(model_path, n_threads, cache_size=cache_size)
labels = classifyImageLabKitSegCached(IL.wrap(test_imp), cache)

IL.wrap(labels, "labels").show()
