from net.imglib2.algorithm.math.ImgMath import compute, maximum
from net.imglib2.converter import Converters, ColorChannelOrder
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from ij import IJ, ImagePlus

# Fetch an RGB image stack (or any RGB image with more than 1 dimension)
imp_rgb = IJ.getImage() # IJ.openImage("http://imagej.nih.gov/ij/images/flybrain.zip")

img = IL.wrap(imp_rgb) # an ARGBType Img
red = Converters.argbChannel(img, 1) # a view of the ARGB red channel

# Project the last dimension using the max function
last_d = red.numDimensions() -1
op = maximum([Views.hyperSlice(red, last_d, i) for i in xrange(red.dimension(last_d))])
img_max_red = compute(op).intoArrayImg()

IL.wrap(img_max_red, "max projection of the red channel)").show()


# Now project all 3 color channels and compose an RGB image     
last_dim_index = img.numDimensions() -1
channel_stacks = [[Views.hyperSlice(Converters.argbChannel(img, channel_index),
                                    last_dim_index, slice_index)
                   for slice_index in xrange(img.dimension(last_dim_index))]
                  for channel_index in [1, 2, 3]] # 1: red, 2: green, 3: blue

channels = Views.stack([maximum(cs).view() for cs in channel_stacks])
max_rgb = Converters.mergeARGB(channels, ColorChannelOrder.RGB)

IL.wrap(max_rgb, "max RGB").show()