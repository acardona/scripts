from net.imglib2.algorithm.math.ImgMath import compute, block, div, offset, add
from net.imglib2.algorithm.math.abstractions import Util
from net.imglib2.algorithm.integral import IntegralImg
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.type.numeric.integer import UnsignedByteType, \
                          UnsignedShortType, UnsignedLongType
from net.imglib2.view import Views
from ij import IJ

imp = IJ.getImage() # e.g. EM of Drosophila neurons 180-220-sub512x512-30.tif
#imp = IJ.openImage("/home/albert/lab/TEM/abd/microvolumes/Seg/180-220-sub/180-220-sub512x512-30.tif")
img = compute(IL.wrap(imp)).intoImg(UnsignedShortType()) # in 16-bit

# Create an integral image in longs
alg = IntegralImg(img, UnsignedLongType(), Util.genericIntegerTypeConverter())
alg.process()
integralImg = alg.getResult()

# Create an image pyramid as views, with ImgMath and imglib2,
# which amounts to scale area averaging sped up by the integral image
# and generated on demand whenever each pyramid level is read.
width = img.dimension(0)
min_width = 32
imgE = Views.extendBorder(integralImg)
blockSide = 1
# Corners for level 1: a box of 2x2
corners = [[0, 0], [1, 0], [0, 1], [1, 1]]
pyramid = [] # level 0 is the image itself, not added

while width > min_width:
  blockSide *= 2
  width /= 2
  # Scale the corner coordinates to make the block larger
  cs = [[c * blockSide for c in corner] for corner in corners]
  blockRead = div(block(imgE, cs), pow(blockSide, 2)) # the op
  # a RandomAccessibleInterval view of the op, computed with shorts but seen as bytes
  view = blockRead.view(UnsignedShortType(), UnsignedByteType())
  # Views.subsample by 2 will turn a 512-pixel width to a 257 width,
  # so crop to proper interval 256
  level = Views.interval(Views.subsample(view, blockSide),
                         [0] * img.numDimensions(), # min
                         [img.dimension(d) / blockSide -1
                          for d in xrange(img.numDimensions())]) # max
  pyramid.append(level)


"""
for i, level in enumerate(pyramid):
  imp_level = IL.wrap(level, str(i+1))
  imp_level.show()
  win = imp.getWindow().getCanvas().
"""


from java.lang import Runnable
from javax.swing import SwingUtilities

# Show and position the original window and each level of the pyramid in a 3x2 grid
offsetX, offsetY = 100, 100 # from top left of the screen, in pixels
gridWidth = 3
imp.getWindow().setLocation(offsetX, offsetY) # from top left

# Show each pyramid level
imps = [imp] + [IL.wrap(level, str(i+1)) for i, level in enumerate(pyramid)]

class Show(Runnable):
  def __init__(self, i, imp):
    self.i = i # index in the 3x2 grid, from 0 to 5
    self.imp = imp
  def run(self):
    self.imp.show()
    win = self.imp.getWindow()
    # zoom in so that the window has the same dimensions as the original image
    scale = int(pow(2, self.i))
    win.getCanvas().setMagnification(scale)
    win.getCanvas().setSize(self.imp.getWidth() * scale, self.imp.getHeight() * scale)
    win.pack()
    win.toFront()
    win.setLocation(offsetX + (self.i % gridWidth) * win.getWidth(),
                    offsetY + (self.i / gridWidth) * win.getHeight())

for i, imp in enumerate(imps):
  SwingUtilities.invokeLater(Show(i, imp))
