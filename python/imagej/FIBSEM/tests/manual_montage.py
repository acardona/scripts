from ini.trakem2.display import Patch, Layer
from ini.trakem2 import Project
import os, sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import readFIBSEMHeader, readFIBSEMdat
from java.awt import Color
from ij import ImagePlus
from java.awt.geom import AffineTransform

# Given a name like "Merlin-FIBdeSEMAna_23-07-10_170614_" generate the paths to the 4 tiles for it
name = "Merlin-FIBdeSEMAna_23-06-15_064124_"
z = 107
overlap = 250 # between tiles along any border

# Generate tile paths
month = name[22:24]
day = name[25:27]
tag = name[28:34]
basepath = "/net/zstore1/FIBSEM/Pedro_parker/M%s/D%s/Merlin-FIBdeSEMAna_23-%s-%s_%s_" % (month, day, month, day, tag)
paths = [basepath + "0-%i-%i.dat" % (i, j) for i in [0, 1] for j in [0, 1]]

for path in paths:
  print path


def createTrakEM2Layer(paths):
  projects = Project.getProjects()
  if 0 == projects.size():
    print "Open a new TrakEM2 project first!"
    return

  project = projects[0]
  parent = project.getRootLayerSet()
  layer = Layer(project, z, 1.0, parent)
  parent.add(layer)
  parent.recreateBuckets(layer, True)

  widths = []
  heights = []

  for path in paths:
    header = readFIBSEMHeader(path)
    widths.append(header.xRes)
    heights.append(header.yRes)

  # Add tiles in reverse order for proper Z stacking
  for i, (path, width, height) in enumerate(reversed(zip(paths, widths, heights))):
    x = (widths[i-1] - overlap) if 0 != i % 2 else 0
    y = (heights[i -2] - overlap) if i > 1 else 0
    patch = Patch(project, os.path.basename(path), widths[i], heights[i], widths[i], heights[i],
                  ImagePlus.GRAY16, 1.0, Color.yellow, False, 0, pow(2, 16) -1,
                  AffineTransform(1, 0, 0, 1, x, y), None)
    patch.setProperty("source_path", path)
    # Setup preprocessor script to decode DAT files
    project.getLoader().setPreprocessorScriptPathSilently(patch, "/home/albert/lab/scripts/python/imagej/FIBSEM/tests/dat_trakem2_preprocessor_script.py")
    # No need: it's a DAT file that can only be read properly via the preprocessor script
    #patch.cacheCurrentPath(path)
    #project.getLoader().addedPatchFrom(path, patch)
    layer.add(patch)
    patch.updateMipMaps()

createTrakEM2Layer(paths)