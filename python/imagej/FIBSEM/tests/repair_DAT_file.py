# Repair FIBSEM DAT files based on a good file
# Rescues as much data as there may be from the first channel
# into a new file.

import os, sys
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")
from jarray import zeros
from java.io import RandomAccessFile, File
from java.lang import System
from lib.io import repairTruncatedDAT, readFIBSEMdat, blankROIDAT

sourcePath = "/net/fibserver1/raw/MR1.4-3/"
repairedPath = "/net/zstore1/FIBSEM/MR1.4-3/repaired/"

# List of images to repair with a reference image to use for correcting header and dimensions
pairs = [
  {"good": "M02/D27/Merlin-WEMS_24-02-27_165658_0-0-0.dat",
   "bad" : "M02/D27/Merlin-WEMS_24-02-27_165658_0-1-0.dat"}, # truncated
  {"good": "M02/D27/Merlin-WEMS_24-02-27_201135_0-0-0.dat",
   "bad" : "M02/D27/Merlin-WEMS_24-02-27_201135_0-1-0.dat"}, # truncated
  {"good": "M03/D05/Merlin-WEMS_24-03-05_062018_0-1-0.dat",
   "bad" : "M03/D05/Merlin-WEMS_24-03-05_062018_0-0-0.dat"}, # truncated: but when montaging should end up at the bottom
  {"good": "M03/D10/Merlin-WEMS_24-03-10_054103_0-0-0.dat",
   "bad" : "M03/D10/Merlin-WEMS_24-03-10_054103_0-1-0.dat"}, # truncated
  {"good": "M03/D13/Merlin-WEMS_24-03-13_235528_0-0-0.dat",
   "bad" : "M03/D13/Merlin-WEMS_24-03-13_235528_0-1-0.dat"}, # truncated
  {"good": "M03/D15/Merlin-WEMS_24-03-15_130137_0-0-0.dat",
   "bad" : "M03/D15/Merlin-WEMS_24-03-15_130137_0-1-0.dat"}, # truncated
  {"good": "M02/D23/Merlin-WEMS_24-02-23_213431_0-0-0.dat",
   "bad" : "M02/D23/Merlin-WEMS_24-02-23_213519_0-0-0.dat"}, # truncated
  {"good": "M02/D24/Merlin-WEMS_24-02-24_015441_0-0-0.dat",
   "bad" : "M02/D24/Merlin-WEMS_24-02-24_015620_0-0-0.dat"}, # truncated
]

# List of images with ROIs to blank out
to_blank = [
  #{"path": "M02/D23/Merlin-WEMS_24-02-23_213519_0-0-0.dat",  # turns out it's truncated by opens funny, with a duplication
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
