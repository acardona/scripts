from ini.trakem2 import Project
from ini.trakem2.display import Patch

project = Project.getProjects()[0]

for layer in project.getRootLayerSet().getLayers():
  for patch in layer.getDisplayables(Patch):
    if patch.isVisible():
      patch.updateMipMaps()