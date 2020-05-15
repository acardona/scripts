# Example deque
from collections import deque
from ij import IJ, ImagePlus, VirtualStack
from java.awt.event import KeyAdapter, KeyEvent as KEY
from itertools import islice

class KeyboardListener(KeyAdapter):
  # Shared across all instances
  moves = {KEY.VK_LEFT: -1,
           KEY.VK_UP:   -1,
           KEY.VK_RIGHT: 1,
           KEY.VK_DOWN:  1}

  # Constructor
  def __init__(self, imp, dstack):
    self.imp = imp
    self.dstack = dstack
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
    n = KeyboardListener.moves.get(key, 0)
    if 0 != n:
      self.dstack.shiftSlicesBy(n)
      event.consume()
    elif KEY.VK_R == key:
      self.dstack.reset()
      event.consume()
    elif KEY.VK_M == key:
      self.dstack.mirrorSlicesAt(self.imp.getCurrentSlice())
      event.consume()
    elif KEY.VK_W == key:
      if not event.isControlDown(): # otherwise, left control+W close the window
        width = IJ.getNumber("Window width:", min(7, self.dstack.size()))
        if not (IJ.CANCELED == width):
          self.dstack.windowAroundSlice(self.imp.getCurrentSlice(), width)
        event.consume()
    if event.isConsumed():
      # Refresh
      self.imp.setStack(self.dstack)
    else:
      # Run pre-existing key listeners
      for l in self.listeners.get(event.getSource(), []):
        if not event.isConsumed():
          l.keyPressed(event)


class DequeStack(VirtualStack):
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

  def reset(self):
    self.sliceIndices = deque(xrange(1, self.stack.size() + 1))

  def windowAroundSlice(self, slice_index, width): # slice_index is 1-based
    if 0 == width % 2: # if width is an even number
      width += 1 # must be odd: current slice remains at the center
    # New indices
    half = int(width / 2)
    first = max(slice_index - half, 0)
    last  = min(slice_index + half, len(self.sliceIndices))
    self.sliceIndices = deque(islice(self.sliceIndices, first, last + 1))


imp = IJ.getImage() # a stack
dstack = DequeStack(imp.getStack())
dimp = ImagePlus("deque " + imp.getTitle(), dstack)
dimp.show()

# After it shows in an ImageWindow with an ImageCanvas, setup key listeners
KeyboardListener(dimp, dstack)
