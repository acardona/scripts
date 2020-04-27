from ij import IJ
from java.util import EventListener
import operator

imp = IJ.getImage()
canvas = imp.getWindow().getCanvas()

def spyEvent(self, event):
  print event

def findEventInterfaces(*classes): # one or more
  # Gather all interfaces that extend EventListener
  classes = list(classes) # turn a tuple argument into a list
  event_interfaces = set([])
  while len(classes) > 0:
    cl = classes.pop() # remove the last one
    if cl.isInterface() and list(cl.getInterfaces()).count(EventListener) > 0:
      event_interfaces.add(cl)
      continue
    # Else, search its superclass and its implemented interfaces
    sup = cl.getSuperclass()
    if sup:
      classes.append(sup)
    for interface in cl.getInterfaces():
      classes.append(interface)
  return event_interfaces

# ImageJ main window deals with KeyListener, so use it too to search for interfaces
obs = [canvas, IJ.getInstance()]
classes = map(lambda x: x.getClass(), obs)

# Add spying instances of each event interface to the image canvas
for i, interface in enumerate(findEventInterfaces(*classes)):
  # Find the method, if it exists, like "addMouseListener" for "MouseListener"
  adder = getattr(canvas, "add" + interface.getSimpleName(), None)
  if adder:
    # Dynamically create a class that implements the interface
    # with all its methods using the spyEvent function to print the event
    methods = {method.getName(): spyEvent for method in interface.getDeclaredMethods()}
    event_listener_class = type('EventInterface_%i' % i, # the name of the new class
                                (interface,), # the tuple of interfaces that it implements
                                methods) # the dictionary of method names vs functions
    adder(event_listener_class()) # add a new instance
  