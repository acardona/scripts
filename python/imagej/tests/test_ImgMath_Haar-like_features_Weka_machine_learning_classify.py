from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from ij import IJ, WindowManager

import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.features_em import classify


imp = WindowManager.getImage("180-220-sub512x512-30.tif") # IJ.getImage() # e.g. 8-bit EM of Drosophila neurons 180-220-sub512x512-30.tif
#imp = IJ.openImage("/home/albert/lab/TEM/abd/microvolumes/Seg/180-220-sub/180-220-sub512x512-30.tif")
img = IL.wrap(imp)

# Classify pixels as membrane or not
result = classify(img, "/tmp/svm-mem-nonmem", class_names=None)

IL.wrap(result, "result").show()