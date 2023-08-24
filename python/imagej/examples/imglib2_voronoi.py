from net.imglib2.view import Views
from net.imglib2 import RealPoint, RealRandomAccess, KDTree, RealRandomAccessible, FinalInterval
from net.imglib2.neighborsearch import RadiusNeighborSearchOnKDTree
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.util import ImgUtil
from net.imglib2.img.array import ArrayImgs
from net.imglib2.img.display.imagej import ImageJFunctions as IL


class RadiusBounds(RealPoint, RealRandomAccess):
  """ Each point checks whether it's within the radius of the nearest point. """
  def __init__(self, n_dimensions, kdtree, max_search_radius, inside, outside):
    super(RealPoint, self).__init__(n_dimensions)
    self.search = RadiusNeighborSearchOnKDTree(kdtree)
    self.max_search_radius = max_search_radius
    self.inside = inside
    self.outside = outside
  def copyRealRandomAccess(self):
    return RadiusBounds(self.numDimensions(), self.kdtree, self.max_search_radius, self.inside, self.outside)
  def get(self):
    # Returns neighbors sorted from nearest to furthest
    self.search.search(self, self.max_search_radius, True)
    seen = set()
    # Find a point whose radius is smaller than the distance to it
    # and which is of a type that hasn't been seen yet
    for i in xrange(self.search.numNeighbors()):
      radius, tagID = self.search.getSampler(i).get()
      if tagID in seen:
        continue
      seen.add(tagID)
      distance = self.search.getDistance(i)
      if distance < radius:
        return self.inside
    return self.outside

class RadiusBoundsRealRandomAccessible(RealRandomAccessible):
  """ The RealRandomAccessible that wraps the RadiusBounds in space, unbounded.
      NOTE: partial implementation, unneeded methods were left unimplemented.
  """
  def __init__(self, n_dimensions, kdtree, max_search_radius, inside, outside):
    self.n_dimensions = n_dimensions
    self.kdtree = kdtree
    self.max_search_radius = max_search_radius
    self.inside = inside
    self.outside = outside
  def realRandomAccess(self):
      return RadiusBounds(self.n_dimensions, self.kdtree, self.max_search_radius, self.inside, self.outside)
  def numDimensions(self):
    return self.n_dimensions



inside  = UnsignedByteType(255) # white
outside = UnsignedByteType(0)   # black

width = 128
height = 128
x0 = 0
y0 = 40
x1 = 512
y1 = 80
dx = x1 - x0
dy = y1 - y0
steps = max(dx, dy)

# TODO: write a class Line that grows, avoiding other existing lines
# by changing its direction vector just enough, using swarm rules.

line = [[x0 + dx * i/float(steps),
         y0 + dy * i/float(steps)] for i in xrange(steps)]
tagID = 1

#for x,y in line:
#  print x,y

kdtree = KDTree([(10.0, tagID)] * len(line), [RealPoint.wrap(p) for p in line])
max_search_radius = 30

rac = RadiusBoundsRealRandomAccessible(2, kdtree, max_search_radius, inside, outside)
view = Views.interval(Views.raster(rac), FinalInterval([width, height]))
img = ArrayImgs.unsignedBytes(width, height)
ImgUtil.copy(view, img)

IL.wrap(img, "voronoi").show()





         