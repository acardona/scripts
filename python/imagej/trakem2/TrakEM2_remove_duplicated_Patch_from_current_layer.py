from ini.trakem2.display import Display, Patch

unique = set()
for patch in Display.getFront().getLayer().getDisplayables(Patch):
  path = patch.getImageFilePath()
  if path in unique:
    patch.remove(False)
  else:
    unique.add(path)

Display.repaint()