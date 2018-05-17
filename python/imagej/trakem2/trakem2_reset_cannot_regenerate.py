from java.lang.reflect import Field, Method
from java.lang import Runtime
from ini.trakem2.persistence import FSLoader, Loader
from ini.trakem2 import Project
import os
from ij import IJ

loader = Project.getProjects()[0].getLoader()

f = FSLoader.getDeclaredField("cannot_regenerate")
f.setAccessible(True)
f.get(loader).clear()

f = Loader.getDeclaredField("hs_unloadable")
f.setAccessible(True)
f.get(loader).clear()

m = FSLoader.getDeclaredMethod("generateMipMaps", [Patch])
m.setAccessible(True)

ids = [124255, 124256, 124257, 124263, 124264, 124272, 124271]
layer = Display.getFront().getLayer()
for id in ids:
  patch = layer.findById(id)
  path = loader.getAbsolutePath(patch)
  print os.path.exists(path)
  # They open well
  # IJ.open(path)
  m.invoke(loader, patch)
