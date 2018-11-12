# Duplicate a hyperstack reducing dimensionality in the Z axis,
# opening a new stack with XYT (no Z).

from ij import IJ, ImagePlus, ImageStack

imp = IJ.getImage()
stack1 = imp.getStack()

# Fixed Z position
slice_index = imp.getSlice()# 1-based

stack2 = ImageStack(imp.getWidth(), imp.getHeight())

for frame_index in xrange(imp.getNFrames()):
  i = frame_index * imp.getNSlices() + slice_index
  stack2.addSlice(str(frame_index), stack1.getPixels(i))

ImagePlus(imp.getTitle() + " - fixed Z=" + str(slice_index), stack2).show()