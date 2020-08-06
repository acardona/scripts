from net.imglib2.roi import Masks, Regions
from net.imglib2.roi.geom import GeomMasks
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.view import Views
from net.imglib2.util import Intervals
from ij import IJ
from itertools import imap

# Open the embryos sample image, and turn it into 16-bit grayscale
imp = IJ.getImage()
IJ.run(imp, "16-bit", "")
IJ.run(imp, "Specify...", "width=61 height=61 x=1037 y=83 oval")
circle = imp.getRoi()
bounds = circle.getBounds()
center = bounds.x + bounds.width / 2.0, bounds.y + bounds.height / 2.0
print center

img = IL.wrap(imp)
sphere = GeomMasks.closedSphere(center, 61 / 2.0)
inside = Regions.iterable(
           Views.interval(
             Views.raster(Masks.toRealRandomAccessible(sphere)),
             Intervals.largestContainedInterval(sphere)))

pixels = []
ra = img.randomAccess()
cursor = inside.cursor() # only True pixels of the sphere mask

while cursor.hasNext():
  cursor.fwd()
  ra.setPosition(cursor)
  pixels.append(ra.get().get())

print "Average:", sum(pixels) / float(len(pixels))

# prints: 68.91
# whereas ImageJ "measure" prints: 69.285 for the EllipseRoi

# Try with Region.sample
cursor = Regions.sample(inside, img).cursor()
pixels = []
while cursor.hasNext():
  pixels.append(cursor.next().get())

print "Average:", sum(pixels) / float(len(pixels))

iterableinterval = Regions.sample(inside, img)
print len(pixels), Intervals.numElements(iterableinterval) # too many, of course: both True and False entries
print sum(imap(lambda t: t.get(), iterableinterval)) / float(Regions.countTrue(inside))
from operator import methodcaller
print sum(imap(methodcaller("get"), iterableinterval)) / float(Regions.countTrue(inside))