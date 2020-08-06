from ij.gui import Plot
from math import sin, radians
plot = Plot("My data", "time", "value")
plot.setColor("blue")
plot.add("circle", [sin(radians(i)) for i in xrange(1000)])
plot.show()