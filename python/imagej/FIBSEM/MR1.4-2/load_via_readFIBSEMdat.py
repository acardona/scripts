import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")

from lib.io import readFIBSEMHeader, readFIBSEMdat
from lib.util import timeit

filepaths = [
  # single tile:
  #"/data/raw/MR1.4-2/Y2024/M06/D08/Merlin-FIBdeSEMAna_24-06-08_214955_0-1-0.dat", # empty file
  #"/data/raw/MR1.4-2/Y2024/M06/D08/Merlin-FIBdeSEMAna_24-06-08_215138_0-1-0.dat", # empty file
  #"/net/fibserver1/raw/MR1.4-2/Y2024/M06/D08/Merlin-FIBdeSEMAna_24-06-08_215945_0-0-0.dat", # blurred and bad montage
  #"/net/fibserver1/raw/MR1.4-2/Y2024/M06/D08/Merlin-FIBdeSEMAna_24-06-08_215945_0-1-0.dat", # idem
  #"/net/fibserver1/raw/MR1.4-2/Y2024/M06/D08/Merlin-FIBdeSEMAna_24-06-08_215319_0-0-0.dat", # blurred and bad montage
  #"/net/fibserver1/raw/MR1.4-2/Y2024/M06/D08/Merlin-FIBdeSEMAna_24-06-08_215319_0-1-0.dat", # idem
  #"/net/fibserver1/raw/MR1.4-2/Y2024/M06/D10/Merlin-FIBdeSEMAna_24-06-10_210018_0-0-0.dat",
  #"/net/fibserver1/raw/MR1.4-2/Y2024/M06/D10/Merlin-FIBdeSEMAna_24-06-10_210018_0-1-0.dat",
  #"/net/fibserver1/raw/MR1.4-2/Y2024/M06/D10/Merlin-FIBdeSEMAna_24-06-10_210136_0-0-0.dat",
  #"/net/fibserver1/raw/MR1.4-2/Y2024/M06/D10/Merlin-FIBdeSEMAna_24-06-10_210136_0-1-0.dat",
  "/net/fibserver1/raw/MR1.4-2/Y2024/M06/D10/Merlin-FIBdeSEMAna_24-06-10_205904_0-0-0.dat",
  "/net/fibserver1/raw/MR1.4-2/Y2024/M06/D10/Merlin-FIBdeSEMAna_24-06-10_205904_0-1-0.dat",
]


# Difference is minimal: 20 ms over 500 to 1200 ms, when using buffer_size=0 vs buffer_size=pow(2, 27)
#timeit(3, readFIBSEMdat, filepaths[0], channel_index=0, asImagePlus=True, openAsRaw=False, buffer_size=0)

for filepath in filepaths:
  imp = readFIBSEMdat(filepath, channel_index=0, asImagePlus=True, toUnsigned=True)[0]
  imp.setTitle(os.path.basename(filepath))
  imp.show()
  
  print readFIBSEMHeader(filepath)
