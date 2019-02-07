from net.imglib2.view import Views
from net.imglib2 import RealPoint, RealRandomAccess, KDTree, RealRandomAccessible
from net.imglib2.neighborsearch import NearestNeighborSearchOnKDTree
from net.imglib2.type.numeric.integer import UnsignedByteType
from synthetic_asm import makeNativeRadiusBounds

RadiusBounds = makeNativeRadiusBounds()

#class RadiusBounds(RealPoint, RealRandomAccess):
#  """ The definition of a point with a diameter in space. """
#  def __init__(self, n_dimensions, kdtree, radius, inside, outside):
#    super(RealPoint, self).__init__(n_dimensions)
#    self.search = NearestNeighborSearchOnKDTree(kdtree)
#    self.radius = radius
#    self.radius_squared = radius * radius
#    self.inside = inside
#    self.outside = outside
#  def copyRealRandomAccess(self):
#    return RadiusBounds(self.numDimensions(), self.kdtree, self.radius, self.inside, self.outside)
#  def get(self):
#    self.search.search(self)
#    if self.search.getSquareDistance() < self.radius_squared:
#      return self.inside
#    return self.outside

class RadiusBoundsRealRandomAccessible(RealRandomAccessible):
  """ The RealRandomAccessible that wraps the RadiusBounds in space, unbounded.
      NOTE: partial implementation, unneeded methods were left unimplemented.
  """
  def __init__(self, n_dimensions, kdtree, radius, inside, outside):
    self.n_dimensions = n_dimensions
    self.kdtree = kdtree
    self.radius = radius
    self.inside = inside
    self.outside = outside
  def realRandomAccess(self):
    return RadiusBounds(self.n_dimensions, self.kdtree, self.radius, self.inside, self.outside)
  def numDimensions(self):
    return self.n_dimensions


def virtualPointsRAI(points, radius, interval,
                     inside=UnsignedByteType(255),
                     outside=UnsignedByteType(0)):
  """
  points: a list of RealPoint instances, such as obtained from a difference of Gaussian getSubpixelPeaks().
  radius: how "fat" to draw each point.
  interval: the interval within which to define the returned RandomAccessibleInterval.
  inside: defaults to UnsignedByteType(255), meaning "white".
  outside: defaults to UnsignedByteType(0), meaning "black".
  
  Returns a RandomAccessibleInterval showing each point within the interval painted within radius,
  with its data created dynamically from a KDTree on the points and a NearestNeighborSearchOnKDTree,
  using the inside and outside values.
  """
  kdtree = KDTree([inside] * len(points), points)
  
  # An unbounded view of the RadiusBounds that can be iterated in a grid, with integers
  raster = Views.raster(RadiusBoundsRealRandomAccessible(points[0].numDimensions(),
                                                         kdtree, radius, inside, outside))

  return Views.interval(raster, interval)
