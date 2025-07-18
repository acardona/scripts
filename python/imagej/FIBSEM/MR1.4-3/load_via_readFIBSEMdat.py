import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")

from lib.io import readFIBSEMHeader, readFIBSEMdat
from lib.util import timeit

filepaths = [
  # single tile:
  #"/net/fibserver1/raw/MR1.4-3/M02/D28/Merlin-WEMS_24-02-28_074147_0-0-0.dat",
  #"/net/fibserver1/raw/MR1.4-3/M02/D28/Merlin-WEMS_24-02-28_074147_0-1-0.dat",
  #"/net/fibserver1/raw/MR1.4-3/M03/D05/Merlin-WEMS_24-03-05_062018_0-0-0.dat", # fails to load
  "/net/zstore1/FIBSEM/MR1.4-3/repaired/Merlin-WEMS_24-03-05_062018_0-0-0.dat",
 ]

#TODO check if these above are the ones at the new large shift


# Difference is minimal: 20 ms over 500 to 1200 ms, when using buffer_size=0 vs buffer_size=pow(2, 27)
#timeit(3, readFIBSEMdat, filepaths[0], channel_index=0, asImagePlus=True, openAsRaw=False, buffer_size=0)

for filepath in filepaths:
  imp = readFIBSEMdat(filepath, channel_index=0, asImagePlus=True, toUnsigned=True)[0]
  imp.setTitle(os.path.basename(filepath))
  imp.show()
  
  print readFIBSEMHeader(filepath)
