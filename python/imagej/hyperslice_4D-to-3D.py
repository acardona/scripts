from ij import IJ, ImagePlus, ImageStack
from java.util.concurrent import Executors, Callable
from java.lang import Thread
import sys
sys.path.append("//home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.util import Task

imp4D = IJ.getImage()
stack = imp4D.getStack()

# The selected stack slice
slice_index = imp4D.getSlice()
# The selected channel
channel_index = imp4D.getChannel()

stack2 = ImageStack(imp4D.width, imp4D.height)
depth = imp4D.getNSlices()
n_frames = imp4D.getNFrames()


def getProcessor(frame_index):
  stack_index = imp4D.getStackIndex(channel_index, slice_index, frame_index)
  return stack.getProcessor(stack_index).convertToShort(False)

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

