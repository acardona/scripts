# Create a TrakEM2 project that is a virtual view of another volume
# such as an 8-bit N5 volume loaded with an imglib2 LazyCellImg.
import os
from ini.trakem2 import Project
from ini.trakem2.display import Display, Layer, Patch
from ini.trakem2.persistence import ExportMultilevelTiles
from ini.trakem2.utils import Saver
from ij import ImagePlus
from java.awt import Color, Rectangle
from java.awt.geom import AffineTransform


# From the N5 attributes:
dimensions = [15312, 17424, 13770]
img_type = ImagePlus.GRAY8
name = "FIBSEM_L1116"  # The name of the ImagePlus showing the N5 volume

# CATMAID target folder for tiles
tgt_dir = "/groups/cardona/cardonalab/" + name + "_CATMAID_tiles/"
if not os.exists(tgt_dir):
  os.mkdir(tgt_dir)

# Grab an empty project created from the Fiji GUI:
project = Project.getProjects()[0]

# Project properties: large buckets, no mipmaps
project.setProperty("bucket_side", str(max(dimensions[0], dimensions[1])))
project.getLoader().setMipMapsRegeneration(False)

# Adjust first layer to Z of -1 (as proper layers will be added from 0 onwards
layerset = project.getRootLayerSet()
layerset.getLayers().get(0).setZ(-1.0)
# (This first layer serves as a layer to avoid repainting anything.)

# Create a preprocessor script in beanshell
script = """
// Variables 'patch' and 'imp' exist, with 'imp' being an uninitialized ImagePlus
import ij.ImagePlus;
import ij.WindowManager;

ids = WindowManager.getIDList();
for (int i=0; i<ids.length; ++i) {
  src = WindowManager.getImage(ids[i]); // an ImagePlus
  if (src.getStack().isVirtual() && src.getTitle() == %s) {
    layer = patch.getLayer();
    ip = src.getStack().getProcessor(layer.getParent().getLayerIndex(layer) + 1); // 1-based
    imp.setProcessor("", ip);
    break;
  }
}
""" % (name)

preprocessor_script_path = "/tmp/trakem2-n5.bsh"
with open(preprocessor_script_path, 'w') as f:
  f.write(script)

# Create as many layers as indices in the Z dimension
layers = []
for z in xrange(dimensions[2]):
  layer = Layer(project, z, 1.0, layerset)
  layerset.addSilently(layer)
  layers.append(layer)

layerset.recreateBuckets(layers, True)
Display.updateLayerScroller(layerset)

# Add a single Patch instance per Layer, whose image is a 2D crop of the N5 volume
for layer in layerset.getLayers():
  index = layerset.getLayerIndex(layer.getId())
  patch = Patch(project, "", dimensions[0], dimensions[1],
                dimensions[0], dimensions[1],
                img_type, 1.0,
                Color.black, True,
                0, 255,
                AffineTransform(), "")
  patch.setPreprocessorScriptPathSilently(preprocessor_script_path)


# Export for CATMAID from raw images (strategy=0)
saver = Saver("jpg")
saver.setQuality(0.75)
ExportMultilevelTiles.makePrescaledTiles(layers, Patch, Rectangle(0, 0, dimensions[0], dimensions[1]),
                                         -1, img_type, tgt_dir, 0, saver, True, True,
                                         Runtime.getRuntime().availableProcessors())
