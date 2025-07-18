from ij import IJ

filepath = "/net/fibserver1/raw/MR1.3-2/Y2024/M06/D29/Merlin-WEMS_24-06-29_031451_0-0-0.dat"

#imp = IJ.openImage(filepath)
#imp.show


libDir = "/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/"
import sys, os
sys.path.append(libDir)
from lib.io import readFIBSEMdat

imp1 = readFIBSEMdat(filepath, channel_index=0, asImagePlus=True, toUnsigned=True)[0]
imp1.setTitle(os.path.basename(filepath) + " channel 0")
imp1.show()


imp2 = readFIBSEMdat(filepath, channel_index=1, asImagePlus=True, toUnsigned=True)[0]
imp2.setTitle(os.path.basename(filepath) + " channel 1")
imp2.show()
