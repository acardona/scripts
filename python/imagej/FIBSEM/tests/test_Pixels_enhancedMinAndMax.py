import sys, os
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import readFIBSEMHeader, readFIBSEMdat
from lib.pixels_asm import Pixels

paths = [
  "/home/albert/Desktop/t2/Pedro_Parker/failed SIFT montage 23-07-10_170164/Merlin-FIBdeSEMAna_23-07-10_170614_0-0-0.dat",
  #"/home/albert/Desktop/t2/Pedro_Parker/failed SIFT montage 23-07-10_170164/Merlin-FIBdeSEMAna_23-07-10_170614_0-0-1.dat",
  #"/home/albert/Desktop/t2/Pedro_Parker/failed SIFT montage 23-07-10_170164/Merlin-FIBdeSEMAna_23-07-10_170614_0-1-0.dat",
  #"/home/albert/Desktop/t2/Pedro_Parker/failed SIFT montage 23-07-10_170164/Merlin-FIBdeSEMAna_23-07-10_170614_0-1-1.dat"
]

for path in paths:
  imp = readFIBSEMdat(path, channel_index=0, asImagePlus=True)[0]
  imp.getProcessor().invert()
  # With 2 stdDev
  Pixels.enhancedMinAndMax(imp.getProcessor(), 2)
  
  imp.setTitle(os.path.basename(path))
  imp.show()