# I2K 2022 example script: illustrate use of ImgLib2 views
# Albert Cardona 2022

from ij import IJ
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from org.scijava.plugins.scripteditor.jython import JythonDev
JythonDev.debug = 2

# Grab the ImagePlus from the most recently activated Fiji image window
imp = IJ.getImage()

# Convert the image to an ImgLib2 image
img = IL.wrap(imp)

# Show it
IL.show(img, "wrapped as an ImgLib2 image")

# Extend it: an infinite view
extendedView = Views.extendMirrorSingle(img)

# View with a larger canvas
width = img.dimension(0)  # same as imp.getWidth()
height = img.dimension(1) # same as imp.getHeight()

# from half an image beyond 0,0 (to the left and up) to half an image beyond width,height
imgExtended = Views.interval(extendedView, [-width/2,
                                            -height/2],
                                           [width + width/2,
                                            height + height/2])

IL.show(imgExtended, "enlarged canvas with extended mirror symmetry")

# The viewing interval doesn't have to overlap with the interval where the original image is defined
# For example:

imgSomewhere = Views.interval(extendedView, [41000, 60000],
                                            [42000, 61000])

IL.show(imgSomewhere, "Arbitrary interval somewhere")

# Other forms of extended views:
extendedEmptyView = Views.extendZero(img)
extendedValueView = Views.extendValue(img, 50)

# Find out the pixel type and its min and max values
t = img.randomAccess().get()
min_value = t.getMinValue() # minimum value for the pixel type
max_value = t.getMaxValue() # maximum
extendedRandomView = Views.extendRandom(img, min_value, max_value)
imgExtRandom = Views.interval(extendedRandomView, [-width/2,
                                                   -height/2],
                                                  [width + width/2,
                                                   height + height/2])

IL.show(imgExtRandom, "extended with random noise")

