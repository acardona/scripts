# Duplicate a stack in parallel
import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.ui import duplicateInParallel, saveInParallel
from ij import IJ

imp = IJ.getImage()
roi = imp.getRoi()

ranges = [
  #(2050, 2200),
  #(2250, 2450),
  #(2200, 4000),
  #(3800, 6000),
  #(6000, 8000),
  (0, 18009),
]

#scale = 400.0 / 16000
scale = 1.0

for r in ranges:
  copy = duplicateInParallel(imp, range(*r), n_threads=200, shallow=True, show=True, scale=scale, roi=roi)
  #copy = saveInParallel(targetDir, imp, range(*r), n_threads=32, show=True, scale=scale, incremental=True)