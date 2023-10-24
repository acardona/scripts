import sys, os
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")

from lib.io import readFIBSEMHeader, readFIBSEMdat

#filepath = "/home/albert/zstore1/FIBSEM/Pedro_parker/M06/D15/Merlin-FIBdeSEMAna_23-06-15_000153_0-0-0.dat"
filepath = "/home/albert/zstore1/FIBSEM/Pedro_parker/M06/D17/Merlin-FIBdeSEMAna_23-06-17_235001_0-0-0.dat"
#filepath = "/home/albert/zstore1/FIBSEM/Pedro_parker/M06/D17/Merlin-FIBdeSEMAna_23-06-17_235001_0-0-1.dat"
#rilepath = "/home/albert/zstore1/FIBSEM/Pedro_parker/M06/D17/Merlin-FIBdeSEMAna_23-06-17_235001_0-1-0.dat"
#filepath = "/home/albert/zstore1/FIBSEM/Pedro_parker/M06/D17/Merlin-FIBdeSEMAna_23-06-17_235001_0-1-1.dat"

imp = readFIBSEMdat(filepath, channel_index=0, asImagePlus=True)[0]

imp.show()