from net.imglib2.converter import Converters
from net.imglib2.view import Views
from net.imglib2.algorithm.phasecorrelation import PhaseCorrelation2
from net.imglib2.img.array import ArrayImgFactory
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.type.numeric.complex import ComplexFloatType
from net.imglib2.util import Intervals
from java.util.concurrent import Executors
from java.lang import Runtime
from java.awt import Rectangle
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from ij import IJ

# Open Nile Bend sample image
imp = IJ.getImage()
#imp = IJ.openImage("https://imagej.nih.gov/ij/images/NileBend.jpg")
img = IL.wrapRGBA(imp)

# Extract red channel: alpha:0, red:1, green:2, blue:3
red = Converters.argbChannel(img, 1)

# Cut out two overlapping ROIs
r1 = Rectangle(1708, 680, 1792, 1760)
r2 = Rectangle( 520, 248, 1660, 1652)
cut1 = Views.zeroMin(Views.interval(red, [r1.x, r1.y],
                                         [r1.x + r1.width -1, r1.y + r1.height -1]))
cut2 = Views.zeroMin(Views.interval(red, [r2.x, r2.y],
                                         [r2.x + r2.width -1, r2.y + r2.height -1]))

# Thread pool
exe = Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors())

try:
  # PCM: phase correlation matrix
  pcm = PhaseCorrelation2.calculatePCM(cut1,
                                       cut2,
                                       ArrayImgFactory(FloatType()), FloatType(),
                                       ArrayImgFactory(ComplexFloatType()), ComplexFloatType(),
                                       exe)	

  # Number of phase correlation peaks to check with cross-correlation
  nHighestPeaks = 10

  # Minimum image overlap to consider, in pixels
  minOverlap = cut1.dimension(0) / 10

  # Returns an instance of PhaseCorrelationPeak2
  peak = PhaseCorrelation2.getShift(pcm, cut1, cut2, nHighestPeaks, minOverlap, True, True, exe)

  print "Translation:", peak.getSubpixelShift()
except Exception, e:
  print e
finally:
  exe.shutdown()

# Register images using the translation (the "shift")
shift = peak.getSubpixelShift()
dx = int(shift.getFloatPosition(0) + 0.5)
dy = int(shift.getFloatPosition(1) + 0.5)

# Top-left and bottom-right corners of the canvas that fits both registered images
x0 = min(0, dx)
y0 = min(0, dy)
x1 = max(cut1.dimension(0), cut2.dimension(0) + dx)
y1 = max(cut1.dimension(1), cut2.dimension(1) + dy)

canvas_width = x1 - x0
canvas_height = y1 - y0

def intoSlice(img, xOffset, yOffset):
  stack_slice = ArrayImgFactory(img.randomAccess().get().createVariable()).create([canvas_width, canvas_height])
  target = Views.interval(stack_slice, [xOffset, yOffset],
                                       [xOffset + img.dimension(0) -1, yOffset + img.dimension(1) -1])
  c1 = target.cursor()
  c2 = img.cursor()
  while c1.hasNext():
    c1.next().set(c2.next())

  return stack_slice

# Re-cut ROIs, this time in RGB rather than just red
img1 = Views.interval(img, [r1.x, r1.y],
                           [r1.x + r1.width -1, r1.y + r1.height -1])
img2 = Views.interval(img, [r2.x, r2.y],
                           [r2.x + r2.width -1, r2.y + r2.height -1])

# Insert each into a stack slice
xOffset1 = 0 if dx >= 0 else abs(dx)
yOffset1 = 0 if dy >= 0 else abs(dy)
xOffset2 = 0 if dx <= 0 else dx
yOffset2 = 0 if dy <= 0 else dy
slice1 = intoSlice(img1, xOffset1, yOffset1)
slice2 = intoSlice(img2, xOffset2, yOffset2)

stack = Views.stack([slice1, slice2])
IL.wrap(stack, "registered with phase correlation").show()
