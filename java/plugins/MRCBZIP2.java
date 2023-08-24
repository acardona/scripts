package plugins;

import java.io.FileInputStream;
import org.apache.commons.compress.compressors.bzip2.BZip2CompressorInputStream;
import ij.ImagePlus;
import ij.process.ShortProcessor;
import ij.io.FileInfo;


import ini.trakem2.display.Display;
import ini.trakem2.display.Patch;


public class MRCBZIP2 {

 	//Files are MRC 16-bit with an offset of 1024 bytes

	public static ImagePlus decompress16bit(final String path) {
 		try {
 			final BZip2CompressorInputStream bzip2 = new BZip2CompressorInputStream(new FileInputStream(path));
 			final byte[] buf = new byte[1024];
 			bzip2.read(buf, 0, buf.length);
 		
 			final boolean bigEndian = (readInt(buf, 0xd0, false) == 0x2050414d) && buf[0xd4] == 17;
 			final int width = readInt(buf, 0, bigEndian);
 			final int height = readInt(buf, 4, bigEndian);
 			final int n_images = readInt(buf, 8, bigEndian);
 			if (n_images > 1) {
 				System.out.println("WARNING: ignoring images beyond the first at " + path);
 			}
 			final int dtype = readInt(buf, 12, bigEndian);
 			// COMMENTED OUT: turns out it is SIGNED *sigh*
 			//if (dtype != FileInfo.GRAY16_UNSIGNED) {
 			//	System.out.println("Not a 16-bit unsigned image at " + path);
 			//	return null;
 			//}
 			final int extended_header_size = readInt(buf, 0x5c, bigEndian);

 			// Read the rest
 			final byte[] bytes = new byte[extended_header_size + 2 * width * height];
 			bzip2.read(bytes);
 			bzip2.close();
 			
 			final short[] shorts = new short[width * height];
 			if (bigEndian) {
 				for (int i=0, j=extended_header_size; i<shorts.length; ++i, j+=2) {
 					shorts[i] = (short)(((bytes[j] & 0xff) << 8) | (bytes[j+1] & 0xff));
 				}
 			} else {
 				
 				for (int i=0, j=extended_header_size; i<shorts.length; ++i, j+=2) {
 					shorts[i] = (short)((bytes[j] & 0xff) | ((bytes[j+1] & 0xff) << 8));
 				}
 			}
 		
 		return new ImagePlus(path, new ShortProcessor(width, height, shorts, null));
 	} catch (Exception e) {
 		System.out.println("Failed to decompress: " + path);
 		e.printStackTrace();
 	}
 	return null;
 }

	static private final int readInt(final byte[] buf, final int start, final boolean bigEndian) {
		int b0 = buf[start] & 0xff;
		int b1 = buf[start + 1] & 0xff;
		int b2 = buf[start + 2] & 0xff;
		int b3 = buf[start + 3] & 0xff;
		if (bigEndian)
			return b3 | (b2 << 8) | (b1 << 16) | (b0 << 24);
		return b0 | (b1 << 8) | (b2 << 16) | (b3 << 24);
	}

	static private final int getType(int datatype) {
		switch (datatype) {
			case 0: return FileInfo.GRAY8;
			case 1: return FileInfo.GRAY16_SIGNED;
			case 2: return FileInfo.GRAY32_FLOAT;
			case 6: return FileInfo.GRAY16_UNSIGNED;
		}
		// else, error:
		return -1;
	}

	static public void main(final String[] args){
		final Patch p = (Patch) Display.getFrontLayer().getDisplayables().get(0);
		decompress16bit(p.getImageFilePath() + ".bz2").show();
	}

}