# Duplicate a stack in parallel
import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.ui import duplicateInParallel
from ij import IJ


imp = IJ.getImage()


# MR1.4-3

#copy = duplicateInParallel(imp, range(2868 -5 -964, 2869 +5 -964), n_threads=50, shallow=True, show=True)
#copy = duplicateInParallel(imp, range(100, 200), n_threads=100, shallow=True, show=True)


ranges = [
  #(7100, 7112), # top tile has the wrong magnification TODO
  #(16768, 17170), # displacement, may need manual shift
  #(17000, 17020), # displacement, needs manual shift at 17014 (1-based)
  #(21548, 21724), # displacement, may need manual shift: only somas, stems from multiple montage failures. IGNORE
  #(1810, 1825), # displacement, may need manual shift
  # All good (1530, 1623), # displacement between 1030 and 1623, may need manual shift
  #(1030, 1200)
  #(1053, 1061)
  #(17010, 18000),
  #(17999, 19000),
  #(18999, 20000),
  #(19999, 21000),
  #(20999, 22000),
  #(16395, 16403),
  #(1895, 1910),
  #(1800, 1900), # fine?
  #(2250, 2347), # fine?
  (2340, 2360), 
  (1900, 1930),
]

for r in ranges:
  copy = duplicateInParallel(imp, range(*r), n_threads=100, shallow=True, show=True)