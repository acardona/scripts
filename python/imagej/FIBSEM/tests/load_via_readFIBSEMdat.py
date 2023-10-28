import sys, os
sys.path.append("/lmb/home/acardona/lab/scripts/python/imagej/IsoView-GCaMP/")

from lib.io import readFIBSEMHeader, readFIBSEMdat

#filepath = "/home/albert/zstore1/FIBSEM/Pedro_parker/M06/D15/Merlin-FIBdeSEMAna_23-06-15_000153_0-0-0.dat"
#filepath = "/home/albert/zstore1/FIBSEM/Pedro_parker/M06/D17/Merlin-FIBdeSEMAna_23-06-17_235001_0-0-0.dat"
#filepath = "/home/albert/zstore1/FIBSEM/Pedro_parker/M06/D17/Merlin-FIBdeSEMAna_23-06-17_235001_0-0-1.dat"
#rilepath = "/home/albert/zstore1/FIBSEM/Pedro_parker/M06/D17/Merlin-FIBdeSEMAna_23-06-17_235001_0-1-0.dat"
#filepath = "/home/albert/zstore1/FIBSEM/Pedro_parker/M06/D17/Merlin-FIBdeSEMAna_23-06-17_235001_0-1-1.dat"

#/net/zstore1/FIBSEM/Pedro_parker/M07/D10/Merlin-FIBdeSEMAna_23-07-10_170205_0-0-0.dat
#/net/zstore1/FIBSEM/Pedro_parker/M07/D10/Merlin-FIBdeSEMAna_23-07-10_170205_0-0-1.dat
#/net/zstore1/FIBSEM/Pedro_parker/M07/D10/Merlin-FIBdeSEMAna_23-07-10_170205_0-1-0.dat
#/net/zstore1/FIBSEM/Pedro_parker/M07/D10/Merlin-FIBdeSEMAna_23-07-10_170205_0-1-1.dat

filepaths = [
  "/net/zstore1/FIBSEM/Pedro_parker/M07/D10/Merlin-FIBdeSEMAna_23-07-10_170614_0-0-0.dat",
  "/net/zstore1/FIBSEM/Pedro_parker/M07/D10/Merlin-FIBdeSEMAna_23-07-10_170614_0-0-1.dat",
  "/net/zstore1/FIBSEM/Pedro_parker/M07/D10/Merlin-FIBdeSEMAna_23-07-10_170614_0-1-0.dat",
  "/net/zstore1/FIBSEM/Pedro_parker/M07/D10/Merlin-FIBdeSEMAna_23-07-10_170614_0-1-1.dat"
]

# Smaller files: but all good
filepaths = [
  "/net/zstore1/FIBSEM/Pedro_parker/M07/D14/Merlin-FIBdeSEMAna_23-07-14_102820_0-0-0.dat",
  "/net/zstore1/FIBSEM/Pedro_parker/M07/D14/Merlin-FIBdeSEMAna_23-07-14_102820_0-0-1.dat",
  "/net/zstore1/FIBSEM/Pedro_parker/M07/D14/Merlin-FIBdeSEMAna_23-07-14_102820_0-1-0.dat",
  "/net/zstore1/FIBSEM/Pedro_parker/M07/D14/Merlin-FIBdeSEMAna_23-07-14_102820_0-1-1.dat"
]

filepaths = [
  "/net/zstore1/FIBSEM/Pedro_parker/M07/D14/Merlin-FIBdeSEMAna_23-07-14_110750_0-0-0.dat"
]

for filepath in filepaths:
  imp = readFIBSEMdat(filepath, channel_index=0, asImagePlus=True)[0]
  imp.setTitle(os.path.basename(filepath))
  imp.show()