import os
from ij import IJ, ImagePlus
from ij.process import ImageConverter
import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.util import Task, newFixedThreadPool
from lib.io import writeZip

sourceFolder = "/home/albert/shares/cardonalab/Albert/2017-05-10_1018/deconvolved/"
targetFolder = os.path.join(sourceFolder, "16-bit")

def accept(filepath):
  """ ADJUST to fit purpose. """
  return filepath.endswith(".zip") and os.path.getsize(filepath) > pow(2, 26) # about 67 MB

# Ensure target directory exists
if not os.path.exists(targetFolder):
  os.mkdir(targetFolder)

def convert(filepath, targetFolder):
  imp = IJ.openImage(filepath)
  if imp.getType() == ImagePlus.GRAY32:
    ic = ImageConverter(imp)
    ic.setDoScaling(False)
    ic.convertToGray16()
    filename = os.path.basename(filepath)
    writeZip(imp, os.path.join(targetFolder, filename), title=filename)
  else:
    syncPrint("Not a 32-bit image: " + filename)

exe = newFixedThreadPool()
try:
  futures = []
  for filename in sorted(os.listdir(sourceFolder)):
    filepath = os.path.join(sourceFolder, filename)
    if accept(filepath):
      futures.append(exe.submit(Task(convert, filepath, targetFolder)))
  for f in futures:
    f.get() # wait
finally:
  exe.shutdownNow()
