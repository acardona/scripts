from ij import IJ
from org.jfree.chart import ChartFactory, ChartPanel
from org.jfree.data.statistics import HistogramDataset, HistogramType
from javax.swing import JFrame
from java.awt import Color

imp = IJ.getImage()
pixels = imp.getProcessor().convertToFloat().getPixels()

# Data and parameter of the histogram
values = list(pixels)
n_bins = 256 # number of histogram bins

# Construct the histogram from the pixel data
hist = HistogramDataset()
hist.setType(HistogramType.RELATIVE_FREQUENCY)
hist.addSeries("my data", values, n_bins)

# Create a JFreeChart histogram
chart = ChartFactory.createHistogram("My histogram", "the bins", "counts", hist)

# Adjust series color
chart.getXYPlot().getRendererForDataset(hist).setSeriesPaint(0, Color.blue)

# Show the histogram in an interactive window
# where the right-click menu enables saving to PNG or SVG, and adjusting properties
frame = JFrame("Histogram window")
frame.getContentPane().add(ChartPanel(chart))
frame.pack()
frame.setVisible(True)
