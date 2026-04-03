# Duplicate a stack in parallel
import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.ui import duplicateInParallel
from ij import IJ


imp = IJ.getImage()
roi = imp.getRoi()

ranges = [
  #(0, 1850),
  (16300, 17368)
]

for r in ranges:
  copy = duplicateInParallel(imp, range(*r), n_threads=256, shallow=True, show=True, roi=roi)
