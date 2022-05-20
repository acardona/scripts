from org.objectweb.asm import ClassWriter, Opcodes, Type, Label
from java.lang import Object, Class, Math
from net.imglib2.converter.readwrite import SamplerConverter
from net.imglib2 import Sampler, RandomAccessibleInterval, InterableInterval
from net.imglib2.converter import Converter, Converters
from net.imglib2.type import Type as ImgLib2Type # must alias
from itertools import imap, repeat
# Local lib
from lib.asm import initClass, initMethod, initConstructor, CustomClassLoader


def defineSamplerConverter(fromType,
                           toType,
                           classname="",
                           toAccess=None,
                           fromMethod="getRealFloat",
                           fromMethodReturnType="F", # F: native float; if a class, use: "L%s;" % Type.getInternalName(TheClass)
                           toMethod="setReal",
                           toMethodArgType="F"): # F: native float
  """ A class implementing SamplerConverter, in asm for high-performance (25x jython's speed).

      fromType: the source type to convert like e.g. UnsignedByteType.
      toType: the target type, like e.g. FloatType.
      classname: optional, the fully qualified name for the new class implementing SamplerConverter.
      fromMethod: the name of the fromType class method to use for getting its value.
                  Defaults to "getRealFloat" from the RealType interface.
      fromMethodReturnType: a single letter, like:
        'F': float, 'D': double, 'C': char, 'B': byte, 'Z': boolean, 'S': short, 'I': integer, 'J': long
        See: https://gitlab.ow2.org/asm/asm/blob/master/asm/src/main/java/org/objectweb/asm/Frame.java
      toMethod: the name of the toType class method for setting the value.
                Defaults to "setReal" from the RealType interface.
      toMethodArgType: a single letter, like:
        'F': float, 'D': double, 'C': char, 'B': byte, 'Z': boolean, 'S': short, 'I': integer, 'J': long
      toAccess: the interface to implement, such as FloatAccess. Optional, will be guessed. """

  if toAccess is None:
    toTypeName = toType.getSimpleName()
    name = toTypeName[0:toTypeName.rfind("Type")]
    if name.startswith("Unsigned"):
      name = name[8:]
    toAccessName = "net.imglib2.img.basictypeaccess.%sAccess" % name
    toAccess = CustomClassLoader().loadClass("net.imglib2.img.basictypeaccess.%sAccess" % name)

  if "" == classname:
    classname = "asm/converters/%sTo%sSamplerConverter" % (fromType.getSimpleName(), toType.getSimpleName())

  access_classname = "asm/converters/%sTo%sAccess" % (fromType.getSimpleName(), toType.getSimpleName())

  # First *Access class like e.g. FloatAccess
  facc = initClass(access_classname,
                   access=Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL,
                   interfaces=[toAccess],
                   interfaces_parameters={},
                   with_default_constructor=False)

  # private final "sampler" field
  f = facc.visitField(Opcodes.ACC_PRIVATE | Opcodes.ACC_FINAL,
                      "sampler",
                      "L%s;" % Type.getInternalName(Sampler),
                      "L%s<+L%s;>;" % tuple(imap(Type.getInternalName, (Sampler, fromType))),
                      None)

  # The constructor has to initialize the field "sampler"
  c = initConstructor(facc,
                      descriptor="(Lnet/imglib2/Sampler;)V",
                      signature="(Lnet/imglib2/Sampler<+L%s;>;)V" % Type.getInternalName(fromType))
  # The 'c' constructor already invoked <init>
  # Now onto the rest of the constructor body:
  c.visitVarInsn(Opcodes.ALOAD, 0)
  c.visitVarInsn(Opcodes.ALOAD, 1)
  field = {"classname": access_classname,
           "name": "sampler",
           "descriptor": "Lnet/imglib2/Sampler;"}
  c.visitFieldInsn(Opcodes.PUTFIELD, field["classname"], field["name"], field["descriptor"])
  c.visitInsn(Opcodes.RETURN)
  c.visitMaxs(2, 2)
  c.visitEnd()

  # Declare getValue and setValue methods
  gv = initMethod(facc,
                  "getValue",
                  access=Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL,
                  descriptor="(I)%s" % toMethodArgType) # e.g. "F" for native float
  gv.visitVarInsn(Opcodes.ALOAD, 0)
  gv.visitFieldInsn(Opcodes.GETFIELD, field["classname"], field["name"], field["descriptor"])
  gv.visitMethodInsn(Opcodes.INVOKEINTERFACE,
                    Type.getInternalName(Sampler),
                    "get",
                    "()L%s;" % Type.getInternalName(Object), # isn't this weird? Why Object?
                    True)
  gv.visitTypeInsn(Opcodes.CHECKCAST, Type.getInternalName(fromType))
  print Type.getInternalName(fromType), fromMethod, fromMethodReturnType
  gv.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                    Type.getInternalName(fromType),
                    fromMethod, # e.g. getRealFloat
                    "()%s" % fromMethodReturnType, # e.g. F for native float
                    False)
  # Figure out the return and the loading instructions: primitive or object class
  # (NOTE: will not work for array, that starts with '[')
  if fromMethodReturnType in ["F", "D"]: # 'F' for float, 'D' for double
    ret = fromMethodReturnType + "RETURN"
    load = fromMethodReturnType + "LOAD"
  elif 'J' == fromMethodReturnType: # 'J' is for long
    ret = "LRETURN"
    load = "LLOAD"
  elif fromMethodReturnType in ["S", "I", "B", "C", "Z"]: # 'C': char, 'B': byte, 'Z', boolean, 'S', short, 'I': integer
    ret = "IRETURN"
    load = "ILOAD"
  else:
    ret = "ARETURN" # object class
    load = "ALOAD"
  gv.visitInsn(Opcodes.__getattribute__(Opcodes, ret)._doget(Opcodes)) # Opcodes.FRETURN: native float return
  gv.visitMaxs(1, 2)
  gv.visitEnd()

  sv = initMethod(facc,
                  "setValue",
                  access=Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL,
                  descriptor="(I%s)V" % toMethodArgType) # e.g. "F" for native float
  sv.visitVarInsn(Opcodes.ALOAD, 0)
  sv.visitFieldInsn(Opcodes.GETFIELD, field["classname"], field["name"], field["descriptor"])
  sv.visitMethodInsn(Opcodes.INVOKEINTERFACE,
                    Type.getInternalName(Sampler),
                    "get",
                    "()L%s;" % Type.getInternalName(Object), # isn't this weird? Why Object?
                    True)
  sv.visitTypeInsn(Opcodes.CHECKCAST, Type.getInternalName(fromType))
  sv.visitVarInsn(Opcodes.__getattribute__(Opcodes, load)._doget(Opcodes), 2) # e.g. Opcodes.FLOAD
  sv.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                    Type.getInternalName(fromType),
                    toMethod, # e.g. setReal
                    "(%s)V" % toMethodArgType, # e.g. 'F' for native float
                    False)
  sv.visitInsn(Opcodes.RETURN)
  sv.visitMaxs(2, 3)
  sv.visitEnd()

  # The SamplerConverter outer class
  cw = initClass(classname,
                 interfaces=[SamplerConverter],
                 interfaces_parameters={SamplerConverter: [fromType, toType]})

  # In the signature, the + sign is for e.g. <? extends UnignedByteType>
  # Here, the signature is the same as the descriptor, but with parameter types
  # descriptor="(Lnet/imglib2/Sampler;)Lnet/imglib2/type/numeric/real/FloatType;"
  # signature="(Lnet/imglib2/Sampler<+Lnet/imglib2/type/numeric/integer/UnsignedByteType;>;)Lnet/imglib2/type/numeric/real/FloatType;",
  m = initMethod(cw, "convert",
                 argument_classes=[Sampler],
                 argument_parameters=[fromType],
                 argument_prefixes=['+'], # '+' means: <? extends UnsignedByteType>
                 return_type=toType)

  m.visitCode()
  m.visitTypeInsn(Opcodes.NEW, Type.getInternalName(toType))
  m.visitInsn(Opcodes.DUP)
  m.visitTypeInsn(Opcodes.NEW, access_classname)
  m.visitInsn(Opcodes.DUP)
  m.visitVarInsn(Opcodes.ALOAD, 1)
  m.visitMethodInsn(Opcodes.INVOKESPECIAL, # invoke new
                    access_classname,
                    "<init>", # constructor
                    "(L%s;)V" % Type.getInternalName(Sampler),
                    False)
  m.visitMethodInsn(Opcodes.INVOKESPECIAL, # create new toType with the *Access as argument
                    Type.getInternalName(toType),
                    "<init>", # constructor
                    "(L%s;)V" % Type.getInternalName(toAccess),
                    False)
  m.visitInsn(Opcodes.ARETURN) # ARETURN: return the object at the top of the stack
  m.visitMaxs(5, 2) # 5 stack slots: the two NEW calls, 1 ALOAD, 2 DUP (I think). And 2 local variables: this, and a method argument.
  m.visitEnd()

  # If bridge is not defined, the above 'convert' method cannot be invoked: would fail with AbstractMethodException
  # To be fair, the TextWriter on the compiled java version of this class did use the bridge.
  # The surprising bit is that, in test_asm_class_generation.py, the bridge is not necessary
  # even though the class is rather similar overall.
  bridge = cw.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_VOLATILE | Opcodes.ACC_BRIDGE,
                          "convert",
                          "(L%s;)L%s;" % tuple(imap(Type.getInternalName, (Sampler, Object))),
                          None,
                          None)
  bridge.visitCode()
  bridge.visitVarInsn(Opcodes.ALOAD, 0)
  bridge.visitVarInsn(Opcodes.ALOAD, 1)
  bridge.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                         classname,
                         "convert",
                         "(L%s;)L%s;" % tuple(imap(Type.getInternalName, (Sampler, toType))), # descriptor
                         False)
  bridge.visitInsn(Opcodes.ARETURN)
  bridge.visitMaxs(2, 2)
  bridge.visitEnd()

  # Load both classes
  loader = CustomClassLoader()
  accessClass = loader.defineClass(access_classname, facc.toByteArray())
  samplerClass = loader.defineClass(classname, cw.toByteArray())

  return samplerClass


