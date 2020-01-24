package my;

import mpicbg.models.Point;
import java.lang.Math;
import java.util.List;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Set;
import java.lang.Integer;
import net.imglib2.RealLocalizable;
import net.imglib2.neighborsearch.RadiusNeighborSearchOnKDTree;
import com.google.common.collect.Sets;
import com.google.common.collect.ContiguousSet;
import com.google.common.collect.Range;
import com.google.common.collect.DiscreteDomain;


public final class ConstellationPlus
{
  private final double[] angles,
                         lengths; // as square-lengths
  public final Point position;
  static final public int COMPARE_ANGLES = 1,  // 01
              COMPARE_LENGTHS = 2, // 10
              COMPARE_ALL = 3;     // 11 

  public ConstellationPlus(
      final double[] angles,
      final double[] lengths,
      final double[] coords)
  {
    this.angles = angles;
    this.lengths = lengths;
    this.position = new Point(coords);
  }

  /** Expects the two ConstellationPlus instances to have the same number of angles and lengths, and in the same order; the comparison_type determines whether only angles, or only lengths, or both, are used: for scale-invariant comparisons use only angles. */
  public final boolean matches(
      final ConstellationPlus other,
      final double angle_epsilon,
      final double len_epsilon_sq,
      final int comparison_type)
  {
    // Check for different number of neighbors
    if (this.lengths.length != other.lengths.length) return false;
    // Compare angles
    if ((comparison_type & COMPARE_ANGLES) != 0) {
      for (int i=0; i<this.angles.length; ++i) {
        if (Math.abs(this.angles[i] - other.angles[i]) > angle_epsilon) return false;
      }
    }
    // Compare distances to other points: each should be under the permitted error
    if ((comparison_type & COMPARE_LENGTHS) != 0) {
      for (int i=0; i<this.lengths.length; ++i) {
        if (Math.abs(this.lengths[i] - other.lengths[i]) > len_epsilon_sq) return false;
      }
    }
    return true;
  }

  /** 
   * Copied from org.scijava.vecmath.Vector3f
   * Returns values from 0 to pi
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

  public static final List<ConstellationPlus> extractFeatures(
    final List<RealLocalizable> peaks,
    final RadiusNeighborSearchOnKDTree<RealLocalizable> search,
    final double radius,
    final int max_per_peak,
    final int min_neighbors, // should be at least 2
    final int max_neighbors) // should also be at least 2
  {
    final List<ConstellationPlus> constellations = new ArrayList<ConstellationPlus>();
    for (final RealLocalizable peak : peaks)
    {
      search.search(peak, radius, true);
      final int n = search.numNeighbors();
      int count = 0;
      final Set<Integer> naturals = ContiguousSet.create(Range.closedOpen(0, n), DiscreteDomain.integers());
      for (int n_neighbors=Math.max(2, min_neighbors); n_neighbors <= max_neighbors && n_neighbors < n; ++n_neighbors) {
        for (final Set<Integer> indices : Sets.combinations(naturals, n_neighbors)) {
          final RealLocalizable[] neighbors = new RealLocalizable[n_neighbors];
          final double[] sqLengths = new double[n_neighbors];
          int k = 0;
          // combinations of indices are always sorted, by design
          for (final Integer index: indices) {
            neighbors[k]   = search.getPosition(index);
            sqLengths[k++] = search.getSquareDistance(index);
          }
          constellations.add(ConstellationPlus.fromSearch(peak, neighbors, sqLengths));
          if (++count == max_per_peak) break;
        }
        if (count == max_per_peak) break;
      }
    }
    return constellations;
  }

  public static final ConstellationPlus fromSearch(
      final RealLocalizable center,
      final RealLocalizable[] ps, // sorted by proximity to center
      final double[] sqLengths)
  {
    final double xc = center.getFloatPosition(0),
                 yc = center.getFloatPosition(1),
                 zc = center.getFloatPosition(2);
		// Number of pairs: ps.length elements taken in groups of 2 without repeat
		int count = 1;
		switch (ps.length) {
			case 2: count = 2; break;
			case 3: count = 3; break;
			case 4: count = 6; break;
			case 5: count = 10; break;
			case 6: count = 15; break;
			default:
				int numerator = 2;
		    for (int i=ps.length; i>2; --i) numerator *= i;
				int denominator = 1;
				for (int i=ps.length -2; i>1; --i) denominator *= i;
				count = numerator / (denominator * 2);
		}

		// Angles among all possible pairs
		final double[] angles = new double[count];
    for (int i=0, a=0; i<ps.length; ++i) {
			final RealLocalizable p1 = ps[i];
			for (int k=i+1; k<ps.length; ++k) {
				final RealLocalizable p2 = ps[k];
				angles[a++] = computeAngle(
          p1.getFloatPosition(0) - xc,
          p1.getFloatPosition(1) - yc,
          p1.getFloatPosition(2) - zc,
          sqLengths[i],
          p2.getFloatPosition(0) - xc,
          p2.getFloatPosition(1) - yc,
          p2.getFloatPosition(2) - zc,
          sqLengths[k]);
			}
		}

		/*
    final double[] angles = new double[ps.length - 1];
    for (int i=0; i<angles.length; ++i) {
      final RealLocalizable p1 = ps[i],
                            p2 = ps[i+1];
      angles[i] = computeAngle(
          p1.getFloatPosition(0) - xc,
          p1.getFloatPosition(1) - yc,
          p1.getFloatPosition(2) - zc,
          sqLengths[i],
          p2.getFloatPosition(0) - xc,
          p2.getFloatPosition(1) - yc,
          p2.getFloatPosition(2) - zc,
          sqLengths[i+1]);
    }
		*/

    return new ConstellationPlus(
        angles,
        sqLengths,
        new double[]{xc, yc, zc});
  }
}
