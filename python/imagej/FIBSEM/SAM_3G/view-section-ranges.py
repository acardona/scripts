# Duplicate a stack in parallel
import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.ui import duplicateInParallel, saveInParallel
from ij import IJ

imp = IJ.getImage()


ranges = [
  (0, 8000)
]

targetDir = "/net/fibserver1/raw/SAM_3G/samia/scaled_0.05/"

scale = 0.05

for r in ranges:
  #copy = duplicateInParallel(imp, range(*r), n_threads=100, shallow=True, show=True)
  saveInParallel(targetDir, imp=None, slices=range(*r), n_threads=0, show=True, scale=scale, incremental=True)