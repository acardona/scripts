import sys
from ij import IJ

# Find out dimensions and overall appearance

path = "/data/raw/SAM_3M/Y2024/M12/D04/Merlin-FIBdeSEMAna_24-12-04_193122_0-0-0.dat"
path = "/net/fibserver1/raw/SAM_3M/Y2024/M12/D10/Merlin-FIBdeSEMAna_24-12-10_223537_0-0-0.dat"

imp = IJ.openImage(path)
imp.show()
