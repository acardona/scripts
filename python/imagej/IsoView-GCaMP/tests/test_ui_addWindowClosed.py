import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.ui import addWindowListener
from ij import ImagePlus
from ij.process import ByteProcessor

imp = ImagePlus("test", ByteProcessor(10, 10))
imp.show()
window = imp.getWindow()

def report(event):
  print "window closed:", event.getSource().getTitle()

addWindowListener(window, report)
window.dispose()

# Prints: "window closed: test"