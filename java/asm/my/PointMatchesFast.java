package my;

import mpicbg.models.Point;
import mpicbg.models.PointMatch;
import mpicbg.models.AbstractModel;
import mpicbg.imagefeatures.Feature;
import mpicbg.imagefeatures.FloatArray2DSIFT;
import my.ConstellationFast;
import my.ParsePointMatchFunction;
import net.imglib2.RealPoint;
import net.imglib2.KDTree;
import net.imglib2.neighborsearch.RadiusNeighborSearchOnKDTree;
import java.util.List;
import java.util.ArrayList;
import java.util.Iterator;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.stream.Collectors;
import java.io.IOException;

public final class PointMatchesFast
{
	public final List<PointMatch> pointmatches;

	public PointMatchesFast(final List<PointMatch> pointmatches)
	{
		this.pointmatches = pointmatches;
	}

	static public final PointMatchesFast fromFeatures(
			final List<ConstellationFast> features1,
			final List<ConstellationFast> features2,
			final double angle_epsilon,
			final double len_epsilon_sq)
	{
		final List<PointMatch> pointmatches = new ArrayList<PointMatch>();
		for (final ConstellationFast c1: features1) {
			for (final ConstellationFast c2: features2) {
				if (c1.matches(c2, angle_epsilon, len_epsilon_sq)) {
					pointmatches.add(new PointMatch(c1.position, c2.position));
				}
			}
		}
		return new PointMatchesFast(pointmatches);
	}

	static public final PointMatchesFast fromFeaturesScaleInvariant(
			final List<ConstellationFast> features1,
			final List<ConstellationFast> features2,
			final double angle_epsilon,
			final double len_epsilon)
	{
		final List<PointMatch> pointmatches = new ArrayList<PointMatch>();
		for (final ConstellationFast c1: features1) {
			for (final ConstellationFast c2: features2) {
				if (c1.matchesScaleInvariant(c2, angle_epsilon, len_epsilon)) {
					pointmatches.add(new PointMatch(c1.position, c2.position));
				}
			}
		}
		return new PointMatchesFast(pointmatches);
	}

	static public final PointMatchesFast fromNearbyFeatures(
			final double radius,
			final List<ConstellationFast> features1,
			final List<ConstellationFast> features2,
			final double angle_epsilon,
			final double len_epsilon_sq)
	{
		final List<RealPoint> positions2 = new ArrayList<RealPoint>();
		for (final ConstellationFast c2 : features2) {
			positions2.add(RealPoint.wrap(c2.position.getW()));
		}
		final RadiusNeighborSearchOnKDTree<ConstellationFast> search2 =
			new RadiusNeighborSearchOnKDTree<ConstellationFast>(new KDTree<ConstellationFast>(features2, positions2));
		final List<PointMatch> pointmatches = new ArrayList<PointMatch>();
		for (final ConstellationFast c1 : features1) {
			search2.search(RealPoint.wrap(c1.position.getW()), radius, false); // unsorted
			for (int i=0, n=search2.numNeighbors(); i<n; ++i) {
				final ConstellationFast c2 = search2.getSampler(i).get();
				if (c1.matches(c2, angle_epsilon, len_epsilon_sq)) {
					pointmatches.add(new PointMatch(c1.position, c2.position));
				}
			}
		}
		return new PointMatchesFast(pointmatches);
	}

