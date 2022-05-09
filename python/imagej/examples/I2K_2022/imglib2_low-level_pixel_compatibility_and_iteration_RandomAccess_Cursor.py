from net.imglib2.img.display.imagej import ImageJFunctions
from ij import IJ
from jarray import zeros
from net.imglib2.img.array import ArrayImgs
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.util import ImgUtil

imp = IJ.getImage()
dimensions = [imp.getWidth(), imp.getHeight()]

# Would wrap the image in a way that, while most often compatible with ArrayImg,
# it is not guaranteed to be:

# img = ImageJFunctions.wrap(imp)  # gave a "false" False!! for iterationOrder.equals,
                                   # because the wrap is a CellImg even if its a single slice

# So instead we "steal" the pixel array from the ImageProcessor and give it to an ArrayImg:
pixels = imp.getProcessor().getPixels()
img = ArrayImgs.unsignedBytes(pixels, dimensions)

img2 = ArrayImgs.floats(dimensions)

# Now the iteration order is "True": equal and compatible across both images
print img.iterationOrder().equals(img2.iterationOrder())

# For low-level access to the pixels, use:

# RandomAccess
# Cursor

# An array that expresses the position of a pixel in the image, for RandomAccess (a Positionable)
pos = zeros(2, 'l') # "l" for long

# Let's pick a pixel coordinate in 2D
pos[0] = 128
pos[1] = 200

ra = img.randomAccess()
ra.setPosition(pos)
t = ra.get()  # returns the Type class, which could be e.g. UnsignedByteType
              # which provides access to the pixel at that position
print type(t) # Print the Type class

# To print the pixel value, it's one level of indirection away, so do any of:
print t.get() # the native primitive type, e.g., byte
print t.getRealFloat()
print t.getRealDouble()


# To copy two images that are compatible in their iteration order, use cursors:
cursor = img.cursor()
cursor2 = img2.cursor()
for t in cursor:
  cursor2.next().setReal(t.getRealFloat())
  
# The above is very slow in jython due to iteration overheads.
# Instead, do: (as fast as possible, even multithreaded)
ImgUtil.copy(img, img2)


ImageJFunctions.show(img2, "copied")

# For low-level operations in jython, you can inline small snippets of java code using the Weaver.
# Search for "Weaver" in the tutorial for several examples:
# https://syn.mrc-lmb.cam.ac.uk/acardona/fiji-tutorial
