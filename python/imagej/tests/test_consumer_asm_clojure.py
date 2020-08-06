from net.imglib2.img.array import ArrayImgs
from time import time
from net.imglib2.type.numeric.integer import UnsignedByteType
from java.util.function import Predicate, Consumer, Function
import sys
from org.objectweb.asm import ClassWriter, Opcodes
from java.lang import Object, ClassLoader, String, Class, Integer

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


# TEST:
img = ArrayImgs.unsignedBytes([512, 512, 5])
n_iterations = 5

for i in xrange(n_iterations):
  c = createConsumerInvokeSetOne()
  t0 = time()
  img.cursor().forEachRemaining(c())
  t1 = time()
  print "stream ASM:", t1 - t0 # 10 to 20 milliseconds: ~5 times slower than a clojure loop, and far more verbose




from org.scijava.plugins.scripting.clojure import ClojureScriptEngine
from net.imglib2.util.Util import getTypeFromInterval

# TEST with clojure, plain loop
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


# TEST with clojure, Consumer interface
code = """
(reify java.util.function.Consumer
  (accept [this o]
    (let [^%s t o]
      (.setOne o))))
""" % type_class # the UnsignedByteType of the img

var = clj.eval(code) # returns a clojure.lang.Var
#clj_setOne = var.get() # returns an anonymous Consumer instance

for i in xrange(n_iterations):
  t0 = time()
  img.cursor().forEachRemaining(var)
  t1 = time()
  print "stream clojure:", t1 - t0