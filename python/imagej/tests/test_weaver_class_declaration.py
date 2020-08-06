from fiji.scripting import Weaver
from net.imglib2 import KDTree, RealPoint, RealRandomAccess, RealRandomAccessible
from net.imglib2.neighborsearch import NearestNeighborSearchOnKDTree
from net.imglib2.type.numeric.integer import UnsignedShortType

# Testing out a speed up: define the Spheres class in java
ws = Weaver.method("""
public final class Spheres extends RealPoint implements RealRandomAccess
{
	private final KDTree kdtree;
	private final NearestNeighborSearchOnKDTree search;
	private final double radius,
	                     radius_squared;
	private final UnsignedShortType inside,
	                                outside;

	public Spheres(final KDTree kdtree,
	               final double radius,
	               final UnsignedShortType inside,
	               final UnsignedShortType outside)
	{
		super(3);
		this.kdtree = kdtree;
		this.radius = radius;
		this.radius_squared = radius * radius;
		this.inside = inside;
		this.outside = outside;
		this.search = new NearestNeighborSearchOnKDTree(kdtree);
	}

	public final Spheres copyRealRandomAccess()
	{
		return new Spheres(this.kdtree, this.radius, this.inside, this.outside);
	}

	public final Spheres copy()
	{
		return copyRealRandomAccess();
	}

	public final UnsignedShortType get()
	{
		this.search.search(this);
		if (this.search.getSquareDistance() < this.radius_squared)
		{
			return inside;
		}
		return outside;
	}
}

public final Spheres createSpheres(final KDTree kdtree,
                                   final double radius,
	                               final UnsignedShortType inside,
	                               final UnsignedShortType outside)
{
	return new Spheres(kdtree, radius, inside, outside);
}

""", [RealPoint, RealRandomAccess, KDTree, NearestNeighborSearchOnKDTree, UnsignedShortType])

points = [RealPoint([i, i, i]) for i in xrange(10)]
kdtree = KDTree(points, points)



# Works:
ws = ws.createSpheres(kdtree, 2, UnsignedShortType(255), UnsignedShortType(0))

# Mysteriously fails with "expected 5 args, got 4". Has to do with calling the subclass constructor like a method.
#ws = ws.Spheres(kdtree, 2, UnsignedShortType(255), UnsignedShortType(0))
