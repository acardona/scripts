# Capture RGB movie from stack, including ROIs and overlays
	
from ij import IJ, ImageStack, ImagePlus
from ij.process import ColorProcessor
from java.awt.image import BufferedImage as BI
from java.lang import Thread

f = ImagePlus.getDeclaredField("listeners")
f.setAccessible(True)
listeners = f.get(None)

imp = IJ.getImage()
canvas = imp.getWindow().getCanvas()

# Define range of slices to capture
slices = xrange(1, imp.getNSlices() + 1)

w, h = canvas.getWidth(), canvas.getHeight()

capture = ImageStack(w, h)

for i in slices:
  imp.setSlice(i)
  for l in listeners:
    l.imageUpdated(imp)
  Thread.sleep(50) # wait for repaints to happen, triggered by listeners, if any.
  bi = BI(w, h, BI.TYPE_INT_ARGB)
  g = bi.createGraphics()
  canvas.paint(g)
  g.dispose()
  capture.addSlice(ColorProcessor(bi))
  bi.flush()

ImagePlus("capture", capture).show()