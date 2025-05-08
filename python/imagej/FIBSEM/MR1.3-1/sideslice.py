# Duplicate a stack in parallel
import sys, os
sys.path.append("/lmb/home/phague/fibsem/scripts/python/imagej/IsoView-GCaMP/")
from lib.ui import duplicateInParallel, saveInParallel
from ij import IJ


imp = IJ.getImage()
stack = imp.getStack()

wd = stack.width
ht = stack.height
dp = stack.size()
print(wd, ht,dp)#, array.shape)

imp.setSlice(8600)
