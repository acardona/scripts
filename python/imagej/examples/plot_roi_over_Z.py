import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.plot import plot2DRoiOverZ
from ij import IJ
from ij.gui import Roi
from java.awt import Color
from math import sin, radians

#imp = IJ.openImage("http://imagej.nih.gov/ij/images/bat-cochlea-volume.zip")
imp = IJ.getImage()
imp.setRoi(Roi(69, 93, 5, 5))
IJ.run(imp, "Gaussian Blur...", "sigma=10 stack") # to make it more interesting

intensity, xaxis, plot, win = plot2DRoiOverZ(imp)

# Can be "circle", "dot", "box", "x", "cross", "bar", "separated bar", "connected circle", "line"
#        "diamond", "triangle", or "filled".
plot.setColor(Color.red)
plot.add("circle", [50 + sin(radians(index * 5)) * 50 for index in xrange(len(intensity))])