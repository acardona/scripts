# Example deque
from collections import deque
from ij import IJ, ImagePlus, VirtualStack
from java.awt.event import KeyAdapter
from java.awt.event.KeyEvent import VK_LEFT, VK_RIGHT, VK_UP, VK_DOWN


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
    n = Shifter.moves.get(event.getKeyCode(), 0)
    if 0 != n:
      self.cstack.shiftSlicesBy(n)
      # Doesn't work for stacks:
      # self.imp.updateAndDraw()
      # Use instead to update the rendered image:
      self.imp.setStack(self.cstack)
      event.consume()
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

  # Rotate the deque either by +1 or -1, and update the image
  def shiftSlicesBy(self, n):
    self.sliceIndices.rotate(n)

  def getProcessor(self, index):
    return self.stack.getProcessor(self.sliceIndices[index-1])


imp = IJ.getImage() # a stack
cstack = CyclicStack(imp.getStack())
cyclic = ImagePlus("cyclic " + imp.getTitle(), cstack)
cyclic.show()
# After showing it, update key listeners
Shifter(cyclic, cstack)
