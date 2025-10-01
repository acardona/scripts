
from ini.trakem2.display import Display

for patch in Display.getFront().getLayer().getPatches(True):
  print patch
  print patch.getAffineTransform()