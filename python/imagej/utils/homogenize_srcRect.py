# Make all open images show the same area of the image.
# Of course this only works as intended if all images are of the same size.

from ij import IJ, WindowManager

srcRect = None

for ID in WindowManager.getIDList():
  imp = WindowManager.getImage(ID)
  if not srcRect:
    srcRect = imp.getWindow().getCanvas().getSrcRect()
    print srcRect
  else:
    imp.getWindow().getCanvas().setSourceRect(srcRect)
    imp.updateAndDraw()