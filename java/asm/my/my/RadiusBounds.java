package my;

import net.imglib2.RealPoint;
import net.imglib2.RealRandomAccess;
import net.imglib2.KDTree;
import net.imglib2.neighborsearch.NearestNeighborSearchOnKDTree;
import net.imglib2.type.numeric.RealType;

public final class RadiusBounds< T extends RealType< T > > extends RealPoint implements RealRandomAccess< T >
{
	final private NearestNeighborSearchOnKDTree<T> search;
	final private KDTree<T> kdtree;
	final private double radius, radius_squared;
	final private T inside, outside;

	public RadiusBounds(
			final int n_dimensions,
			final KDTree<T> kdtree,
			final double radius,
			final T inside,
			final T outside)
	{
		super(n_dimensions);
		this.kdtree = kdtree;
		this.radius = radius;
		this.radius_squared = radius * radius;
		this.inside = inside;
		this.outside = outside;
		this.search = new NearestNeighborSearchOnKDTree<T>(kdtree);
	}

	@Override
	public T get() {
		this.search.search(this);
	    if (this.search.getSquareDistance() < this.radius_squared) {
	      return this.inside;
	    }
	    return this.outside;
	}

	@Override
	public RealRandomAccess<T> copy() {
		return copyRealRandomAccess();
	}

	@Override
	public RealRandomAccess<T> copyRealRandomAccess() {
		return new RadiusBounds<T>(this.numDimensions(), kdtree, radius, inside, outside);
	}     
}
