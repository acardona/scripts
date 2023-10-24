from __future__ import with_statement
from sc.fiji.io import FIBSEM_Reader
from ij import IJ
from java.io import File, FileInputStream

paths = [
"/home/albert/zstore1/FIBSEM/Pedro_parker/M07/D14/Merlin-FIBdeSEMAna_23-07-14_000300_0-0-0.dat",
"/home/albert/zstore1/FIBSEM/Pedro_parker/M07/D14/Merlin-FIBdeSEMAna_23-07-14_000300_0-0-1.dat",
"/home/albert/zstore1/FIBSEM/Pedro_parker/M07/D14/Merlin-FIBdeSEMAna_23-07-14_000300_0-1-0.dat",
"/home/albert/zstore1/FIBSEM/Pedro_parker/M07/D14/Merlin-FIBdeSEMAna_23-07-14_000300_0-1-1.dat"]

for path in paths:
  r = FIBSEM_Reader()
  fis = None
  try:
    fis = FileInputStream(File(path))
    header = r.parseHeader(fis)
    print path
    print "stageX (mm):", header.stageX
    print "stageY (mm):", header.stageY
    print "stageZ (mm):", header.stageZ
    print "stageT (degree):", header.stageT
    print "stageR (degree):", header.stageR
    print "stageM (mm):", header.stageM
    print "fibShiftX (mm):", header.fibShiftX
    print "fibShiftY (mm):", header.fibShiftY
    print "semShiftX (mm):", header.semShiftX
    print "semShiftY (mm):", header.semShiftY
  finally:
    if fis is not None:
      fis.close()

