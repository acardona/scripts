package my;

import net.imglib2.type.numeric.integer.UnsignedByteType;
import net.imglib2.type.numeric.real.FloatType;
import net.imglib2.converter.Converter;

public class UnsignedByteToFloatConverter<I extends UnsignedByteType, O extends FloatType> implements Converter<I, O>
{
	public void convert(I input, O output)
	{
		output.setReal(input.getRealFloat());
	}
}
