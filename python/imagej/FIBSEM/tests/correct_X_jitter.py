from ij import IJ
from ij.process import ShortProcessor
from ij import ImagePlus


try:
  from fiji.scripting import Weaver
  # Check if the tools.jar is in the classpath
  try:
    from java.lang import Class
    Class.forName("com.sun.tools.javac.Main")
  except:
    print "*** tools.jar not in the classpath ***"
except:
  print "*** fiji.scripting.Weaver NOT installed ***"
  Weaver = None
  print sys.exc_info()


wd = Weaver.method("""
static public final short[] correctXJitter(final ShortProcessor sp, final int delta) {
  final short[] pixels = (short[])sp.getPixels(),
                pixels2 = new short[pixels.length];
  final int width = sp.getWidth(),
            height = sp.getHeight();
  // Copy first line
  System.arraycopy(pixels, 0, pixels2, 0, width);
  // Start at the second line, for every line
  int min_d_accum = 0;
  for (int i=1; i<height; ++i) {
    int offset1 = i * width;
    int offset0 = offset1 - width;
    double min_sum = Long.MAX_VALUE;
    int min_d = 0;
    for (int d=-delta; d<=delta; ++d) {
      // For every pixel in the line, sum the square of the difference
      double sum = 0;
      for (int k=delta; k<width - delta; ++k) { // delta is much smaller than width
        sum += Math.pow(pixels[offset0 + k] - pixels[offset1 + k + d], 2);
      }
      System.out.println("line: " + i + " delta: " + d + " sum: " + sum);
      if (sum < min_sum) {
        min_sum = sum;
        min_d = -d;
      } else if (sum == min_sum) {
        if (Math.abs(d) < Math.abs(min_d)) {
          min_d = -d;
        }
      }
    }
    min_d_accum += min_d;
    System.out.println("line: " + i + " chosen delta: " + min_d + " accum delta: " + min_d_accum);
    // TODO fix boundaries
    System.arraycopy(pixels, offset1, pixels2, offset1 + min_d_accum, width - delta); // TODO not delta
  }
  return pixels2;
}
""", [ShortProcessor], False)

imp = IJ.getImage()
pixels2 = wd.correctXJitter(imp.getProcessor(), 4)

ImagePlus("corrected", ShortProcessor(imp.getWidth(), imp.getHeight(), pixels2, None)).show()



