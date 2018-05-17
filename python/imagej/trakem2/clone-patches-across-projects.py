from ini.trakem2 import Project
from ini.trakem2.display import Display

projects = Project.getProjects()

original = projects[0]
new_project = projects[1]

patches = None
layer2 = None

for display in Display.getDisplays():
  if display.getProject() == original:
    patches = display.getSelection().getSelected()
  elif display.getProject() == new_project:
    layer2 = display.getLayer()


for patch in patches:
  layer2.add(patch.clone(new_project, True))