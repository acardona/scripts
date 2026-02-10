from ini.trakem2.display import Display, Patch

for layer in Display.getFront().getLayer().getParent().getLayers():
  r = layer.getMinimalBoundingBox(Patch)
  print layer.getZ(), r
  for patch in layer.getDisplayables(Patch):
    print "will translate:", -r.x, -r.y
    patch.translate(-r.x, -r.y)

Display.repaint()