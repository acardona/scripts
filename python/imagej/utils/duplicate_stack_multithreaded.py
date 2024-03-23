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

def duplicateInParallel(imp=None, slices=None, n_threads=0, shallow=False, show=True):
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
    imp = ImagePlus("%s - [%i, %i]" % (imp.getTitle(), slices[0], slices[-1]), stack2)
    if show:
      imp.show()
    return imp
  finally:
    exe.shutdown()


imp = IJ.getImage()
# NC_Hypathia transition from 2x2 tiles to single tile
#copy = duplicateInParallel(imp, range(3490, 3493), n_threads=10, shallow=True)

copy = duplicateInParallel(imp, range(3470, 3520), n_threads=50, shallow=True, show=True)

copy = duplicateInParallel(imp, range(1990, 2010), n_threads=50, shallow=True, show=True)


#copy = duplicateInParallel(imp, range(9000, 9020), n_threads=50, shallow=True)

#copy = duplicateInParallel(imp, range(11885, 12054), n_threads=50, shallow=True, show=True)