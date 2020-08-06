from ij.gui import Plot
from math import sin, cos, radians

# title, X label, Y label
plot = Plot("My data", "time", "value")

# Series 1
plot.setColor("blue")
plot.add("circle", [50 + sin(radians(i * 5)) * 50 for i in xrange(100)])

# Series 2
plot.setColor("magenta")
plot.add("diamond", [50 + cos(radians(i * 5)) * 50 for i in xrange(100)])

# Series 3
plot.setColor("black")
plot.add("line", [50 + cos(-1.0 + radians(i * 5)) * 50 for i in xrange(100)])

plot.show()
