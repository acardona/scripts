import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")

from lib.io import readFIBSEMHeader, readFIBSEMdat
from lib.util import timeit

filepaths = [
  #"/net/fibserver1/raw/NC_Hypathia/Y2023/M11/D02/Merlin-FIBdeSEMAna_23-11-02_215645_0-0-0.dat" 
  #"/net/fibserver1/raw/NC_Hypathia/Y2023/M11/D02/Merlin-FIBdeSEMAna_23-11-02_093618_0-0-0.dat", # first image tiles with more than one tile per section
  #"/net/fibserver1/raw/NC_Hypathia/Y2023/M11/D02/Merlin-FIBdeSEMAna_23-11-02_093618_0-0-1.dat",
  #"/net/fibserver1/raw/NC_Hypathia/Y2023/M11/D02/Merlin-FIBdeSEMAna_23-11-02_193326_0-0-0.dat",
  #"/net/fibserver1/raw/NC_Hypathia/Y2023/M11/D02/Merlin-FIBdeSEMAna_23-11-02_193326_0-0-1.dat",
  #"/net/fibserver1/raw/NC_Hypathia/Y2023/M11/D02/Merlin-FIBdeSEMAna_23-11-02_193326_0-1-0.dat",
  #"/net/fibserver1/raw/NC_Hypathia/Y2023/M11/D02/Merlin-FIBdeSEMAna_23-11-02_193326_0-1-1.dat",
  "/net/fibserver1/raw/NC_Hypathia/Y2023/M11/D11/Merlin-FIBdeSEMAna_23-11-11_094625_0-0-0.dat"
  #"/net/fibserver1/raw/NC_Hypathia/Y2023/M11/D11/Merlin-FIBdeSEMAna_23-11-11_095104_0-0-0.dat"
]


# Difference is minimal: 20 ms over 500 to 1200 ms, when using buffer_size=0 vs buffer_size=pow(2, 27)
#timeit(3, readFIBSEMdat, filepaths[0], channel_index=0, asImagePlus=True, openAsRaw=False, buffer_size=0)

for filepath in filepaths:
  imp = readFIBSEMdat(filepath, channel_index=0, asImagePlus=True, toUnsigned=True)[0]
  imp.setTitle(os.path.basename(filepath))
  imp.show()
  
  print readFIBSEMHeader(filepath)