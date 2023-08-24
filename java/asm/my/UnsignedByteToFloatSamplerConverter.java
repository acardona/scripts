package my;

import net.imglib2.type.numeric.integer.UnsignedByteType;
import net.imglib2.type.numeric.real.FloatType;
import net.imglib2.img.basictypeaccess.FloatAccess;
import net.imglib2.Sampler;
import net.imglib2.converter.readwrite.SamplerConverter;

public class UnsignedByteToFloatSamplerConverter implements SamplerConverter<UnsignedByteType, FloatType>
{
	@Override
	public FloatType convert(final Sampler<? extends UnsignedByteType> sampler)
	{
		return new FloatType(new UnsignedByteToFloatAccess(sampler));
	}
}

