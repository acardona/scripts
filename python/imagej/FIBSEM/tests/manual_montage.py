from ini.trakem2.display import Patch
from ini.trakem2 import Project
import os, sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.io import readFIBSEMHeader, readFIBSEMdat
from java.awt import Color
from ij import ImagePlus
from java.awt.geom import AffineTransform

def createTrakEM2Layer():
  projects = Project.getProjects()
  if 0 == projects.size():
    print "Open a new TrakEM2 project first!"
    return

  paths = [
    "/home/albert/Desktop/t2/Pedro_Parker/failed SIFT montage 23-07-10_170164/Merlin-FIBdeSEMAna_23-07-10_170614_0-0-0.dat",
    "/home/albert/Desktop/t2/Pedro_Parker/failed SIFT montage 23-07-10_170164/Merlin-FIBdeSEMAna_23-07-10_170614_0-0-1.dat",
    "/home/albert/Desktop/t2/Pedro_Parker/failed SIFT montage 23-07-10_170164/Merlin-FIBdeSEMAna_23-07-10_170614_0-1-0.dat",
    "/home/albert/Desktop/t2/Pedro_Parker/failed SIFT montage 23-07-10_170164/Merlin-FIBdeSEMAna_23-07-10_170614_0-1-1.dat"
  ]

  overlap = 250
  
  project = projects[0]
  layer = project.getRootLayerSet().getLayers().get(0)

  widths = []
  heights = []

  for path in paths:
    header = readFIBSEMHeader(path)
    widths.append(header.xRes)
    heights.append(header.yRes)

  for i, (path, width, height) in enumerate(zip(paths, widths, heights)):
    x = (widths[i-1] - overlap) if 0 != i % 2 else 0
    y = (heights[i -2] - overlap) if i > 1 else 0
    patch = Patch(project, os.path.basename(path), widths[i], heights[i], widths[i], heights[i],
                  ImagePlus.GRAY16, 1.0, Color.yellow, False, 0, pow(2, 16) -1,
                  AffineTransform(1, 0, 0, 1, x, y), None)
    patch.setProperty("source_path", path)
    # Use this very same script as the preprocessor script
    project.getLoader().setPreprocessorScriptPathSilently(patch, "/home/albert/lab/scripts/python/imagej/FIBSEM/tests/dat_trakem2_preprocessor_script.py")
    layer.add(patch)
    patch.updateMipMaps()

createTrakEM2Layer()