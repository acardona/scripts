# Find out the 2D area of the largest section
# and whether it is larger than 2 GB (for array indexing with signed int)
#
# While it doesn't require mipmaps, it will be much faster if mipmaps are available

from ini.trakem2 import Project
from ini.trakem2.display import Patch
from ij import ImagePlus
from ij.io import FileSaver
from java.awt import Color
from java.awt.image import BufferedImage
from java.lang import Runnable, System
from java.util.concurrent import Executors
import os
import sys

target_dir = "/home/albert/shares/cardona_nearline/Albert/0111-8_whole_L1_CNS/section-series-flat-images/"

class Exporter(Runnable):
  def __init__(self, layer, i, target_dir):
    self.target_dir = target_dir
    self.layer = layer
    self.i = i
  def run(self):
    try:
      bounds = self.layer.getMinimalBoundingBox(Patch, True)
      filepath = os.path.join(self.target_dir, "section-" + str(self.i).zfill(5) + "-[x=" + str(bounds.x) + "-y=" + str(bounds.y) + "-width=" + str(bounds.width) + "-height=" + str(bounds.height) + "].zip")
      if os.path.exists(filepath):
        System.out.println("Skipping: " + filepath)
        return
      # Export
      System.out.println("Preparing: " + os.path.split(filepath)[1])
      img = self.layer.getProject().getLoader().getFlatAWTImage(self.layer, bounds, 1.0, -1, ImagePlus.GRAY8, Patch, None, False, Color.black)
      bi = BufferedImage(img.getWidth(None), img.getHeight(None), BufferedImage.TYPE_BYTE_GRAY)
      g = bi.createGraphics()
      g.drawImage(img, 0, 0, None)
      g.dispose()
      g = None
      imp = ImagePlus(str(self.layer.getZ()), ByteProcessor(bi))
      FileSaver(imp).saveAsZip(filepath)
      bi.flush()
      bi = None
      imp.flush()
      imp = None
      ip = None
      System.out.println("Saved: " + os.path.split(filepath)[1])
    except:
      import sys
      e = sys.exc_info()
      System.out.println("Error:" + str(e[0]) +"\n" + str(e[1]) + "\n" + str(e[2]))


exporters2 = Executors.newFixedThreadPool(4)
p = Project.getProjects()[0]

for k, lay in enumerate(p.getRootLayerSet().getLayers()):
  if 0 == k:
    continue
  exporters2.submit(Exporter(lay, k, target_dir))
