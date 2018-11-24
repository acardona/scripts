from org.objectweb.asm import ClassWriter, Opcodes, Type
from java.lang import Object, Class
from net.imglib2.converter.readwrite import SamplerConverter
from net.imglib2 import Sampler
from itertools import imap
# Local lib
from lib.asm import initClass, initMethod, initConstructor, CustomClassLoader


def createSamplerConverter(fromType,
                           toType,
                           classname="",
                           toAccess=None,
                           fromMethod="getRealFloat",
                           toMethod="setReal"):
  """ A SamplerConverter in asm for high-performance (25x jython's speed).

      fromType: the source type to convert like e.g. UnsignedByteType.
      toType: the target type, like e.g. FloatType.
      classname: optional, the fully qualified name for the new class implementing SamplerConverter.
      fromMethod: the name of the fromType class method to use for getting its value.
                  Defaults to "getRealFloat" from the RealType interface.
      toMethod: the name of the toType class method for setting the value.
                Defaults to "setReal" from the RealType interface.
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
                   interfaces_parameters={toAccess: ['']},
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
                  descriptor="(I)F")
  gv.visitVarInsn(Opcodes.ALOAD, 0)
  gv.visitFieldInsn(Opcodes.GETFIELD, field["classname"], field["name"], field["descriptor"])
  gv.visitMethodInsn(Opcodes.INVOKEINTERFACE,
                    Type.getInternalName(Sampler),
                    "get",
                    "()L%s;" % Type.getInternalName(Object), # isn't this weird? Why Object?
                    True)
  gv.visitTypeInsn(Opcodes.CHECKCAST, Type.getInternalName(fromType))
  gv.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                    Type.getInternalName(fromType),
                    fromMethod, # e.g. getRealFloat
                    "()F",
                    False)
  gv.visitInsn(Opcodes.FRETURN) # native float return
  gv.visitMaxs(1, 2)
  gv.visitEnd()

  sv = initMethod(facc,
                  "setValue",
                  access=Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL,
                  descriptor="(IF)V")
  sv.visitVarInsn(Opcodes.ALOAD, 0)
  sv.visitFieldInsn(Opcodes.GETFIELD, field["classname"], field["name"], field["descriptor"])
  sv.visitMethodInsn(Opcodes.INVOKEINTERFACE,
                    Type.getInternalName(Sampler),
                    "get",
                    "()L%s;" % Type.getInternalName(Object), # isn't this weird? Why Object?
                    True)
  sv.visitTypeInsn(Opcodes.CHECKCAST, Type.getInternalName(fromType))
  sv.visitVarInsn(Opcodes.FLOAD, 2)
  sv.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                    Type.getInternalName(fromType),
                    toMethod, # e.g. setReal
                    "(F)V",
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

  return samplerClass.newInstance()

