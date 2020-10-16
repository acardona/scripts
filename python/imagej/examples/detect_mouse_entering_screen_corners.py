from java.awt import MouseInfo, Rectangle, Toolkit
from java.util.concurrent import Executors, TimeUnit
import sys
from ij import IJ

# Dimensions of an action region
w, h = 50, 50
# Dimensions of the whole screen
screen = Toolkit.getDefaultToolkit().getScreenSize()

# Dictionary of action region names vs. tuple of area and ImageJ command with macro arguments
corners = {'top-left': (Rectangle(0, 0, w, h),
                        ["Capture Screen"]),
           'top-right': (Rectangle(screen.width - w, 0, w, h),
                         ["Split Channels"]),
           'bottom-right': (Rectangle(screen.width - w, screen.height - h, w, h),
                            ["Z Project...", "projection=[Max Intensity]"]),
           'bottom-left': (Rectangle(0, screen.height - h, w, h),
                           ["Dynamic ROI Profiler"])}

# State: whether the mouse is outside any of the action regions
outside = True

def actionRegion():
  global outside # will be modified, so import for editing with 'global'
  try:
    point = MouseInfo.getPointerInfo().getLocation()
    inside = False
    # Check if the mouse is in any of the action regions
    for name, (corner, macroCommand) in corners.iteritems():
      if corner.contains(point):
        inside = True
        if outside:
          print "ENTERED", name
          IJ.run(*macroCommand)
          outside = False
    if not inside:
      outside = True
  except:
    print sys.exc_info()

scheduler = Executors.newSingleThreadScheduledExecutor()
scheduler.scheduleAtFixedRate(actionRegion, 0, 100, TimeUnit.MILLISECONDS)