def createSamplerConverter(*args, **kwargs):
  """ Returns a new instance of the newly defined class implementing the SamplerConverter interface.
      See defineSamplerConverter for all argument details. """
  return defineSamplerConverter(*args, **kwargs).newInstance()


def defineConverter(fromType,
                    toType,
                    classname="",
                    fromMethod="getRealFloat",
                    fromMethodReturnType="F", # e.g. "F" for native float
                    toMethod="setReal",
                    toMethodArgType="F"):
  """ Create a new Converter fromType toType.
  
      fromType: the net.imglib2.Type to see as transformed into toType.
      toType: the net.imglib2.Type to see.
      classname: optional, will be made up if not defined.
      fromMethod: the method for reading the value from the fromType.
                  Defaults to getRealFloat form the RealType interface.
      fromMethodReturnType: the return type of the method, e.g., "F" for native float or e.g., UnsignedByteType for class.
      toMethod: the method for setting the value to the toType.
                Defaults to setReal from the RealType interface.
      toMethodReturnType: like fromMethodReturnType.
  """

  if "" == classname:
    classname = "asm/converters/%sTo%sConverter" % (fromType.getSimpleName(), toType.getSimpleName())

  class_object = Type.getInternalName(Object)

  # Type I for fromType
  # Type O for toType
  # Object for superclass
  # Converter<I, O> for interface
  class_signature = "<I:L%s;O:L%s;>L%s;L%s<TI;TO;>;" % \
    tuple(imap(Type.getInternalName, (fromType, toType, Object, Converter)))

  # Two arguments, one parameter for each: one for I, and another for O
  # void return type: V
  method_signature = "(TI;TO;)V;"

  cw = ClassWriter(ClassWriter.COMPUTE_FRAMES)
  cw.visit(Opcodes.V1_8,                      # java version
           Opcodes.ACC_PUBLIC,                # public class
           classname,                         # package and class name
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
                          "(L%s;L%s;)V" % tuple(imap(Type.getInternalName, (fromType, toType))), # descriptor
                          "(TI;TO;)",         # signature
                          None)               # Exceptions (array of String)

  method.visitCode()
  method.visitVarInsn(Opcodes.ALOAD, 2) # Load second argument onto stack: the FloatType
  method.visitVarInsn(Opcodes.ALOAD, 1) # Load first argument onto stack: the UnsignedByteType
  method.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                         Type.getInternalName(fromType),
                         fromMethod, # e.g. "getRealFloat"
                         "()%s" % fromMethodReturnType, # descriptor: no arguments # e.g. "F" for native float
                         False)
  method.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                         Type.getInternalName(toType),
                         toMethod, # e.g. "setReal"
                         "(%s)V" % toMethodArgType, # e.g. "F" for native float
                         False)
  method.visitInsn(Opcodes.RETURN)
  method.visitMaxs(2, 3) # 2 stack slots: the two ALOAD calls. And 3 local variables: this, and two method arguments.
  method.visitEnd()

  # Now the public volatile bridge, because the above method uses generics.
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
  bridge.visitTypeInsn(Opcodes.CHECKCAST, Type.getInternalName(fromType))
  bridge.visitVarInsn(Opcodes.ALOAD, 2)
  bridge.visitTypeInsn(Opcodes.CHECKCAST, Type.getInternalName(toType))
  bridge.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                         classname,
                         "convert",
                         "(L%s;L%s;)V" % tuple(imap(Type.getInternalName, (fromType, toType))), # descriptor
                         False)
  bridge.visitInsn(Opcodes.RETURN)
  bridge.visitMaxs(3, 3)
  bridge.visitEnd()

  loader = CustomClassLoader()
  converterClass = loader.defineClass(classname, cw.toByteArray())

  return converterClass


