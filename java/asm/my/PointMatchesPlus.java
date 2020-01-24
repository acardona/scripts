package my;

import mpicbg.models.Point;
import mpicbg.models.PointMatch;
import my.ConstellationPlus;
import net.imglib2.RealPoint;
import net.imglib2.KDTree;
import net.imglib2.neighborsearch.RadiusNeighborSearchOnKDTree;
import java.util.List;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Callable;
import java.util.concurrent.Future;

public final class PointMatchesPlus
{
  public final List<PointMatch> pointmatches;

  public PointMatchesPlus(final List<PointMatch> pointmatches)
  {
    this.pointmatches = pointmatches;
  }

  static public final PointMatchesPlus fromFeatures(
      final List<ConstellationPlus> features1,
      final List<ConstellationPlus> features2,
      final double angle_epsilon,
      final double len_epsilon_sq)
    throws Exception
  {
    return fromFeatures(features1, features2, angle_epsilon, len_epsilon_sq,
        ConstellationPlus.COMPARE_ALL, 1);
  }

  static public final PointMatchesPlus fromFeaturesScaleInvariant(
      final List<ConstellationPlus> features1,
      final List<ConstellationPlus> features2,
      final double angle_epsilon,
      final double len_epsilon_sq)
    throws Exception
  {
    return fromFeatures(features1, features2, angle_epsilon, len_epsilon_sq,
        ConstellationPlus.COMPARE_ANGLES, 1);
  }

  // All to all
  static public final PointMatchesPlus fromFeatures(
      final List<ConstellationPlus> features1,
      final List<ConstellationPlus> features2,
      final double angle_epsilon,
      final double len_epsilon_sq,
      final int comparison_type,
      final int n_threads)
    throws Exception
  {
    final ArrayList<PointMatch> pointmatches = new ArrayList<PointMatch>();
    final int inc = features1.size() / n_threads;
    final ExecutorService exe = Executors.newFixedThreadPool(n_threads);
    try {
      final ArrayList<Future<ArrayList<PointMatch>>> futures = new ArrayList<>(n_threads);
      for (int i=0; i<=n_threads; ++i) { // <= to ensure last chunk is done
        final int offset = i * inc;
        if (offset >= features1.size()) break;
        futures.add(exe.submit(new Callable<ArrayList<PointMatch>>() {
          public final ArrayList<PointMatch> call() {
            final ArrayList<PointMatch> pointmatches = new ArrayList<PointMatch>();
            for (final ConstellationPlus c1: features1.subList(offset, Math.min(offset + inc, features1.size()))) {
              for (final ConstellationPlus c2: features2) {
                if (c1.matches(c2, angle_epsilon, len_epsilon_sq, comparison_type)) {
                  pointmatches.add(new PointMatch(c1.position, c2.position));
                }
              }
            }
            return pointmatches;
          }
        }));
      }
      uniquePointMatches(futures, pointmatches);
    } finally {
      exe.shutdown();
    }

    return new PointMatchesPlus(pointmatches);
  }

  static private final void uniquePointMatches(
      final List<Future<ArrayList<PointMatch>>> futures,
      final List<PointMatch> pointmatches)
    throws Exception
  {
    // Add unique PointMatch, avoiding repeats
    // (Comparisons are done by pointer to instance, not content)
    final HashMap<Point, HashSet<Point>> seen = new HashMap<>();
    for (final Future<ArrayList<PointMatch>> f: futures) {
      for (final PointMatch pm: f.get()) {
        HashSet<Point> p2s = seen.get(pm.getP1());
        if (null == p2s) {
          // First time p1 is used in a PointMatch
          p2s = new HashSet<Point>();
          p2s.add(pm.getP2());
          seen.put(pm.getP1(), p2s);
        } else if (p2s.contains(pm.getP2())) {
          // skip: p1, p2 combination seen already
          continue;
        } else {
          // Seeing p1, p2 combination for the first time
          p2s.add(pm.getP2());
        }
        pointmatches.add(pm);
      }
    }
  }

  static public final PointMatchesPlus fromNearbyFeatures(
      final double radius,
      final List<ConstellationPlus> features1,
      final List<ConstellationPlus> features2,
      final double angle_epsilon,
      final double len_epsilon_sq)
    throws Exception
  {
    return fromNearbyFeatures(radius, features1, features2, angle_epsilon, len_epsilon_sq, ConstellationPlus.COMPARE_ALL, 1);
  }

  static public final PointMatchesPlus fromNearbyFeatures(
      final double radius,
      final List<ConstellationPlus> features1,
      final List<ConstellationPlus> features2,
      final double angle_epsilon,
      final double len_epsilon_sq,
      final int comparison_type,
      final int n_threads)
    throws Exception
  {
    final List<RealPoint> positions2 = new ArrayList<RealPoint>();
    for (final ConstellationPlus c2 : features2) {
      positions2.add(RealPoint.wrap(c2.position.getW()));
    }
    final KDTree<ConstellationPlus> kdtree2 = new KDTree<ConstellationPlus>(features2, positions2);
    final List<PointMatch> pointmatches = new ArrayList<PointMatch>();

    final int inc = features1.size() / n_threads;
    final ExecutorService exe = Executors.newFixedThreadPool(n_threads);
    try {
      final ArrayList<Future<ArrayList<PointMatch>>> futures = new ArrayList<>(n_threads);
      for (int i=0; i<=n_threads; ++i) { // <= to ensure last chunk is done
        final int offset = i * inc;
        if (offset >= features1.size()) break;
        futures.add(exe.submit(new Callable<ArrayList<PointMatch>>() {
          public final ArrayList<PointMatch> call() {
            final ArrayList<PointMatch> pointmatches = new ArrayList<PointMatch>();
            final RadiusNeighborSearchOnKDTree<ConstellationPlus> search2 =
              new RadiusNeighborSearchOnKDTree<ConstellationPlus>(kdtree2);
            for (final ConstellationPlus c1: features1.subList(offset, Math.min(offset + inc, features1.size()))) {
              search2.search(RealPoint.wrap(c1.position.getW()), radius, false); // unsorted
              // If the two collections of points are the same collection, then
              // the first neighbor would be the point itself and would have to be skipped.
              // But that's not the case here, so start at index 0:
              for (int i=0, n=search2.numNeighbors(); i<n; ++i) {
                final ConstellationPlus c2 = search2.getSampler(i).get();
                if (c1.matches(c2, angle_epsilon, len_epsilon_sq, comparison_type)) {
                  pointmatches.add(new PointMatch(c1.position, c2.position));
                }
              }
            }
            return pointmatches;
          }
        }));
      }
      uniquePointMatches(futures, pointmatches);
    } finally {
      exe.shutdown();
    }
    return new PointMatchesPlus(pointmatches);
  }
}

