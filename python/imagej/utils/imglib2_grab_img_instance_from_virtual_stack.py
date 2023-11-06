# Grab the RandomAccessibleInterval from an ImageJ virtual stack that wraps one

from ij import IJ
from net.imglib2.img.display.imagej import ImageJVirtualStack

imp = IJ.getImage()
stack = imp.getStack() # an ImageJVirtualStackUnsignedShort or similar (for each pixel type) which extends ImageJVirtualStack which has a source field with the ImgLib2 RandomAccessibleInterval instance
print type(stack)

if isinstance(stack, ImageJVirtualStack):
  # Make the private field accessible
  f = ImageJVirtualStack.getDeclaredField("source")
  f.setAccessible(True)
  img = f.get(stack)

  print img # A LazyCellImg

else:
  print "Not an instance of ImageJVirtualStack"