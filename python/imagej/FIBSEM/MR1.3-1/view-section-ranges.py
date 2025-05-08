# Duplicate a stack in parallel
import sys, os
sys.path.append("/lmb/home/phague/fibsem/scripts/python/imagej/IsoView-GCaMP/")
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
  #(3246, 3247), # corrupt tile
  (1,17367)
  #(1,2000)
  #(1870,1900)
  #(200,250),
  #(6600,6700),
  #(8500,8600),
  #(3600,3620),
]

scale = 400.0 / 16000
#scale = 1 #0.25
#scale = 0.1
targetDir = "/net/zstore1/FIBSEM/MR1.3-1/montages-400/"

for r in ranges:
  #copy = duplicateInParallel(imp, range(*r), n_threads=32, shallow=True, show=True, scale=scale)
  copy = saveInParallel(targetDir, imp, range(*r), n_threads=32, show=True, scale=scale, incremental=True)
