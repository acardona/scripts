import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")

from lib.io import readFIBSEMHeader, readFIBSEMdat
from lib.util import timeit

filepaths = [
  # single tile:
  #"/net/fibserver1/raw/MR1.4-3/M02/D23/Merlin-WEMS_24-02-23_213431_0-0-0.dat",
  #"/net/fibserver1/raw/MR1.4-3/M02/D23/Merlin-WEMS_24-02-23_213519_0-0-0.dat", # strange shift at bottom
  # 1x2:
  #"/net/fibserver1/raw/MR1.4-3/M03/D12/Merlin-WEMS_24-03-12_235936_0-0-0.dat",
  #"/net/fibserver1/raw/MR1.4-3/M03/D12/Merlin-WEMS_24-03-12_235936_0-1-0.dat"
  #"/net/fibserver1/raw/MR1.4-3/M03/D01/Merlin-WEMS_24-03-01_141202_0-0-0.dat",
  #"/net/fibserver1/raw/MR1.4-3/M03/D01/Merlin-WEMS_24-03-01_141202_0-1-0.dat",
  #"/net/fibserver1/raw/MR1.4-3/M03/D05/Merlin-WEMS_24-03-05_124008_0-0-0.dat", # first of 4 montages that failed
  #"/net/fibserver1/raw/MR1.4-3/M03/D05/Merlin-WEMS_24-03-05_124008_0-1-0.dat",
  #"/net/fibserver1/raw/MR1.4-3/M03/D05/Merlin-WEMS_24-03-05_163336_0-0-0.dat", # second of 4 montages that failed
  #"/net/fibserver1/raw/MR1.4-3/M03/D05/Merlin-WEMS_24-03-05_163336_0-1-0.dat",
  #"/net/fibserver1/raw/MR1.4-3/M03/D05/Merlin-WEMS_24-03-05_125417_0-0-0.dat", # third of 4 montages that failed
  #"/net/fibserver1/raw/MR1.4-3/M03/D05/Merlin-WEMS_24-03-05_125417_0-1-0.dat",
  "/net/fibserver1/raw/MR1.4-3/M03/D05/Merlin-WEMS_24-03-05_134004_0-0-0.dat", # fourth of 4 montages that failed
  "/net/fibserver1/raw/MR1.4-3/M03/D05/Merlin-WEMS_24-03-05_134004_0-1-0.dat"
]


# Difference is minimal: 20 ms over 500 to 1200 ms, when using buffer_size=0 vs buffer_size=pow(2, 27)
#timeit(3, readFIBSEMdat, filepaths[0], channel_index=0, asImagePlus=True, openAsRaw=False, buffer_size=0)

for filepath in filepaths:
  imp = readFIBSEMdat(filepath, channel_index=0, asImagePlus=True, toUnsigned=True)[0]
  imp.setTitle(os.path.basename(filepath))
  imp.show()
  
  print readFIBSEMHeader(filepath)