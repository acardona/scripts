from org.objectweb.asm import ClassWriter, Opcodes, Type
from java.lang import Object
from net.imglib2.converter.readwrite import SamplerConverter
from net.imglib2 import Sampler
from net.imglib2.type.numeric.integer import UnsignedByteType
from net.imglib2.type.numeric.real import FloatType
from net.imglib2.img.basictypeaccess import FloatAccess
from itertools import imap, repeat

import sys
sys.path.append("/home/albert/lab/scripts/python/imagej/IsoView-GCaMP/")
from lib.asm import initClass, initMethod, initConstructor, CustomClassLoader
from lib.util import timeit

# A SamplerConverter in asm

# First the my/UnsignedByteToFloatAccess
facc = initClass("my/UnsignedByteToFloatAccess",
                 access=Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL,
                 interfaces=[FloatAccess],
                 interfaces_parameters={FloatAccess: ['']},
                 with_default_constructor=False)

# private final "sampler" field
f = facc.visitField(Opcodes.ACC_PRIVATE | Opcodes.ACC_FINAL,
                    "sampler",
                    "L%s;" % Type.getInternalName(Sampler),
                    "L%s<+L%s;>;" % tuple(imap(Type.getInternalName, (Sampler, UnsignedByteType))),
                    None)

# The constructor has to initialize the field "sampler"
c = initConstructor(facc,
                    descriptor="(Lnet/imglib2/Sampler;)V",
                    signature="(Lnet/imglib2/Sampler<+Lnet/imglib2/type/numeric/integer/UnsignedByteType;>;)V")
# The 'c' constructor already invoked <init>
# Now onto the rest of the constructor body:
c.visitVarInsn(Opcodes.ALOAD, 0)
c.visitVarInsn(Opcodes.ALOAD, 1)
field = {"classname": "my/UnsignedByteToFloatAccess",
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
gv.visitTypeInsn(Opcodes.CHECKCAST, Type.getInternalName(UnsignedByteType))
gv.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                  Type.getInternalName(UnsignedByteType),
                  "getRealFloat",
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
sv.visitTypeInsn(Opcodes.CHECKCAST, Type.getInternalName(UnsignedByteType))
sv.visitVarInsn(Opcodes.FLOAD, 2)
sv.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                  Type.getInternalName(UnsignedByteType),
                  "setReal",
                  "(F)V",
                  False)
sv.visitInsn(Opcodes.RETURN)
sv.visitMaxs(2, 3)
sv.visitEnd()



cw = initClass("my/UnsignedByteToFloatSamplerConverter",
               interfaces=[SamplerConverter],
               interfaces_parameters={SamplerConverter: [UnsignedByteType, FloatType]})

# In the signature, the + sign is for e.g. <? extends UnignedByteType>
# Here, the signature is the same as the descriptor, but with parameter types
# descriptor="(Lnet/imglib2/Sampler;)Lnet/imglib2/type/numeric/real/FloatType;"
# signature="(Lnet/imglib2/Sampler<+Lnet/imglib2/type/numeric/integer/UnsignedByteType;>;)Lnet/imglib2/type/numeric/real/FloatType;",
m = initMethod(cw, "convert",
               argument_classes=[Sampler],
               argument_parameters=[UnsignedByteType],
               argument_prefixes=['+'], # '+' means: <? extends UnsignedByteType>
               return_type=FloatType)

m.visitCode()
m.visitTypeInsn(Opcodes.NEW, Type.getInternalName(FloatType))
m.visitInsn(Opcodes.DUP)
m.visitTypeInsn(Opcodes.NEW, "my/UnsignedByteToFloatAccess")
m.visitInsn(Opcodes.DUP)
m.visitVarInsn(Opcodes.ALOAD, 1)
m.visitMethodInsn(Opcodes.INVOKESPECIAL, # Create new my.UnsignedByteToFloatAccess
                  "my/UnsignedByteToFloatAccess",
                  "<init>", # constructor
                  "(L%s;)V" % Type.getInternalName(Sampler),
                  False)
m.visitMethodInsn(Opcodes.INVOKESPECIAL, # Create new FloatType with the new my.UnsignedByteToFloatAccess as argument
                  Type.getInternalName(FloatType),
                  "<init>", # constructor
                  "(L%s;)V" % Type.getInternalName(FloatAccess),
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
                       "my/UnsignedByteToFloatSamplerConverter",
                       "convert",
                       "(L%s;)L%s;" % tuple(imap(Type.getInternalName, (Sampler, FloatType))), # descriptor
                       False)
bridge.visitInsn(Opcodes.ARETURN)
bridge.visitMaxs(2, 2)
bridge.visitEnd()



# Load the facc and cw classes
loader = CustomClassLoader()
accessClass = loader.defineClass("my/UnsignedByteToFloatAccess", facc.toByteArray())
samplerClass = loader.defineClass("my/UnsignedByteToFloatSamplerConverter", cw.toByteArray())

# Test SamplerConverter:
from net.imglib2.img.array import ArrayImgs
from net.imglib2.converter import Converters
from net.imglib2.util import ImgUtil
from net.imglib2.img import ImgView

dimensions = [100, 100, 100]
img1 = ArrayImgs.unsignedBytes(dimensions)
c = img1.cursor()
while c.hasNext():
  c.next().setOne()
img2 = ArrayImgs.floats(dimensions)

def testASM():
  ImgUtil.copy(ImgView.wrap(Converters.convertRandomAccessibleIterableInterval(img1, samplerClass.newInstance()), img1.factory()), img2)

timeit(20, testASM)

class UnsignedByteToFloatAccess(FloatAccess):
  def __init__(self, sampler):
    self.sampler = sampler
  def getValue(self, index):
    return self.sampler.get().getRealFloat()
  def setValue(self, index, value):
    self.sampler.get().setReal(value)

class UnsignedByteToFloatSamplerConverter(SamplerConverter):
  def convert(self, sampler):
    return FloatType(UnsignedByteToFloatAccess(sampler))

def testJython():
  ImgUtil.copy(ImgView.wrap(Converters.convertRandomAccessibleIterableInterval(img1, UnsignedByteToFloatSamplerConverter()), img1.factory()), img2)

timeit(20, testJython)

# ASM: 31 ms
# Jython: 755 ms   -- a factor of 25x or so slowdown
