# Duplicate a stack in parallel
import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.ui import duplicateInParallel, saveInParallel
from ij import IJ


imp = IJ.getImage()
roi = imp.getRoi()

ranges = [
  #(0, 26754),
  #(0, 400),
  (400, 1200),
]

scale = 1.0
#targetDir = 

for r in ranges:
  copy = duplicateInParallel(imp, range(*r), n_threads=256, shallow=True, show=True, scale=scale, roi=roi)
  #copy = saveInParallel(targetDir, imp, range(*r), n_threads=32, show=True, scale=scale, incremental=True)

imp = None
copy = None