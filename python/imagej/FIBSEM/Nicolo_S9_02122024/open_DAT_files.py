import sys, os
from ij import IJ

# Find out dimensions and overall appearance

srcDir = "/net/fibserver1/raw/Nicolo_S9_02122024/Y2025/M01/D17/"
tiles = ["0-0", "0-1", "1-0", "1-1"]
basename = "Merlin-WEMS_25-01-17_142931_0-"

for tile in tiles:
  path = srcDir + basename + tile + ".dat"
  if os.path.exists(path):
    try:
      imp = IJ.openImage(path)
      #imp.show() # imp is null, doesn't return pointer but opens the image
    except:
      print "Failed to open\n" + path
      print sys.exc_info()
  else:
    print "Path not found:\n" + path
