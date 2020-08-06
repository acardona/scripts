from ij import IJ
from java.lang import Class
import sys, re

imp = IJ.getImage()
canvas = imp.getWindow().getCanvas()

def spyEvent(self, event):
  print event

# Remove any listeners whose class name ends with "_spy"
for name in dir(canvas):
  g = re.match(r'^get(.+Listener)s$', name) # e.g. getMouseListeners
  if g:
    interface_name = g.groups()[0] # e.g. MouseListener
    for listener in getattr(canvas, name)(): # invoke 'name' method
      if listener.getClass().getSimpleName().startswith(interface_name + "_spy"):
        getattr(canvas, "remove" + interface_name)(listener)
        print "Removed existing spy listener", listener.getClass()

# Look for methods of canvas named like "addMouseListener"
for name in dir(canvas):
  g = re.match(r'^add(.+Listener)$', name) # e.g. addMouseListener
  if g:
    interface_name = g.groups()[0] # e.g. MouseListener
    try:
      # Try to find the event interface in the java.awt.event package (may fail if wrong package)
      interface_class = Class.forName("java.awt.event." + interface_name)
      # Define all methods of the interface to point to the spyEvent function
      methods = {method.getName(): spyEvent for method in interface_class.getDeclaredMethods()}
      # Define a new class on the fly
      new_class = type(interface_name + "_spy", # name of newly defined class
                       (interface_class,), # tuple of implemented interfaces and superclasses
                       methods)
      # add a new instance of the listener class just defined
      getattr(canvas, name)(new_class())
    except:
      print sys.exc_info()