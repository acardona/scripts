package my;

import ij.process.ShortProcessor;
import java.lang.Math;
import java.lang.Integer;

/** As concieved by Pedro Gómez Gálvez, November 2023, written in java by Albert Cardona. */
public class Pixels {

	static public void enhancedMinAndMax(final ShortProcessor sp, final int n_stdDevs) {
		final short[] pixels = (short[])sp.getPixels();
		// Find non-zero pixels and their sum
		final int[] non_zero = new int[pixels.length];
		long sum = 0;
		int count = 0;
		for (int i=0; i<pixels.length; ++i) {
			int pixel = pixels[i] & 0xffff;
			if (0 == pixel) continue;
			non_zero[count++] = pixel;
			sum += pixel;
		}
		// Compute mean of non-zero pixels
		final double mean = ((double)sum) / count;
		// Compute stdDev of non-zero pixels
		double sumSqDiff = 0;
		for (int i=0; i<count; ++i) {
			sumSqDiff += Math.pow(non_zero[i] - mean, 2);
		}
		final double stdDev = Math.sqrt(sumSqDiff / count);
		// Define a lower and an upper bound
		final double lower_bound = mean - n_stdDevs * stdDev;
		final double upper_bound = mean + n_stdDevs * stdDev;
		// Find the min and max values within the range
		double min = Integer.MAX_VALUE;
		double max = 0;
		for (int i=0; i<count; ++i) {
			int pixel = non_zero[i];
			if (pixel < min && pixel > lower_bound) min = pixel;
			if (pixel > max && pixel < upper_bound) max = pixel;
		}
		sp.setMinAndMax(min, max);
	}

	/** Avoids duplicating the pixel array at the cost of an 'if' per pixel,
	 *  trading memory for CPU. */
	static public void enhancedMinAndMaxSimpler(final ShortProcessor sp, final int n_stdDevs, final boolean exact) {
		final short[] pixels = (short[])sp.getPixels();
		// Find non-zero pixels and their sum
		long sum = 0;
		int count = 0;
		for (int i=0; i<pixels.length; ++i) {
			int pixel = pixels[i] & 0xffff;
			if (0 == pixel) continue;
			sum += pixel;
			++count;
		}
		// Compute mean of non-zero pixels
		final double mean = ((double)sum) / count;
		// Compute stdDev of non-zero pixels
		double sumSqDiff = 0;
		for (int i=0; i<pixels.length; ++i) {
			int pixel = pixels[i] & 0xffff;
			if (0 == pixel) continue;
			sumSqDiff += Math.pow(pixel - mean, 2);
		}
		final double stdDev = Math.sqrt(sumSqDiff / count);
		// Define a lower and an upper bound
		final double lower_bound = mean - n_stdDevs * stdDev;
		final double upper_bound = mean + n_stdDevs * stdDev;
		if (!exact) {
			sp.setMinAndMax(lower_bound, upper_bound);
			return;
		}
		// Find the min and max values within the range
		double min = Integer.MAX_VALUE;
		double max = 0;
		for (int i=0; i<count; ++i) {
			int pixel = pixels[i] & 0xffff;
			if (0 == pixel) continue;
			if (pixel < min && pixel > lower_bound) min = pixel;
			if (pixel > max && pixel < upper_bound) max = pixel;
		}
		sp.setMinAndMax(min, max);
	}
}
