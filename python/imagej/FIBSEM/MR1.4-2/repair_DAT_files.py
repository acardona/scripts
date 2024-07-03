# Repair FIBSEM DAT files based on a good file
# Rescues as much data as there may be from the first channel
# into a new file.

import os, sys
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from jarray import zeros
from java.io import RandomAccessFile, File
from java.lang import System
from lib.io import repairTruncatedDAT, readFIBSEMdat, blankROIDAT

sourcePath = "/data/raw/MR1.4-2/Y2024/" # at fibserver1
repairedPath = "/net/zstore1/FIBSEM/MR1.4-2/repaired/"

# List of images to repair with a reference image to use for correcting header and dimensions
pairs = [
  {"good": "M06/D10/Merlin-FIBdeSEMAna_24-06-10_165631_0-0-0.dat",
   "bad" : "M06/D10/Merlin-FIBdeSEMAna_24-06-10_165631_0-1-0.dat"}, # truncated
   {"good": "M06/D09/Merlin-FIBdeSEMAna_24-06-09_232535_0-0-0.dat",
   "bad" : "M06/D09/Merlin-FIBdeSEMAna_24-06-09_232630_0-0-0.dat"}, # truncated
   {"good": "M06/D10/Merlin-FIBdeSEMAna_24-06-10_181940_0-0-0.dat",
    "bad": "M06/D10/Merlin-FIBdeSEMAna_24-06-10_181940_0-1-0.dat"}, # truncated
]

# List of images with ROIs to blank out
to_blank = [
  #{"path": "M02/D23/Merlin-WEMS_24-02-23_213519_0-0-0.dat",  # turns out it's truncated and opens funny, with a duplication
  # "rois": [[0, 9815, 12500, 2685]]}, # [x,y,width,height]
]


for p in pairs:
  good = p["good"]
  bad = p["bad"]
  repairTruncatedDAT(os.path.join(sourcePath, good),
                     os.path.join(sourcePath, bad),
                     os.path.join(repairedPath, bad[bad.rfind('/')+1:]))


for p in to_blank:
  blankROIDAT(os.path.join(sourcePath, p["path"]),
              os.path.join(repairedPath, p["path"][p["path"].rfind('/')+1:]),
              p["rois"])


# Open all repaired files
for relpath in [p["bad"] for p in pairs] + [p["path"] for p in to_blank]:
  path = os.path.join(repairedPath, relpath[relpath.rfind('/')+1:])
  imp = readFIBSEMdat(path, channel_index=0, asImagePlus=True)[0]
  imp.show()
