# Max-project in chunks an image stack.
# Grabs the current image and generates views of Z-projections
# every 5 slices.
# The last projection may have been projected from less than 5 slices
# if the total number of slices is not a multiple of 5.
# All done with views: actual math happens only upon showing the image.

from net.imglib2.view import Views
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.algorithm.math.ImgMath import minimum, maximum
from ij import IJ

imp = IJ.getImage()
img = Views.dropSingletonDimensions(IL.wrap(imp))
m = img.maxAsLongArray()

# The number of Z slices to project together
inc = 5

# The function to use for projecting
project = maximum # other possibilities: minimum, add, subtract, ...

chunks = [[Views.hyperSlice(img, 2, i)
           for i in xrange(z, min(z + inc, m[2]), 1)]
          for z in xrange(0, m[2], inc)]

imgChunkProjected = Views.stack([project(chunk).view() for chunk in chunks])

impCP = IL.show(imgChunkProjected, "Chunk-projected every " + str(inc))


# Another approach would use Converters.collapse(Views.interval ... on z axis)
# and Converters.compose with a function to run the projecting function on the vector for each pixel.


