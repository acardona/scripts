import os, sys
libDir = "/net/fibserver1/code/scripts/python/imagej/IsoView-GCaMP/"
sys.path.append(libDir)
from lib.montage2d_table import TrakEM2Montage
from ini.trakem2.display import Display

# NOTE: for newly created TrakEM2 projects there's no need for the montageDir at all, can be None
# as an argument to TrakEM2Montage. The montageDir is written in the Patch properties.

# VOLUME
name = "YY9_Gaba" # Nicolo_S9_02122024" # Name of the folder containing the .dat files, e.g., "MR1.4-3"
targetServer = "/net/fibserver1/raw/"
tgtDir = targetServer + name + "/registration/"
montageDir = tgtDir + "montage-csv/" # for in-section montaging

front = Display.getFront()
if front:
  TrakEM2Montage(montageDir, None).addTrakEM2Tab(front.getProject())
