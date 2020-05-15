# Example deque
from collections import deque
from ij import IJ, ImagePlus, VirtualStack
from java.awt.event import KeyAdapter
from java.awt.event.KeyEvent import VK_LEFT, VK_RIGHT, VK_UP, VK_DOWN, VK_M, VK_R, VK_W
from itertools import islice

class Shifter(KeyAdapter):
  # Shared across all Shifter instances
  moves = {VK_LEFT: -1,
           VK_UP:   -1,
           VK_RIGHT: 1,
           VK_DOWN:  1}

  # Constructor
  def __init__(self, imp, cstack):
    self.imp = imp
    self.cstack = cstack
    win = imp.getWindow()
    # Remove and store existing key listeners
    self.listeners = {c: c.getKeyListeners() for c in [win, win.getCanvas()]}
    for c, ls in self.listeners.iteritems():
      for l in ls:
        c.removeKeyListener(l)
      c.addKeyListener(self)

  # On key pressed
  def keyPressed(self, event):
    key = event.getKeyCode()
    n = Shifter.moves.get(key, 0)
    if 0 != n:
      self.cstack.shiftSlicesBy(n)
      event.consume()
    elif VK_R == key:
      self.cstack.reset()
      event.consume()
    elif VK_M == key:
      print 'M'
      self.cstack.mirrorSlicesAt(self.imp.getCurrentSlice())
      event.consume()
    elif VK_W == key:
      if not event.isControlDown(): # otherwise, left control+W close the window
        width = IJ.getNumber("Window width:", min(7, self.cstack.size()))
        if not (IJ.CANCELED == width):
          self.cstack.windowAroundSlice(self.imp.getCurrentSlice(), width)
        event.consume()
    if event.isConsumed():
      # Refresh
      self.imp.setStack(self.cstack)
    else:
      # Run pre-existing key listeners
      for l in self.listeners.get(event.getSource(), []):
        if not event.isConsumed():
          l.keyPressed(event)


class CyclicStack(VirtualStack):
  # Constructor
  def __init__(self, stack):
    # Invoke the super constructor, that is, the VirtualStack constructor
    super(VirtualStack, self).__init__(stack.getWidth(), stack.getHeight(), stack.size())
    self.stack = stack
    self.sliceIndices = deque(xrange(1, stack.size() + 1))
    self.setBitDepth(stack.getBitDepth())

  def getProcessor(self, index):
    return self.stack.getProcessor(self.sliceIndices[index-1])

  def getSize(self):
    return len(self.sliceIndices)

  def shiftSlicesBy(self, n):
    # Rotate the deque either by +1 or -1, and update the image
    self.sliceIndices.rotate(n)

  def mirrorSlicesAt(self, slice_index): # slice_index is 1-based
    # Remove slices from 0 to slice_index (exclusive), i.e. crop to from slice_index to the end
    self.sliceIndices = deque(islice(self.sliceIndices, slice_index -1, None))
    # Append at the begining, reversed, all slices after slice n (which is now at index 0 of the deque)
    self.sliceIndices.extendleft(list(islice(self.sliceIndices, 1, None))) # copy into list
    print self.sliceIndices

  def reset(self):
    self.sliceIndices = deque(xrange(1, self.stack.size() + 1))

  def windowAroundSlice(self, slice_index, width): # slice_index is 1-based
    if 0 == width % 2: # if width is an even number
      width += 1 # must be odd: current slice remains at the center
    # New indices
    half = int(width / 2)
    first = max(slice_index - half, 0)
    last  = min(slice_index + half, len(self.sliceIndices))
    print first, last
    self.sliceIndices = deque(islice(self.sliceIndices, first, last + 1))


imp = IJ.getImage() # a stack
cstack = CyclicStack(imp.getStack())
cyclic = ImagePlus("cyclic " + imp.getTitle(), cstack)
cyclic.show()
# After showing it, update key listeners
Shifter(cyclic, cstack)
