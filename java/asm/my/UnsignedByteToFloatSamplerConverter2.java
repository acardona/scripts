package my;

import net.imglib2.type.numeric.integer.UnsignedByteType;
import net.imglib2.type.numeric.real.FloatType;
import net.imglib2.img.basictypeaccess.FloatAccess;
import net.imglib2.Sampler;
import net.imglib2.converter.readwrite.SamplerConverter;

public class UnsignedByteToFloatSamplerConverter2 implements SamplerConverter<UnsignedByteType, FloatType>
{
	@Override
	public FloatType convert(final Sampler<? extends UnsignedByteType> sampler)
	{
		return new FloatType(new FloatAccess() {
			final Sampler<? extends UnsignedByteType> sampler_ = sampler;
			final public float getValue(final int index) {
				return this.sampler_.get().getRealFloat();
			}
			final public void setValue(final int index, final float value) {
				this.sampler_.get().setReal(value);
			}
		});
	}
}

