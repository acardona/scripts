# I2K 2022 example script: illustrate wrapping an ImagePlus and exploring the class hierarchy
# Albert Cardona 2022

from ij import IJ
from net.imglib2.img.display.imagej import ImageJFunctions as IL

# Grab the ImagePlus from the most recently activated Fiji image window
imp = IJ.getImage()

# Convert the image to an ImgLib2 image
img = IL.wrap(imp)

# peek into the type of img
print type(img) # Prints: net.imglib2.img.imageplus.ByteImagePlus

print type(img).getGenericSuperclass()
# Prints:
# net.imglib2.img.imageplus.ImagePlusImg<T, net.imglib2.img.basictypeaccess.array.ByteArray>

print type(img).getSuperclass()
print type(img).getSuperclass().getSuperclass()
print type(img).getSuperclass().getSuperclass().getSuperclass()
# Prints:
# net.imglib2.img.imageplus.ImagePlusImg
# net.imglib2.img.planar.PlanarImg
# net.imglib2.img.AbstractNativeImg