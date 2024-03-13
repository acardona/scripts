# Duplicate a stack in paralle
from java.util.concurrent import Callable, Future, Executors
from java.lang import Runtime
from ij import IJ, ImagePlus, ImageStack

class Copy(Callable):
  def __init__(self, stack, slice_index, shallow=False):
    self.stack = stack
    self.slice_index = slice_index # 1-based
    self.shallow = shallow
  def call(self):
    ip = self.stack.getProcessor(self.slice_index)
    return ip if self.shallow else ip.duplicate()

def duplicateInParallel(imp=None, slices=None, n_threads=0, shallow=False):
  """ imp: defaults to None, meaning get the current image.
      slices: defaults to None, meaning all. Otherwise a list of 1-based indices.
      n_threads: defaults to 0, meaning as many as possible.
      shallow: defaults to False, meaning don't share the pixel data.
  """
  imp = imp if imp else IJ.getImage()
  slices = slices if slices else range(1, imp.getNSlices() + 1)
  stack = imp.getStack()
  exe = Executors.newFixedThreadPool(n_threads if n_threads > 0 else min(Runtime.getRuntime().availableProcessors(), stack.getSize()))
  try:
    stack2 = ImageStack(imp.getWidth(), imp.getHeight())
    futures = [(i, exe.submit(Copy(stack, i, shallow))) for i in slices]
    for i, fu in futures:
      label = stack.getSliceLabel(i)
      stack2.addSlice(label if label else str(i), fu.get())
    return ImagePlus("%s - [%i, %i]" % (imp.getTitle(), slices[0], slices[-1]), stack2)
  finally:
    exe.shutdown()


imp = IJ.getImage()
copy = duplicateInParallel(imp, range(3490, 3493), n_threads=10, shallow=True)
copy.show()