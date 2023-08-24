package my;

import java.io.RandomAccessFile;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.ByteBuffer;
import net.imglib2.type.numeric.RealType;
import net.imglib2.type.numeric.integer.UnsignedByteType;
import net.imglib2.type.numeric.integer.UnsignedShortType;
import net.imglib2.type.numeric.real.FloatType;
import net.imglib2.img.Img;
import net.imglib2.img.array.ArrayImg;
import net.imglib2.img.array.ArrayImgs;

public class Read2DImageROI
{
	static public final <T extends RealType<T>> Img<T> read(
			final String path,
			final long[] dimensions,
			final long[] minC,
			final long[] maxC,
			final T pixelType,
			final long header)
		throws FileNotFoundException, IOException
	{
		final RandomAccessFile ra = new RandomAccessFile(path, "r");
		try {
			final int minX = (int)minC[0],
			          minY = (int)minC[1],
								maxX = (int)maxC[0],
								maxY = (int)maxC[1],
								width = (int)dimensions[0],
								height = (int)dimensions[1],
			          roi_width  = (int)(maxX - minX + 1),
						    roi_height = (int)(maxY - minY + 1), 
								tailX = (int)(width - roi_width - minX),
								size = roi_width * roi_height,
			          n_bytes_per_pixel = pixelType.getBitsPerPixel() / 8;
			
			final byte[] bytes = new byte[size * n_bytes_per_pixel];
			
			ra.seek(header + (minY * width + minX) * n_bytes_per_pixel);

			for (int h=0; h<roi_height; ++h) {
				ra.readFully(bytes, roi_width * n_bytes_per_pixel, roi_width * n_bytes_per_pixel);
				ra.skipBytes((tailX + minX) * n_bytes_per_pixel);
			}

			final long[] roiDims = new long[]{roi_width, roi_height};

			if (pixelType instanceof UnsignedByteType) {
				return (Img<T>) ArrayImgs.unsignedBytes(bytes, roiDims);
			}
			if (pixelType instanceof UnsignedShortType) {
				final short[] shorts = new short[size];
				ByteBuffer.wrap(bytes).asShortBuffer().get(shorts);
				return (Img<T>) ArrayImgs.unsignedShorts(shorts, roiDims);
			}
			if (pixelType instanceof FloatType) {
				final float[] floats = new float[size];
				ByteBuffer.wrap(bytes).asFloatBuffer().get(floats);
				return (Img<T>) ArrayImgs.floats(floats, roiDims);
			}
			return null;

		} finally {
			ra.close();
		}
	}
}
