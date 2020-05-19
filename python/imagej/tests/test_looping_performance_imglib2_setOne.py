from net.imglib2.img.array import ArrayImgs
from time import time
from itertools import imap
from collections import deque
from net.imglib2.util.Util import getTypeFromInterval
from org.scijava.plugins.scripting.clojure import ClojureScriptEngine
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.type.operators import SetOne
from java.util.function import Predicate, Consumer, Function
from java.lang.invoke import MethodHandles, MethodType, LambdaMetafactory
from java.lang import Void
import sys
from org.objectweb.asm import ClassWriter, Opcodes
from java.lang import Object, ClassLoader, String, Class, Integer

img = ArrayImgs.unsignedBytes([512, 512, 5])

n_iterations = 4


# Test 1: for loop
for i in xrange(n_iterations):
  t0 = time()
  for t in img.cursor():
    t.setOne()
  t1 = time()
  print "looping:", t1 - t0 # About 1 seconds


# Test 2: imap + deque with maxlen=0
for i in xrange(n_iterations):
  t0 = time()
  # Performance almost as bad as the for loop
  #deque(imap(lambda t: t.setOne(), img.cursor()), maxlen=0)
  # Discover the type and grab it's setOne method
  setter = getattr(getTypeFromInterval(img).getClass(), "setOne")
  deque(imap(setter, img.cursor()), maxlen=0)
  # Just as slow as above, but less general
  #deque(imap(UnsignedByteType.setOne, img.cursor()), maxlen=0)
  t1 = time()
  print "deque:", t1 - t0 # About 0.5 seconds


# Test 2.1: reduce
for i in xrange(n_iterations):
  t0 = time()
  reduce(lambda r, x: x.setOne(), img.cursor())
  t1 = time()
  print "reduce:", t1 - t0 # About 0.5 seconds

# Test 2.2: filter
for i in xrange(n_iterations):
  t0 = time()
  setter = getattr(getTypeFromInterval(img).getClass(), "setOne")
  filter(setter, img.cursor())
  t1 = time()
  print "filter:", t1 - t0 # About 0.5 seconds


# Test 3: with clojure
clj = ClojureScriptEngine()
type_class = getTypeFromInterval(img).getClass().getName()
code = """
(import '(net.imglib2 IterableInterval Cursor))
(defn setOne [^IterableInterval img]
  (loop [^Cursor c (.cursor img)]
    (when (.hasNext c)
      (let [^%s t (.next c)]
        (.setOne t)
        (recur c)))))
""" % type_class
var = clj.eval(code) # returns a clojure.lang.Var
clj_fn = var.get() # returns a clojure.lang.AFunction

for i in xrange(n_iterations):
  t0 = time()
  clj_fn.invoke(img)
  t1 = time()
  print "clojure:", t1 - t0 # About 1 to 10 milliseconds !!!




class CP(Consumer):
  def __init__(self, fn):
    self.accept = fn


# Test 4: with Consumer but using a jython function
for i in xrange(n_iterations):
  t0 = time()
  img.cursor().forEachRemaining(CP(UnsignedByteType.setOne))
  t1 = time()
  print "stream python fn:", t1 - t0 # 0.7 seconds




class CustomClassLoader(ClassLoader):
  def defineClass(self, name, bytes):
    """
       name: the fully qualified (i.e. with packages) name of the class to load.
       bytes: a byte[] (a byte array) containing the class bytecode.
       Invokes the defineClass of the parent ClassLoader, which is a protected method.
    """
    # Inheritance of protected methods is complicated in jython
    m = super(ClassLoader, self).__thisclass__.getDeclaredMethod("defineClass", String, Class.forName("[B"), Integer.TYPE, Integer.TYPE)
    m.setAccessible(True)
    try:
      return m.invoke(self, name.replace("/", "."), bytes, 0, len(bytes))
    except:
      print sys.exc_info()


def createConsumerInvokeSetOne():
  cw = ClassWriter(0)

  cw.visit(52, Opcodes.ACC_PUBLIC + Opcodes.ACC_FINAL + Opcodes.ACC_SUPER, "my/InvokeSetOne", "<T::Lnet/imglib2/type/operators/SetOne>Ljava/lang/ObjectLjava/util/function/Consumer<TT>;", "java/lang/Object", ["java/util/function/Consumer"])

  mv = cw.visitMethod(Opcodes.ACC_PUBLIC, "<init>", "()V", None, None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitMethodInsn(Opcodes.INVOKESPECIAL, "java/lang/Object", "<init>", "()V", False)
  mv.visitInsn(Opcodes.RETURN)
  mv.visitMaxs(1, 1)
  mv.visitEnd()

  mv = cw.visitMethod(Opcodes.ACC_PUBLIC + Opcodes.ACC_FINAL, "accept", "(Lnet/imglib2/type/operators/SetOne;)V", "(TT)V", None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 1)
  mv.visitMethodInsn(Opcodes.INVOKEINTERFACE, "net/imglib2/type/operators/SetOne", "setOne", "()V", True)
  mv.visitInsn(Opcodes.RETURN)
  mv.visitMaxs(1, 2)
  mv.visitEnd()

  mv = cw.visitMethod(Opcodes.ACC_PUBLIC + Opcodes.ACC_BRIDGE + Opcodes.ACC_SYNTHETIC, "accept", "(Ljava/lang/Object;)V", None, None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitVarInsn(Opcodes.ALOAD, 1)
  mv.visitTypeInsn(Opcodes.CHECKCAST, "net/imglib2/type/operators/SetOne")
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "my/InvokeSetOne", "accept", "(Lnet/imglib2/type/operators/SetOne;)V", False)
  mv.visitInsn(Opcodes.RETURN)
  mv.visitMaxs(2, 2)
  mv.visitEnd()

  cw.visitEnd()

  # Load class
  return CustomClassLoader().defineClass("my.InvokeSetOne", cw.toByteArray())


# Test 5: with Stream and ASM
for i in xrange(n_iterations):
  c = createConsumerInvokeSetOne()
  t0 = time()
  img.cursor().forEachRemaining(c())
  t1 = time()
  print "stream ASM:", t1 - t0 # 10 to 20 milliseconds: ~5 times slower than a clojure loop, and far more verbose



caller = MethodHandles.lookup()
target = caller.findVirtual(SetOne, "setOne", MethodType.methodType(Void.TYPE))
mh = MethodType.methodType(Void.TYPE, SetOne)
site = LambdaMetafactory.metafactory(caller, # execution context
                                     "accept", # name of method to implement in Consumer interface
                                     MethodType.methodType(Consumer), # return type is the interface to implement, then type of capture variable
                                     MethodType.methodType(Void.TYPE, mh.generic().parameterList()), # return type signature of Consumer.accept, plus no arguments
                                     target, # method to invoke on argument of Consumer.accept
                                     mh) # signature of return type of Consumer.accept

setOne = site.getTarget().invokeWithArguments()

for i in xrange(n_iterations):
  t0 = time()
  img.cursor().forEachRemaining(setOne)
  t1 = time()
  print "steam method:", t1 - t0 # 8 ms -- comparable to a clojure loop
