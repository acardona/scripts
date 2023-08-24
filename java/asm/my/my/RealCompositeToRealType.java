package my;

import net.imglib2.converter.Converter;
import net.imglib2.type.numeric.RealType;
import net.imglib2.view.composite.RealComposite;

public class RealCompositeToRealType<S extends RealType<S>, T extends RealType<T>> implements Converter<RealComposite<S>, T>
{
	@Override
	public final void convert(final RealComposite<S> input, final T output)
	{
		output.setZero(); // must reset, it's reused for every pixel
		for ( final S s : input )
		{
			output.setReal( Math.max(s.getRealDouble(), output.getRealDouble() ) );
		}
	}
}
