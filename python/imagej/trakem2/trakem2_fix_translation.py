# Translate any selected Displayable objects

dx = -90
dy = 129

from ini.trakem2.display import Display

# For any selected objected
for displ in Display.getFront().getSelected():
  displ.getAffineTransform().translate(dx, dy)

Display.repaint()
