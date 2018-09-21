from ij import IJ
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views

# Load an image (of any dimensions)
imp = IJ.getImage()
# Convert to 8-bit if it isn't yet, using macros
IJ.run(imp, "8-bit", "")

# Access its pixel data from an ImgLib2 data structure: a RandomAccessibleInterval
img = IL.wrapReal(imp)

# View as an infinite image, with value zero outside of where the image is defined
imgE = Views.extendZero(img)

# Limit the infinite image with an interval twice as large as the original image.
# So it starts at e.g. minus half the image width, and ends at 1.5x the image width.
# The original image will be at the center.
minC = [int(-0.5 * img.dimension(i)) for i in range(img.numDimensions())]
maxC = [int( 1.5 * img.dimension(i)) for i in range(img.numDimensions())]
imgL = Views.interval(imgE, minC, maxC)

# Visualize the enlarged canvas, so to speak
imp2 = IL.wrap(imgL, imp.getTitle() + " - enlarged canvas") # an ImagePlus
imp2.show()

# Or view mirroring the data beyond the edges
imgE = Views.extendMirrorSingle(img)
imgL = Views.interval(imgE, minC, maxC)

# Visualize the enlarged canvas, so to speak
imp2 = IL.wrap(imgL, imp.getTitle() + " - enlarged canvas") # an ImagePlus
imp2.show()