def createConverter(*args, **kwargs):
  """ Returns a new instance of the newly defined class implementing the Converter interface.
      See defineConverter for all argument details. """
  return defineConverter(*args, **kwargs).newInstance()


def samplerConvert(rai, converter):
  """
    rai: an instance of RandomAccessibleInterval
    converter: an instance of a SamplerConverter.
  """
  # Grab method through reflection. Otherwise we get one that returns an IterableInterval
  # which is not compatible with ImageJFunctions.wrap methods.
  m = Converters.getDeclaredMethod("convert", [RandomAccessibleInterval, SamplerConverter])
  return m.invoke(None, rai, converter)


def convert2(rai, converter, toType, randomAccessible=True):
  """
    rai: an instance of RandomAccessibleInterval
    converter: as created with e.g. createConverter
    toType: class of the target Type
    randomAccessible: when True (default) use RandomAccessibleInterval, otherwise use IterableInterval
  """
  # Grab method through reflection. Otherwise we get one that returns an IterableInterval
  # which is not compatible with ImageJFunctions.wrap methods.
  m = Converters.getDeclaredMethod("convert", [RandomAccessibleInterval if randomAccessible else IterableInterval, Converter, ImgLib2Type])
  return m.invoke(None, rai, converter, toType.newInstance())


def convert(rai, toType, randomAccessible=True):
  """
    rai: an instance of RandomAccessibleInterval
    toType: class of the target Type
    randomAccessible: when True (default) use RandomAccessibleInterval, otherwise use IterableInterval
  """
  return convert2(rai, createConverter(type(rai.randomAccess().get()), toType), toType, randomAccessible=randomAccessible)
  

