# Duplicate a stack in parallel
import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.ui import duplicateInParallel, saveInParallel
from ij import IJ


imp = IJ.getImage()


# MR1.4-3

#copy = duplicateInParallel(imp, range(2868 -5 -964, 2869 +5 -964), n_threads=50, shallow=True, show=True)
#copy = duplicateInParallel(imp, range(100, 200), n_threads=100, shallow=True, show=True)


ranges = [
  #(1, 19532), # all, 1-based
  #(1127, 1129), # transition from 1 to 2 tiles
  #(1127, 1136), # bad montages
  #(1134, 1142), # bad montages
  #(1133, 1150), # bad montages
  #(3246, 3247), # corrupt tile
  #(1150, 1153), # non-linear deformation
  #(1784, 1787), # jump
  #(2737, 2741), # contrast problem
  #(3308, 3313), # deformation at 3310
  #(12175, 19531) # exporting via saveInParallel scaled down
  #(1126, 1129), # shift 1127: good
  #(1783, 1787), # shift 1784: good
  #(14508, 14512), # shift 14509 and 14510: good
  #(14514, 14519), # shift 14516: good
  #(15555, 15560), # shift 15556: good
  #(17282, 17286), # shift 17283: good
  (3308, 3314),
]

#scale = 400.0 / 16000
scale = 1.0

#targetDir = "/data/raw/MR1.4-2/montages-400/"
targetDir = "/net/fibserver1/raw/MR1.4-2/montages-400_for_12175-19531/"

for r in ranges:
  copy = duplicateInParallel(imp, range(*r), n_threads=32, shallow=True, show=True, scale=scale)
  #copy = saveInParallel(targetDir, imp, range(*r), n_threads=32, show=True, scale=scale, incremental=True)