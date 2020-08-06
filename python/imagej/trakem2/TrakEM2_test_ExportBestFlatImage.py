from ini.trakem2.display import Display
from mpicbg.trakem2.transform import ExportBestFlatImage
from ij import ImagePlus

patches = Display.getFront().getLayer().getDisplayables()
bounds = Display.getFront().getRoi().getBounds()
backgroundValue = 0
scale = 0.25

e = ExportBestFlatImage(patches, bounds, backgroundValue, scale)
print e.canUseAWTImage()
print e.isSmallerThan2GB()
e.printInfo()

p = e.makeFlatFloatGrayImageAndAlpha()
ImagePlus("grey", p.a).show()
ImagePlus("mask", p.b).show()