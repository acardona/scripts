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
import os

target_dir = "/home/albert/shares/cardona_nearline/Albert/0111-8_whole_L1_CNS/section-series-flat-images/"

p = Project.getProjects()[0]

for i, layer in enumerate(p.getRootLayerSet().getLayers()):
  if 0 == i:
    continue
  bounds = layer.getMinimalBoundingBox(Patch, True)
  img = p.getLoader().getFlatAWTImage(layer, bounds, 1.0, -1, ImagePlus.GRAY8, Patch, None, False, Color.black)
  bi = BufferedImage(img.getWidth(None), img.getHeight(None), BufferedImage.TYPE_BYTE_GRAY)
  g = bi.createGraphics()
  g.drawImage(img, 0, 0, None)
  g.dispose()
  g = None
  imp = ImagePlus(str(layer.getZ()), ByteProcessor(bi))
  filepath = os.path.join(target_dir, "section-" + str(i).zfill(5) + "-[x=" + str(bounds.x) + "-y=" + str(bounds.y) + "-width=" + str(bounds.width) + "-height=" + str(bounds.height) + "].zip")
  FileSaver(imp).saveAsZip(filepath)
  bi.flush()
  bi = None
  imp.flush()
  imp = None
  ip = None
  print "Saved layer", i