def makeCompositeToRealConverter(reducer_class=Math,
                                 reducer_method="max",
                                 reducer_method_signature="(DD)D",
                                 classloader=None):
  """
  Takes a RealComposite as input and converts it into a RealType,
  by reducing the list of RealType in RealComposite using a specified function.
  reducer_class: e.g. Math
  reducer_method: e.g. "max", a method that takes two doubles and returns one.
  reducer_method_signature: e.g. "(DD)D", two double arguments, returning a double.
  """
  class_name = "my/CompositeToRealConverterVia_" + reducer_class.getName().replace('.', '_') + '_' + reducer_method
  # Turn e.g. class Math into "java/lang/Math":
  reducer_class_string = reducer_class.getName().replace('.', '/')

  cw = ClassWriter(0)

  cw.visit(52, Opcodes.ACC_PUBLIC + Opcodes.ACC_SUPER, class_name, "<S::Lnet/imglib2/type/numeric/RealType<TS;>;T::Lnet/imglib2/type/numeric/RealType<TT;>;>Ljava/lang/Object;Lnet/imglib2/converter/Converter<Lnet/imglib2/view/composite/RealComposite<TS;>;TT;>;", "java/lang/Object", ["net/imglib2/converter/Converter"])


  mv = cw.visitMethod(Opcodes.ACC_PUBLIC, "<init>", "()V", None, None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitMethodInsn(Opcodes.INVOKESPECIAL, "java/lang/Object", "<init>", "()V", False)
  mv.visitInsn(Opcodes.RETURN)
  mv.visitMaxs(1, 1)
  mv.visitEnd()


  mv = cw.visitMethod(Opcodes.ACC_PUBLIC + Opcodes.ACC_FINAL, "convert", "(Lnet/imglib2/view/composite/RealComposite;Lnet/imglib2/type/numeric/RealType;)V", "(Lnet/imglib2/view/composite/RealComposite<TS;>;TT;)V", None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 2)
  mv.visitMethodInsn(Opcodes.INVOKEINTERFACE, "net/imglib2/type/numeric/RealType", "setZero", "()V", True);
  mv.visitVarInsn(Opcodes.ALOAD, 1)
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "net/imglib2/view/composite/RealComposite", "iterator", "()Ljava/util/Iterator;", False)
  mv.visitVarInsn(Opcodes.ASTORE, 4)
  l0 = Label()
  mv.visitJumpInsn(Opcodes.GOTO, l0)
  l1 = Label()
  mv.visitLabel(l1)
  mv.visitFrame(Opcodes.F_FULL, 5, [class_name, "net/imglib2/view/composite/RealComposite", "net/imglib2/type/numeric/RealType", Opcodes.TOP, "java/util/Iterator"], 0, [])
  mv.visitVarInsn(Opcodes.ALOAD, 4)
  mv.visitMethodInsn(Opcodes.INVOKEINTERFACE, "java/util/Iterator", "next", "()Ljava/lang/Object;", True)
  mv.visitTypeInsn(Opcodes.CHECKCAST, "net/imglib2/type/numeric/RealType")
  mv.visitVarInsn(Opcodes.ASTORE, 3)
  mv.visitVarInsn(Opcodes.ALOAD, 2)
  mv.visitVarInsn(Opcodes.ALOAD, 3)
  mv.visitMethodInsn(Opcodes.INVOKEINTERFACE, "net/imglib2/type/numeric/RealType", "getRealDouble", "()D", True)
  mv.visitVarInsn(Opcodes.ALOAD, 2)
  mv.visitMethodInsn(Opcodes.INVOKEINTERFACE, "net/imglib2/type/numeric/RealType", "getRealDouble", "()D", True)
  mv.visitMethodInsn(Opcodes.INVOKESTATIC, reducer_class_string, reducer_method, reducer_method_signature, False)
  mv.visitMethodInsn(Opcodes.INVOKEINTERFACE, "net/imglib2/type/numeric/RealType", "setReal", "(D)V", True)
  mv.visitLabel(l0)
  mv.visitFrame(Opcodes.F_SAME, 0, None, 0, None)
  mv.visitVarInsn(Opcodes.ALOAD, 4)
  mv.visitMethodInsn(Opcodes.INVOKEINTERFACE, "java/util/Iterator", "hasNext", "()Z", True)
  mv.visitJumpInsn(Opcodes.IFNE, l1)
  mv.visitInsn(Opcodes.RETURN)
  mv.visitMaxs(5, 5)
  mv.visitEnd()


  mv = cw.visitMethod(Opcodes.ACC_PUBLIC + Opcodes.ACC_BRIDGE + Opcodes.ACC_SYNTHETIC, "convert", "(Ljava/lang/Object;Ljava/lang/Object;)V", None, None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitVarInsn(Opcodes.ALOAD, 1)
  mv.visitTypeInsn(Opcodes.CHECKCAST, "net/imglib2/view/composite/RealComposite")
  mv.visitVarInsn(Opcodes.ALOAD, 2)
  mv.visitTypeInsn(Opcodes.CHECKCAST, "net/imglib2/type/numeric/RealType")
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, class_name, "convert", "(Lnet/imglib2/view/composite/RealComposite;Lnet/imglib2/type/numeric/RealType;)V", False)
  mv.visitInsn(Opcodes.RETURN)
  mv.visitMaxs(3, 3)
  mv.visitEnd()

  cw.visitEnd()

  if not classloader:
    classloader = CustomClassLoader()
  return classloader.defineClass(class_name, cw.toByteArray())

