package my;

import mpicbg.models.Point;
import mpicbg.models.PointMatch;
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
