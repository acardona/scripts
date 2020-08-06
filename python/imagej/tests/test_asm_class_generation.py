from org.objectweb.asm import ClassWriter, Opcodes, Type
from java.lang import Object, ClassLoader, Class, String, Integer
from net.imglib2.converter import Converter, Converters
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.type.numeric.real import FloatType
from itertools import imap, repeat

# Create a Converter<UnsignedByteType, FloatType> using the ASM library


class_name = "my/UnsignedByteToFloatConverter"
class_object = Type.getInternalName(Object)

# Type I for UnsignedByteType
# Type O for FloatType
# Object for superclass
# Converter<I, O> for interface
class_signature = "<I:L%s;O:L%s;>L%s;L%s<TI;TO;>;" % \
  tuple(imap(Type.getInternalName, (UnsignedByteType, FloatType, Object, Converter)))

print class_signature

# Two arguments, one parameter for each: one for I, and another for O
# void return type: V
method_signature = "(TI;TO;)V;"

cw = ClassWriter(ClassWriter.COMPUTE_FRAMES)
cw.visit(Opcodes.V1_8,                      # java version
         Opcodes.ACC_PUBLIC,                # public class
         class_name,                        # package and class name
         class_signature,                   # signature (None means not generic)
         class_object,                      # superclass
         [Type.getInternalName(Converter)]) # array of interfaces

# Default constructor
constructor = cw.visitMethod(Opcodes.ACC_PUBLIC,  # public
                             "<init>",            # method name
                             "()V",               # descriptor
                             None,                # signature
                             None)                # Exceptions (array of String)

# ... has to invoke the super() for Object
constructor.visitCode()
constructor.visitVarInsn(Opcodes.ALOAD, 0) # load "this" onto the stack: the first local variable is "this"
constructor.visitMethodInsn(Opcodes.INVOKESPECIAL, # invoke an instance method (non-virtual)
                            class_object,          # class on which the method is defined
                            "<init>",              # name of the method (the default constructor of Object)
                            "()V",                 # descriptor of the default constructor of Object
                            False)                 # not an interface
constructor.visitInsn(Opcodes.RETURN) # End the constructor method
constructor.visitMaxs(1, 1) # The maximum number of stack slots (1) and local vars (1: "this")

# The convert(I, O) method from the Converter interface
method = cw.visitMethod(Opcodes.ACC_PUBLIC, # public method
                        "convert",          # name of the interface method we are implementing
                        "(L%s;L%s;)V" % tuple(imap(Type.getInternalName, (UnsignedByteType, FloatType))), # descriptor
                        "(TI;TO;)",         # signature
                        None)               # Exceptions (array of String)

method.visitCode()
method.visitVarInsn(Opcodes.ALOAD, 2) # Load second argument onto stack: the FloatType
method.visitVarInsn(Opcodes.ALOAD, 1) # Load first argument onto stack: the UnsignedByteType
method.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                       Type.getInternalName(UnsignedByteType),
                       "getRealFloat",
                       "()F", # descriptor: no arguments, returns float
                       False)
method.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                       Type.getInternalName(FloatType),
                       "setReal",
                       "(F)V",
                       False)
method.visitInsn(Opcodes.RETURN)
method.visitMaxs(2, 3) # 2 stack slots: the two ALOAD calls. And 3 local variables: this, and two method arguments.
method.visitEnd()

"""
# Not done yet: now the public volatile bridge, because the above method uses generics
# Does not seem to be necessary to run the convert method.
# This method takes an (Object, Object) as arguments and casts them to the expected types,
# and then invokes the above typed version of the "convert" method.
# The only reason I am adding it here is because I saw it when I printed the class byte code,
# after writing the converter in java and using this command to see the asm code:
# $ java -classpath /home/albert/Programming/fiji-new/Fiji.app/jars/imglib2-5.1.0.jar:/home/albert/Programming/fiji-new/Fiji.app/jars/asm-5.0.4.jar://home/albert/Programming/fiji-new/Fiji.app/jars/asm-util-4.0.jar org.objectweb.asm.util.Textifier my/UnsignedByteToFloatConverter.class

bridge = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_SYNTHETIC | Opcodes.ACC_BRIDGE,
                        "convert",
                        "(L%s;L%s;)V" % tuple(repeat(class_object, 2)),
                        "(L%s;L%s;)V" % tuple(repeat(class_object, 2)),
                        None)
bridge.visitCode()
bridge.visitVarInsn(Opcodes.ALOAD, 0)
bridge.visitVarInsn(Opcodes.ALOAD, 1)
bridge.visitTypeInsn(Opcodes.CHECKCAST, Type.getInternalName(UnsignedByteType))
bridge.visitVarInsn(Opcodes.ALOAD, 2)
bridge.visitTypeInsn(Opcodes.CHECKCAST, Type.getInternalName(FloatType))
bridge.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                       class_name,
                       "convert",
                       "(L%s;L%s;)V" % tuple(imap(Type.getInternalName, (UnsignedByteType, FloatType))), # descriptor
                       False)
bridge.visitInsn(Opcodes.RETURN)
bridge.visitMaxs(3, 3)
bridge.visitEnd()
"""



class Loader(ClassLoader):
  def defineClass(self, name, bytes):
    # Inheritance of protected methods is complicated in jython
    m = super(ClassLoader, self).__thisclass__.getDeclaredMethod("defineClass", String, Class.forName("[B"), Integer.TYPE, Integer.TYPE)
    m.setAccessible(True)
    return m.invoke(self, name.replace("/", "."), bytes, 0, len(bytes))

clazz = Loader().defineClass(class_name, cw.toByteArray())


"""
loader = ClassLoader.getSystemClassLoader()
defineClass = loader.getClass().getSuperclass().getSuperclass().getSuperclass().getDeclaredMethod("defineClass", String, Class.forName("[B"), Integer.TYPE, Integer.TYPE)
defineClass.setAccessible(True)
bytes = cw.toByteArray()
clazz = defineClass.invoke(loader, class_name.replace("/", "."), bytes, 0, len(bytes))
"""



bt = UnsignedByteType(120)
ft = FloatType()
conv = clazz.newInstance()
conv.convert(bt, ft)
print ft



