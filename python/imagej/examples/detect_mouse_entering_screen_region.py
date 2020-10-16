from java.awt import MouseInfo, Rectangle
from java.util.concurrent import Executors, TimeUnit
import sys

region = Rectangle(500, 500, 400, 400)
outside = True

def regionEntered():
  global outside
  try:
    point = MouseInfo.getPointerInfo().getLocation()
    print point
    if region.contains(point):
      if outside:
        print "ENTERED REGION"
        outside = False
    else:
      if not outside:
        print "EXITED REGION"
        outside = True
  except Exception as e:
    print sys.print_exception(e)

scheduler = Executors.newSingleThreadScheduledExecutor()
scheduler.scheduleAtFixedRate(regionEntered, 0, 100, TimeUnit.MILLISECONDS)