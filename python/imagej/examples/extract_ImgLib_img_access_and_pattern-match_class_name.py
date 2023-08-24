from ij import IJ
from net.imglib2.img.array import ArrayImgs
import re

imp = IJ.getImage()
pixels = imp.getProcessor().getPixels()
img = ArrayImgs.bytes(pixels, [imp.getWidth(), imp.getHeight()])
access = img.update(None)
t = type(access).getSimpleName()

pattern = re.compile("(Byte|Short|Float|Long)")

m = re.match(pattern, t)
print m.group(1)