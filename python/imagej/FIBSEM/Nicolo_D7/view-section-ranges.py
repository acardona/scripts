# Duplicate a stack in parallel
import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.ui import duplicateInParallel, saveInParallel
from ij import IJ


imp = IJ.getImage()

ranges = [
  #(1, 19532),
  #(1, 400),
  #(17200, 17600),
  #(17000, 17400),
  #(17600, 17927),
  #(200, 599),
  #(17400, 17799),
  #(16400, 16799),
  #(14200, 14599),
  #(16600, 16999),
  #(14400, 14799),
  #(10800, 11199),
  #(10600, 11000),
  (16800, 17200),
]

scale = 1.0
#targetDir = 

for r in ranges:
  copy = duplicateInParallel(imp, range(*r), n_threads=32, shallow=True, show=True, scale=scale)
  #copy = saveInParallel(targetDir, imp, range(*r), n_threads=32, show=True, scale=scale, incremental=True)

imp = None
copy = None