package my;

import net.imglib2.IterableInterval;
import net.imglib2.type.numeric.RealType;
import net.imglib2.Cursor;
import java.lang.Math;


public class ImgCompare {

  /** Single-threaded.
      Assumes:
        - images are of the same dimensions.
        - images can be iterated in the same way.
        - images are small enough that adding up their pixel values won't overflow a double.
  */
  static public double cosyneSimilarity(final IterableInterval<RealType<?>> img1,
                                        final IterableInterval<RealType<?>> img2) {
    final Cursor<RealType<?>> c1 = img1.cursor(),
                              c2 = img2.cursor();
    
    double sumMul = 0,
           sumSq1 = 0,
           sumSq2 = 0;
    
    while (c1.hasNext()) {
    	final double v1 = c1.next().getRealDouble(),
    	             v2 = c2.next().getRealDouble();
    	sumMul += v1 * v2;
    	sumSq1 += Math.pow(v1, 2);
    	sumSq2 += Math.pow(v2, 2);
    }
    
    return sumMul / ( Math.sqrt(sumSq1) + Math.sqrt(sumSq2) );
  }
}