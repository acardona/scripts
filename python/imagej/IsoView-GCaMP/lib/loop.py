from org.objectweb.asm import ClassWriter, Opcodes, Label
from java.lang import ClassLoader
from lib.asm import CustomClassLoader

def defineBiConsumerTypeSet(imglib2Type, classname=None):
  """ 
      A class to use in e.g. an ImgLib2 LoopBuilder.setImages(img1, img2).forEachPixel(<instance of this BiConsumer class>)
      where both image are of the same Type.
  """
  typeClassname = imglib2Type.getName().replace(".", "/")
  
  if classname is None:
    classname = "asm/loop/BiConsumer_%s_set" % imglib2Type.getSimpleName()
  
  classWriter = ClassWriter(0)
  classWriter.visit(Opcodes.V1_8,
                    Opcodes.ACC_PUBLIC | Opcodes.ACC_SUPER,
                    classname,
                    "<T::L%s<TT;>;>Ljava/lang/Object;Ljava/util/function/BiConsumer<TT;TT;>;" % typeClassname,
                    "java/lang/Object",
                    ["java/util/function/BiConsumer"])

  # Constructor
  methodVisitor = classWriter.visitMethod(Opcodes.ACC_PUBLIC, "<init>", "()V", None, None)
  methodVisitor.visitCode()
  label0 = Label()
  methodVisitor.visitLabel(label0)
  methodVisitor.visitLineNumber(5, label0)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitMethodInsn(Opcodes.INVOKESPECIAL, "java/lang/Object", "<init>", "()V", False)
  methodVisitor.visitInsn(Opcodes.RETURN)
  methodVisitor.visitMaxs(1, 1)
  methodVisitor.visitEnd()

  # BiConsumer.accept method implementation with body Type.set(Type)
  methodVisitor = classWriter.visitMethod(Opcodes.ACC_PUBLIC, "accept", "(L%s;L%s;)V" % (typeClassname, typeClassname), "(TT;TT;)V", None)
  methodVisitor.visitCode()
  label0 = Label()
  methodVisitor.visitLabel(label0)
  methodVisitor.visitLineNumber(8, label0)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 2)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 1)
  methodVisitor.visitMethodInsn(Opcodes.INVOKEVIRTUAL, typeClassname, "set", "(L%s;)V" % typeClassname, False)
  label1 = Label()
  methodVisitor.visitLabel(label1)
  methodVisitor.visitLineNumber(9, label1)
  methodVisitor.visitInsn(Opcodes.RETURN)
  methodVisitor.visitMaxs(2, 3)
  methodVisitor.visitEnd()

  # BiConsumer.accept method with Object,Object arguments
  methodVisitor = classWriter.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_BRIDGE | Opcodes.ACC_SYNTHETIC, "accept", "(Ljava/lang/Object;Ljava/lang/Object;)V", None, None)
  methodVisitor.visitCode()
  label0 = Label()
  methodVisitor.visitLabel(label0)
  methodVisitor.visitLineNumber(5, label0)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 1)
  methodVisitor.visitTypeInsn(Opcodes.CHECKCAST, typeClassname)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 2)
  methodVisitor.visitTypeInsn(Opcodes.CHECKCAST, typeClassname)
  methodVisitor.visitMethodInsn(Opcodes.INVOKEVIRTUAL, classname, "accept", "(L%s;L%s;)V" % (typeClassname, typeClassname), False)
  methodVisitor.visitInsn(Opcodes.RETURN)
  methodVisitor.visitMaxs(3, 3)
  methodVisitor.visitEnd()

  classWriter.visitEnd()
  
  loader = CustomClassLoader()
  biconsumerClass = loader.defineClass(classname, classWriter.toByteArray())
  print biconsumerClass
  return biconsumerClass


def createBiConsumerTypeSet(*args, **kwargs):
  """
  Example use: copy pixel-wise one image into another of the same type
  bypassing the slowness of Jython loops:
  
  img1 = ArrayImgs.floats([512, 512])
  # ... add data to img1
  # Now copy img1 into img2
  img2 = ArrayImgs.floats(Intervals.dimensionsAsLongArray(img1)) # same dimensions as img1
  
  copier = createBiConsumerTypeSet(type(img1.randomAccess().get())) # takes the class of the pixel type as argument
  
  LoopBuilder.setImages(img1, img2).forEachPixel(copier)
  
  # Or multithreaded:
  LoopBuilder.setImages(img1, img2).multiThreaded().forEachPixel(copier)
  """
  return defineBiConsumerTypeSet(*args, **kwargs).newInstance()

