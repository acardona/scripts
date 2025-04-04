package my;
import net.imglib2.type.numeric.integer.UnsignedByteType;

public class CopyUnsignedByteType implements BiFunction<UnsignedByteType, UnsignedByteType, UnsignedByteType> {

  public UnsignedByteType apply(final UnsignedByteType src, final UnsignedByteType tgt) {
		tgt.set(src);
		return tgt;
	}
}
