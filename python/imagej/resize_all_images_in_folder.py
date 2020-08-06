import os
from ij import IJ, ImagePlus

srcDir = "/home/albert/jo/casa/Cambridge/Fulbrooke Road/Fulbrooke Road/HR/"
tgtDir = "/home/albert/jo/casa/Cambridge/Fulbrooke Road/Fulbrooke Road/HR-0.5/"

if not os.path.exists(tgtDir):
  os.makedirs(tgtDir)

for filename in os.listdir(srcDir):
  if filename.endswith(".jpg"):
    imp = IJ.openImage(os.path.join(srcDir, filename))
    ip = imp.getProcessor().resize(imp.getWidth() / 2)
    IJ.save(ImagePlus(imp.getTitle(), ip), os.path.join(tgtDir, filename))
