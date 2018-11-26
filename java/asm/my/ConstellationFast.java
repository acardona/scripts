package my;

import mpicbg.models.Point;
import java.lang.Math;
import java.util.List;
import java.util.ArrayList;
import net.imglib2.RealLocalizable;
import net.imglib2.neighborsearch.RadiusNeighborSearchOnKDTree;

public final class ConstellationFast
{
  private final double angle,
                       len1,
                       len2;
  public final Point position; // ACC_PUBLIC for trivial access

  public ConstellationFast(
      final double angle, 
      final double len1, 
      final double len2,
      final double[] coords)
  {
    this.angle = angle;
    this.len1 = len1;
    this.len2 = len2;
    this.position = new Point(coords);
  }

  public final boolean matches(
      final ConstellationFast other,
      final double angle_epsilon,
      final double len_epsilon_sq)
  {
    return Math.abs(this.angle - other.angle) < angle_epsilon
      && Math.abs(this.len1 - other.len1) + Math.abs(this.len2 - other.len2) < len_epsilon_sq;
  }

  /*j
  public static final double[] subtract(
      final RealLocalizable loc1
      final RealLocalizable loc2)
  {
    return new double[]{loc1.getFloatPosition(0) - loc2.getFloatPosition(0),
                        loc1.getFloatPosition(1) - loc2.getFloatPosition(1),
                        loc1.getFloatPosition(2) - loc2.getFloatPosition(2)};
  }
  */

	/** 
	 * Copied from org.scijava.vecmath.Vector3f
	 */
	private static final double computeAngle(
			final double x1, final double y1, final double z1, final double sqlen1,
			final double x2, final double y2, final double z2, final double sqlen2)
	{
		final double len1 = Math.sqrt(sqlen1), // Same: x1*x1 + y1*y1 + z1*z1), // TODO does it need sqrt? Tes, or, use a different algorithm that enables using squared lengths
		             len2 = Math.sqrt(sqlen2), // Same: x2*x2 + y2*y2 + z2*z2),
								 dot = x1*x2 + y1*y2 + z1*z2,
								 vDot = dot / (len1 * len2);
		//if ( vDot >  1.0 ) return Math.acos(  1.0 );
		//if ( vDot < -1.0 ) return Math.acos( -1.0 );
		//return Math.acos( vDot );
		return Math.acos( vDot > 1.0 ? 1.0 : ( vDot < -1.0 ? -1.0 : vDot ) );
	}

  public static final ConstellationFast fromSearch(
      final RealLocalizable center,
      final RealLocalizable p1,
      final double d1,
      final RealLocalizable p2,
      final double d2)
  {
    final double xc = center.getFloatPosition(0),
                 yc = center.getFloatPosition(1),
                 zc = center.getFloatPosition(2);
    return new ConstellationFast(
				computeAngle(
					p1.getFloatPosition(0) - xc,
          p1.getFloatPosition(1) - yc,
          p1.getFloatPosition(2) - zc,
					d1,
          p2.getFloatPosition(0) - xc,
          p2.getFloatPosition(1) - yc,
          p2.getFloatPosition(2) - zc,
					d2),
        d1,
        d2,
        new double[]{xc, yc, zc});
  }

	public static final ConstellationFast fromRow(
			final List<Double> row)
	{
		// Expects: row = [angle, len1, len2, x, y, z]
		return new ConstellationFast(row.get(0), row.get(1), row.get(2),
				new double[]{row.get(3), row.get(4), row.get(5)});
	}

	public final double[] asRow()
	{
		// Returns: [angle, len1, len2, position.x, position,y, position.z]
		final double[] w = this.position.getW();
		return new double[]{this.angle, this.len1, this.len2, w[0], w[1], w[2]};
	}

	public static final String[] csvHeader()
	{
		return new String[]{"angle", "len1", "len2", "x", "y", "z"};
	}

	public static final List<ConstellationFast> extractFeatures(
		final List<RealLocalizable> peaks,
		final RadiusNeighborSearchOnKDTree<RealLocalizable> search,
		final double radius,
		final double min_angle,
		final double max_per_peak)
	{
		final List<ConstellationFast> constellations = new ArrayList<ConstellationFast>();
		for (final RealLocalizable peak : peaks)
		{
			search.search(peak, radius, true);
			final int n = search.numNeighbors();
			if (n > 2) {
				int yielded = 0;
				// 0 is itself: skip from range of indices
				for ( int i=n-2, j=n-1; i > 0; --i, --j)
				{
					if ( max_per_peak == yielded ) break;
					final ConstellationFast cons = ConstellationFast.fromSearch(
							peak,
							search.getPosition(i),
							search.getSquareDistance(i),
							search.getPosition(j),
							search.getSquareDistance(j));
					if (cons.angle >= min_angle) {
						++yielded;
						constellations.add(cons);
					}
				}
			}
		}
		return constellations;
	}
}
