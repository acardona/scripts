# Test whether the first nearest neighbor is the point itself
from net.imglib2 import RealPoint, KDTree
from net.imglib2.neighborsearch import RadiusNeighborSearchOnKDTree

points = [RealPoint.wrap([1.0, 1.0, float(i)]) for i in xrange(10)]

tree = KDTree(points, points)
search = RadiusNeighborSearchOnKDTree(tree)

radius = 3
search.search(RealPoint.wrap([1.0, 1.0, 1.0]), 3, False) # unordered

for i in xrange(search.numNeighbors()):
  print "Point " + str(i), search.getSampler(i).get()


# Prints:
# Point 0 (1.0,1.0,3.0)
# Point 1 (1.0,1.0,4.0)
# Point 2 (1.0,1.0,0.0)
# Point 3 (1.0,1.0,1.0)
# Point 4 (1.0,1.0,2.0)


# So yes: the first point is always the query point.