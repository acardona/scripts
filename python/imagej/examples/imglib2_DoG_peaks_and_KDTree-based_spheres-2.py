from ij import IJ
from net.imglib2.view import Views
from net.imglib2.algorithm.dog import DogDetection
from net.imglib2 import KDTree, RealPoint, RealRandomAccess, RealRandomAccessible
from net.imglib2.neighborsearch import NearestNeighborSearchOnKDTree
from net.imglib2.img.display.imagej import ImageJFunctions as IL
from net.imglib2.type.numeric.integer import UnsignedByteType
from java.util import AbstractList

# The difference of Gaussian calculation, same as above (compressed)
# (or, paste this script under the script above where 'dog' is defined)
imp = IJ.openImage("https://imagej.nih.gov/ij/images/embryos.jpg")
IJ.run(imp, "8-bit", "")
img = IL.wrapReal(imp)
imgE = Views.extendMirrorSingle(img)
dog = DogDetection(imgE, img, [1.0, 1.0], 15.0, 30.0,
  DogDetection.ExtremaType.MAXIMA, 10, False)

# The spatial coordinates for the centers of all detected embryos
centers = dog.getSubpixelPeaks() # in floating-point precision

# A value for the inside of an embryo: white, in 8-bit
inside = UnsignedByteType(255)
  
# A value for the outside (the background): black, in 8-bit
outside = UnsignedByteType(0)

# The radius of a simulated embryo, same as sigmaLarger was above
radius = 30 # or = sigmaLarger

# KDTree: a data structure for fast spatial look up
kdtree = KDTree([inside] * len(centers), centers)

# The definition of circles (or spheres, or hyperspheres) in space
class Circles(RealPoint, RealRandomAccess):
  def __init__(self, n_dimensions, kdtree, radius, inside, outside):
    super(RealPoint, self).__init__(n_dimensions)
    self.search = NearestNeighborSearchOnKDTree(kdtree)
    self.radius = radius
    self.radius_squared = radius * radius
    self.inside = inside
    self.outside = outside
  def copyRealRandomAccess(self):
    return Circles(self.numDimensions(), self.kdtree, self.radius, self.inside, self.outside)
  def get(self):
    self.search.search(self)
    if self.search.getSquareDistance() < self.radius_squared:
      return self.inside
    return self.outside

# The RealRandomAccessible that wraps the Circles in 2D space, unbounded
# NOTE: partial implementation, unneeded methods were left unimplemented
class CircleData(RealRandomAccessible):                           
  def realRandomAccess(self):                                           
    return Circles(2, kdtree, radius, inside, outside)               
  def numDimensions(self):                                              
    return 2
                                                    
# An unbounded view of the Circles that can be iterated in a grid, with integers
raster = Views.raster(CircleData())

# A bounded view of the raster, within the bounds of the original 'img'
# I.e. 'img' here is used as the Interval within which the CircleData is defined
circles = Views.interval(raster, img)                                 
                                                                        
IL.wrap(circles, "Circles").show()