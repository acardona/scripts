from ij import IJ, ImagePlus, ImageStack
from java.util.concurrent import Executors, Callable
from java.lang import Thread

imp4D = IJ.getImage()
stack = imp4D.getStack()

slice_index = 160

stack2 = ImageStack(imp4D.width, imp4D.height)
depth = 325
n_frames = 800

class Task(Callable):
  """ A wrapper for executing functions in concurrent threads. """
  def __init__(self, fn, *args, **kwargs):
    self.fn = fn
    self.args = args
    self.kwargs = kwargs
  def call(self):
    t = Thread.currentThread()
    if t.isInterrupted() or not t.isAlive():
        return None
    return self.fn(*self.args, **self.kwargs)


def getProcessor(index):
  return stack.getProcessor(index).convertToShort(False)

exe = Executors.newFixedThreadPool(32)

try:
  futures = [exe.submit(Task(getProcessor, frame_index * depth + slice_index + 1))
             for frame_index in xrange(n_frames)]
  imp2 = None
  for f in futures:
    stack2.addSlice(f.get())
    if imp2 is None and stack2.size() > 1:
      imp2 = ImagePlus("hyperslice at %i" % slice_index, stack2)
      imp2.show()

finally:
  exe.shutdownNow()

