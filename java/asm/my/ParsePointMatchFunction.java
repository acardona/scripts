package my;

import mpicbg.models.Point;
import mpicbg.models.PointMatch;
import java.util.function.Function;

public final class ParsePointMatchFunction implements Function<String, PointMatch>
{
	final public PointMatch apply(final String row) {
		final String[] cols = row.split(",");
		return new PointMatch(
			new Point(new double[]{Double.parseDouble(cols[0]), Double.parseDouble(cols[1])}),
			new Point(new double[]{Double.parseDouble(cols[2]), Double.parseDouble(cols[3])}));
	}
}
