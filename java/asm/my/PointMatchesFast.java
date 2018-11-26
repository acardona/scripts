package my;

import mpicbg.models.Point;
import mpicbg.models.PointMatch;
import my.ConstellationFast;
import net.imglib2.RealPoint;
import net.imglib2.KDTree;
import net.imglib2.neighborsearch.RadiusNeighborSearchOnKDTree;
import java.util.List;
import java.util.ArrayList;
import java.util.Iterator;

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
		final double[][] rows = new double[this.pointmatches.size()][6];
		for (int i=0; i<pointmatches.size(); ++i) {
			final PointMatch pm = pointmatches.get(i);
			final double[] p1 = pm.getP1().getW(),
						         p2 = pm.getP2().getW();
			rows[i][0] = p1[0];
			rows[i][1] = p1[1];
			rows[i][2] = p1[2];
			rows[i][3] = p2[0];
			rows[i][4] = p2[1];
			rows[i][5] = p2[2];
		}
		return rows;
	}

	static public final PointMatchesFast fromRows(final Iterator<List<String>> rows)
	{
		final List<PointMatch> pointmatches = new ArrayList<PointMatch>();
		while (rows.hasNext()) {
		  final List<String> row = rows.next();
			pointmatches.add(new PointMatch(
						new Point(new double[]{Double.parseDouble(row.get(0)),
						                       Double.parseDouble(row.get(1)),
												 					 Double.parseDouble(row.get(2))}),
					  new Point(new double[]{Double.parseDouble(row.get(3)),
                                   Double.parseDouble(row.get(4)),
                                   Double.parseDouble(row.get(5))})));
		}
		return new PointMatchesFast(pointmatches);
	}

	static public final String[] csvHeader()
	{
		return new String[]{"x1", "y1", "z1", "x2", "y2", "z2"};
	}

	static public final double[] asRow(final PointMatch pm)
	{
		final double[] row = new double[6],
									 p1 = pm.getP1().getW(),
									 p2 = pm.getP2().getW();
		row[0] = p1[0];
		row[1] = p1[1];
		row[2] = p1[2];
		row[3] = p2[0];
		row[4] = p2[1];
		row[5] = p2[2];
		return row;
	}
}
