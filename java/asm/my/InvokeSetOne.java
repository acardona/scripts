package my;
import java.util.function.Consumer;
import net.imglib2.type.operators.SetOne;

public final class InvokeSetOne<T extends SetOne> implements Consumer<T> {
	public final void accept(final T t) {
		t.setOne();
	}
}
