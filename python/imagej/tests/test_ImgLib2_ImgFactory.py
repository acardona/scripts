from net.imglib2.img.array import ArrayImgFactory
from net.imglib2.type.numeric.integer import UnsignedByteType, UnsignedShortType
from net.imglib2.util import Intervals

# An 8-bit 256x256x256 volume
img = ArrayImgFactory(UnsignedByteType()).create([256, 256, 256])

# Another image of the same type and dimensions, but empty
img2 = img.factory().create([img.dimension(d) for d in xrange(img.numDimensions())])

# Same, but easier reading of the image dimensions    
img3 = img.factory().create(Intervals.dimensionsAsLongArray(img))

# Same, but use an existing img as an Interval from which to read out the dimensions
img4 = img.factory().create(img)

# Now we change the type: same kind of image and same dimensions,
# but crucially a different pixel type (16-bit) via a new ImgFactory
imgShorts = img.factory().imgFactory(UnsignedShortType()).create(img)
