from java.lang.invoke import MethodHandles, MethodType, LambdaMetafactory
from java.lang import Void
from java.util.function import Consumer
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.type.operators import SetOne
from net.imglib2.img.array import ArrayImgs

caller = MethodHandles.lookup()
target = caller.findVirtual(SetOne, "setOne", MethodType.methodType(Void.TYPE))
mh = MethodType.methodType(Void.TYPE, SetOne)
site = LambdaMetafactory.metafactory(caller, # execution context
                                     "accept", # name of method to implement in Consumer interface
                                     MethodType.methodType(Consumer), # return type is the interface to implement, then type of capture variable
                                     MethodType.methodType(Void.TYPE, mh.generic().parameterList()), # return type signature of Consumer.accept, plus no arguments
                                     target, # method to invoke on argument of Consumer.accept
                                     mh) # signature of return type of Consumer.accept


img = ArrayImgs.unsignedBytes([512, 512, 5])
img.cursor().forEachRemaining(site.getTarget().invokeWithArguments())
print img

"""
mh = site.getTarget()
print mh
print mh.type()
consumer = mh.invokeWithArguments()

t = UnsignedByteType(0)
consumer.accept(t)
"""

#print t

"""

public void testFunctionWithParameter() throws Throwable {
    SimpleBean simpleBean = new SimpleBean();

    MethodHandles.Lookup caller = MethodHandles.lookup();
    MethodType invokedType = MethodType.methodType(BiFunction.class);
    MethodType biFunc = MethodType.methodType(String.class, String.class);
    MethodHandle target = caller.findVirtual(SimpleBean.class, "simpleFunction", biFunc);
    MethodType func = target.type();


    CallSite site = LambdaMetafactory.metafactory(
            caller,
            "apply",
            invokedType,
            func.generic(),
            target,
            MethodType.methodType(String.class, SimpleBean.class, String.class)
    );

    BiFunction<SimpleBean, String, String> fullFunction = (BiFunction<SimpleBean, String, String>) site.getTarget().invokeExact();


    System.out.println(fullFunction.apply(simpleBean, "FOO"));

}

private class SimpleBean {
    public String simpleFunction(String in) {
        return "The parameter was " + in;
    }
}

"""