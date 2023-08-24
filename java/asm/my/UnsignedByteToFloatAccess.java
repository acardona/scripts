package my;

import net.imglib2.type.numeric.integer.UnsignedByteType;
import net.imglib2.type.numeric.real.FloatType;
import net.imglib2.img.basictypeaccess.FloatAccess;
import net.imglib2.Sampler;

public class UnsignedByteToFloatAccess implements FloatAccess
{
	final private Sampler<? extends UnsignedByteType> sampler;

	public UnsignedByteToFloatAccess(final Sampler<? extends UnsignedByteType> sampler)
	{
		this.sampler = sampler;
	}
	@Override
	public final float getValue(final int index)
	{
		return sampler.get().getRealFloat();
	}
	@Override
	public final void setValue(final int index, final float value)
	{
		sampler.get().setReal(value);
	}
}

