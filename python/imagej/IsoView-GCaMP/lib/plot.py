from ij.gui import Plot
from roi import roiPoints
from util import syncPrint
from java.awt import BasicStroke, Color
from java.io import File
from java.lang import Double
from java.util import ArrayList, TreeMap
from javax.swing import JFrame
from org.jfree.chart import ChartFactory, ChartPanel, JFreeChart
from org.jfree.chart.plot import PlotOrientation, XYPlot
from org.jfree.chart.renderer.xy import StandardXYBarPainter, XYBarRenderer
from org.jfree.chart.util import ExportUtils
from org.jfree.data.statistics import HistogramDataset, HistogramType
from ij import ImagePlus
from ij.process import ColorProcessor


def plot2DRoiOverZ(imp, roi=None, show=True, XaxisLabel='Z', YaxisLabel='I', Zscale=1.0):
  """
  Take an ImagePlus and a 2D ROI (optional, can be read from the ImagePlus)
  and plot the average value of the 2D ROI in each Z slice.

  Return 4 elements: the two lists of values for the Y (intensity) and X (slice index),
  and the Plot and PlotWindow instances.
  """
  roi = roi if roi else imp.getRoi()
  if not roi:
    syncPrint("Set a ROI first.")
    return
  # List of 2D points from where pixel values are to be read
  points = roiPoints(roi)
  stack = imp.getStack()
  intensity = [sum(stack.getProcessor(slice_index).getf(p.x, p.y) for p in points) / len(points)
               for slice_index in xrange(1, imp.getNSlices() + 1)]
  xaxis = [z * Zscale for z in range(1, imp.getNSlices() + 1)]
  plot = Plot("Intensity", XaxisLabel, YaxisLabel, xaxis, intensity)
  if show:
    win = plot.show()
  else:
    win = None
  return intensity, xaxis, plot, win


def setTheme(chart):
  """ Takes a JFreeChart as argument and sets its rendering style to sensible defaults.
      See javadoc at http://jfree.org/jfreechart/api/javadoc/index.html """
  plot = chart.getPlot()
  r = plot.getRenderer()
  r.setBarPainter(StandardXYBarPainter())
  r.setSeriesOutlinePaint(0, Color.lightGray)
  r.setShadowVisible(False)
  r.setDrawBarOutline(False)
  gridStroke = BasicStroke(1.0, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND, 1.0, (2.0, 1.0), 0.0)
  plot.setRangeGridlineStroke(gridStroke)
  plot.setDomainGridlineStroke(gridStroke)
  plot.setBackgroundPaint(Color(235, 235, 235))
  plot.setRangeGridlinePaint(Color.white)
  plot.setDomainGridlinePaint(Color.white)
  plot.setOutlineVisible(False)
  plot.getDomainAxis().setAxisLineVisible(False)
  plot.getRangeAxis().setAxisLineVisible(False)
  plot.getDomainAxis().setLabelPaint(Color.gray)
  plot.getRangeAxis().setLabelPaint(Color.gray)
  plot.getDomainAxis().setTickLabelPaint(Color.gray)
  plot.getRangeAxis().setTickLabelPaint(Color.gray)
  chart.getTitle().setPaint(Color.gray)


def renderHistogram(values, n_bins, min_max=None, title="Histogram", show=True, setThemeFn=setTheme):
  """ values: a list or array of numeric values.
      n_bins: the number of bins to use.
      min_max: defaults to None, a tuple with the minimum and maximum value.
      title: defaults to "Histogram", must be not None.
      show: defaults to True, showing the histogram in a new window.
      setThemeFn: defaults to setTheme, can be None or another function that takes a chart
               as argument and sets rendering colors etc.
      Returns a tuple of the JFreeChart instance and the window JFrame, if shown.
  """
  hd = HistogramDataset()
  hd.setType(HistogramType.RELATIVE_FREQUENCY)
  print min_max
  if min_max:
    hd.addSeries(title, values, n_bins, min_max[0], min_max[1])
  else:
    hd.addSeries(title, values, n_bins)
  chart = ChartFactory.createHistogram(title, "", "", hd, PlotOrientation.VERTICAL,
                                       False, False, False)
  if setThemeFn:
    setThemeFn(chart)
  frame = None
  if show:
    frame = JFrame(title)
    frame.getContentPane().add(ChartPanel(chart))
    frame.pack()
    frame.setVisible(True)
  return chart, frame


def chartAsImagePlus(chart, frame):
  """ Given a JFreeChart and its JFrame, return an ImagePlus of type COLOR_RGB. """
  panel = frame.getContentPane().getComponent(0) # a ChartPanel
  dimensions = panel.getSize()
  bimg = chart.createBufferedImage(dimensions.width, dimensions.height)
  return ImagePlus(str(chart.getTitle()), ColorProcessor(bimg))


def saveChartAsSVG(chart, filepath, frame=None, dimensions=None):
  """ chart: a JFreeChart instance.
      filepath: a String or File describing where to store the SVG file.
      frame: defaults to None, can be a JFrame where the chart is shown.
      dimensions: defaults to None, expects an object with width and height fields.
      If both frame and dimensions are None, uses 1024x768 as dimensions. """
  if dimensions:
    width, height = dimensions.width, dimensions.height
  elif frame:
    panel = frame.getContentPane().getComponent(0) # a ChartPanel
    dimensions = panel.getSize()
    width, height = dimensions.width, dimensions.height
  else:
    width = 1024
    height = 768
  ExportUtils.writeAsSVG(chart, width, height, File(filepath))