	/**
	 * Use a KDTree for nearest neighbor search, to avoid all-to-all matching
	 * when using SIFT features.
	 * Note the need for removing ambiguous matches, which, while it is done
	 * for every call to FloatArray2DSIFT.createMatches, it has to be done again
	 * for all features since we don't know which ones overlap. It's a fast inexpensive match,
	 * albeit one that is N*N. Could also be done with a KDTRee but there's no need,
	 * there are less matching features than the input features, and the comparison
	 * is extremely cheap.
	 *
	 * The issue here is that FloatArray2DSIFT.createMatches still has a "TODO implement the spatial constraints" and therefore does not make use of the model or the max_id.
	 */
	static public final List<PointMatch> matchNearbyFeatures(
			final double radius,
			final List<Feature> features1,
			final List<Feature> features2,
			final double max_sd, // maximal difference in size (ratio max/min)
			final AbstractModel< ? > model, // NOT USED
			final double max_id, // NOT USED, would be the same as radius
			final float rod) // ratio of distances (closest/next closest match)
	{
		final List<PointMatch> matches = new ArrayList<PointMatch>();
		if (0 == features1.size() || 0 == features2.size()) return matches;
		final List<RealPoint> positions2 = new ArrayList<RealPoint>();
		for (final Feature f2 : features2) {
			positions2.add(RealPoint.wrap(f2.location));
		}
		final RadiusNeighborSearchOnKDTree<Feature> search2 =
			new RadiusNeighborSearchOnKDTree<Feature>(new KDTree<Feature>(features2, positions2));
		final List<Feature> single1 = new ArrayList<Feature>(1);
		single1.add(features1.get(0)); // to make the list be of size 1
		final List<Feature> neighbors2 = new ArrayList<Feature>(Math.max(1, features2.size() / 10));
		for (final Feature f1 : features1) {
			single1.set(0, f1); // replace the one and only element
			search2.search(RealPoint.wrap(f1.location), radius, false); // unsorted
			for (int i=0, n=search2.numNeighbors(); i<n; ++i) {
				neighbors2.add(search2.getSampler(i).get());
			}
			matches.addAll(FloatArray2DSIFT.createMatches(single1, neighbors2, max_sd, model, max_id, rod));
			neighbors2.clear();
		}
		// now remove ambiguous matches: where one feature from 1 matched more than one feature from 2
		// Copied and modified from: mpicbg.imagefeatures.FloatArray2DSIFT.createMatches
		for ( int i = 0; i < matches.size(); )
		{
			boolean amb = false;
			final PointMatch m = matches.get( i );
			final double[] m_p2 = m.getP2().getL();
			for ( int j = i + 1; j < matches.size(); )
			{
				final PointMatch n = matches.get( j );
				final double[] n_p2 = n.getP2().getL();
				if ( m_p2[ 0 ] == n_p2[ 0 ] && m_p2[ 1 ] == n_p2[ 1 ] )
				{
					amb = true;
					matches.remove( j ); // removeElementAt is specific of Vector
				}
				else ++j;
			}
			if ( amb )
			{
				matches.remove( i ); // removeElementAt is specific of Vector
			}
			else ++i;
		}
		return matches;
	}

	public final double[][] toRows()
	{
		final int n = this.pointmatches.get(0).getP1().getW().length;
		final double[][] rows = new double[this.pointmatches.size()][n + n];
		for (int i=0; i<pointmatches.size(); ++i) {
			final PointMatch pm = pointmatches.get(i);
			final double[] p1 = pm.getP1().getW(),
						         p2 = pm.getP2().getW();
			for (int j=0; j<n; ++j) rows[i][j] = p1[j];
			for (int j=0; j<n; ++j) rows[i][n+j] = p2[j];
		}
		return rows;
	}

	static public final PointMatchesFast fromRows(final Iterator<List<String>> rows)
	{
		final List<PointMatch> pointmatches = new ArrayList<PointMatch>();
		while (rows.hasNext()) {
		  final List<String> row = rows.next();
			final int n = row.size() / 2;
			final double[] d1 = new double[n],
			               d2 = new double[n];
			for (int i=0; i<n; ++i) d1[i] = Double.parseDouble(row.get(i));
			for (int i=0; i<n; ++i) d2[i] = Double.parseDouble(row.get(n+i));
			pointmatches.add(new PointMatch(new Point(d1), new Point(d2)));
		}
		return new PointMatchesFast(pointmatches);
	}

	static public final PointMatchesFast fromPath(final String path) throws IOException
	{
		final List<PointMatch> pointmatches = Files.lines(Paths.get(path))
			.skip(3) // The header
			.map(new ParsePointMatchFunction())
			.collect(Collectors.toList());
		return new PointMatchesFast(pointmatches);
	}

	static public final String[] csvHeader(final PointMatch pm)
	{
		return 3 == pm.getP1().getW().length ?
			  new String[]{"x1", "y1", "z1", "x2", "y2", "z2"}
			: new String[]{"x1", "y1", "x2", "y2"};
	}

	static public final double[] asRow(final PointMatch pm)
	{
		final double[] p1 = pm.getP1().getW(),
									 p2 = pm.getP2().getW(),
                   row = new double[p1.length + p2.length];
		for (int i=0; i<p1.length; ++i) row[i] = p1[i];
		for (int i=0; i<p2.length; ++i) row[p1.length + i] = p2[i];
		return row;
	}
}
