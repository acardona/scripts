# Example library file. Save to e.g. /tmp/mylib.py
from ij import ImagePlus, ImageStack, WindowManager as WM

def imagesToStack(ref_imp=None, imps=None):
  """ Return a stack with all open images of the same dimensions
      and pixel type as its slices, relative to the ref_imp.
      If a suitable open image is a stack, all its slices will be included,
      effectively concatenating all open stacks.
 
      ref_imp: the reference ImagePlus, determining the dimensions and
               pixel type of the images to include. Can be None (default),
               in which case the current active image will be used
      imps: the list of ImagePlus to concatenate. Can be None (default)
            in which case all suitable open images will be concatenated

      Returns an ImagePlus containing the ImageStack. """
  # Get list of images to potentially include
  ids = WM.getIDList()
  if not ids:
    print "No open images!"
    return
  imps = imps if imps else map(WM.getImage, ids)
  ref_imp = ref_imp if ref_imp else WM.getCurrentImage()
  # Dimensions and pixel type of the reference image
  width, height = ref_imp.getWidth(), ref_imp.getHeight()
  impType = ref_imp.getType()
  # The new stack containing all images of the same dimensions and type as ref_imp
  stack_all = ImageStack(width, height)
  for imp in imps:
    # Include only if dimensions and pixel type match those of ref_imp
    if imp.getWidth() == width and imp.getHeight() == height and imp.getType() == impType:
      title = imp.getTitle()
      # If the imp is a single-slice image, works anyway: its stack has 1 slice
      stack = imp.getStack()
      for slice in xrange(1, stack.getSize() + 1):
        ip = stack.getProcessor(slice).duplicate() # 1-based slice indexing
        stack_all.addSlice("%s-%i" % (title, slice), ip)
  return ImagePlus("all", stack_all)


from ij import IJ

# Open the blobs image  
blobs_imp = IJ.openImage("http://imagej.nih.gov/ij/images/blobs.gif")
blobs_imp.show()

# Create a copy and invert it
ip = blobs_imp.getProcessor().duplicate()
ip.invert()
blobs_inv = ImagePlus("blobs inverted", ip)
blobs_inv.show()
  
# Concatenate all images of the same type (8-bit) and dimensions as blobs.gif  
imp_all = imagesToStack(ref_imp=blobs_imp)  
imp_all.show() 