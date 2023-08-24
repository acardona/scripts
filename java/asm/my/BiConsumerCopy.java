package my;
import net.imglib2.type.numeric.real.FloatType;
import net.imglib2.type.numeric.integer.UnsignedByteType;
import java.util.function.BiConsumer;

public class BiConsumerCopy< T extends FloatType, U extends UnsignedByteType > implements BiConsumer< T, U>
{
	public void accept(final T source, final U target) {
		target.setReal(source.getRealFloat());
	}
}
