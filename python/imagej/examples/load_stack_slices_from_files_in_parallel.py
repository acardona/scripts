# Load stack slices in parallel
import os
from ij import IJ, ImagePlus, ImageStack
from java.util.concurrent import Executors, Callable
from java.util import LinkedList
from java.lang import Thread

# Directory with a listing of file names
src = "/home/albert/lab/google-drive/lizard 3.3773um 80 kV 7 W bin 2 LE3 BH0.25 RF0.5/"
extension = ".tiff"

class Load(Callable):
  def __init__(self, filepath):
    self.filepath = filepath
  def call(self):
    return IJ.openImage(self.filepath)

# Assumes the Google Drive is mounted via rclone --transfers 8
# and that the CPU has at least 8 cores
exe = Executors.newFixedThreadPool(8)

try:
  filenames = sorted(filename for filename in os.listdir(src) if filename.endswith(extension))
  futures = LinkedList()

  for filename in filenames:
    futures.add(exe.submit(Load(os.path.join(src, filename))))

  stack = ImageStack()

  count = 0
  impStack = None

  while not futures.isEmpty():
    #
    if Thread.currentThread().isInterrupted():
      print "Interrupted"
      break
    #
    imp = futures.removeFirst().get()
    stack.addSlice("", imp.getProcessor())

    if not impStack:
      # Show it right away with the first slice, will update dynamically
      impStack = ImagePlus(os.path.basename(src), stack)
      impStack.show()
    
    count += 1
    print "Loaded %i/%i" % (count, len(filenames))
    impStack.repaintWindow()

finally:
  exe.shutdownNow()





