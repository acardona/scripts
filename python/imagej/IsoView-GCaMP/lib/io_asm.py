from org.objectweb.asm import ClassWriter, Opcodes, Label
from java.lang import ClassLoader, Integer
from lib.asm import CustomClassLoader, initClass, initMethod, initMethodObj

def defineDATHandler(classname=None):
  """ Returns the static class DAT_handler with static methods 'deinterleave' and 'toUnsigned'.
      See: scripts/java/asm/my/IO_DAT.java
  """
  if classname is None:
    classname = "asm/io/DAT_handler"

  classWriter = initClass(classname)
  
  methodVisitor = classWriter.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL | Opcodes.ACC_STATIC,
                                          "toUnsigned", "([S)V", None, None)
  methodVisitor.visitCode()
  label0 = Label()
  methodVisitor.visitLabel(label0)
  methodVisitor.visitLineNumber(6, label0)
  methodVisitor.visitIntInsn(Opcodes.SIPUSH, 32767)
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 1)
  label1 = Label()
  methodVisitor.visitLabel(label1)
  methodVisitor.visitLineNumber(7, label1)
  methodVisitor.visitInsn(Opcodes.ICONST_0)
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 2)
  label2 = Label()
  methodVisitor.visitLabel(label2)
  methodVisitor.visitFrame(Opcodes.F_APPEND,2, [Opcodes.INTEGER, Opcodes.INTEGER], 0, None)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 2)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitInsn(Opcodes.ARRAYLENGTH)
  label3 = Label()
  methodVisitor.visitJumpInsn(Opcodes.IF_ICMPGE, label3)
  label4 = Label()
  methodVisitor.visitLabel(label4)
  methodVisitor.visitLineNumber(8, label4)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 2)
  methodVisitor.visitInsn(Opcodes.SALOAD)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 1)
  label5 = Label()
  methodVisitor.visitJumpInsn(Opcodes.IF_ICMPGE, label5)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 2)
  methodVisitor.visitInsn(Opcodes.SALOAD)
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 1)
  methodVisitor.visitLabel(label5)
  methodVisitor.visitLineNumber(7, label5)
  methodVisitor.visitFrame(Opcodes.F_SAME, 0, None, 0, None)
  methodVisitor.visitIincInsn(2, 1)
  methodVisitor.visitJumpInsn(Opcodes.GOTO, label2)
  methodVisitor.visitLabel(label3)
  methodVisitor.visitLineNumber(10, label3)
  methodVisitor.visitFrame(Opcodes.F_CHOP,1, None, 0, None)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 1)
  label6 = Label()
  methodVisitor.visitJumpInsn(Opcodes.IFGE, label6)
  label7 = Label()
  methodVisitor.visitLabel(label7)
  methodVisitor.visitLineNumber(11, label7)
  methodVisitor.visitInsn(Opcodes.ICONST_0)
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 2)
  label8 = Label()
  methodVisitor.visitLabel(label8)
  methodVisitor.visitFrame(Opcodes.F_APPEND,1, [Opcodes.INTEGER], 0, None)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 2)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitInsn(Opcodes.ARRAYLENGTH)
  methodVisitor.visitJumpInsn(Opcodes.IF_ICMPGE, label6)
  label9 = Label()
  methodVisitor.visitLabel(label9)
  methodVisitor.visitLineNumber(12, label9)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 2)
  methodVisitor.visitInsn(Opcodes.DUP2)
  methodVisitor.visitInsn(Opcodes.SALOAD)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 1)
  methodVisitor.visitInsn(Opcodes.ISUB)
  methodVisitor.visitInsn(Opcodes.I2S)
  methodVisitor.visitInsn(Opcodes.SASTORE)
  label10 = Label()
  methodVisitor.visitLabel(label10)
  methodVisitor.visitLineNumber(11, label10)
  methodVisitor.visitIincInsn(2, 1)
  methodVisitor.visitJumpInsn(Opcodes.GOTO, label8)
  methodVisitor.visitLabel(label6)
  methodVisitor.visitLineNumber(15, label6)
  methodVisitor.visitFrame(Opcodes.F_CHOP,1, None, 0, None)
  methodVisitor.visitInsn(Opcodes.RETURN)
  methodVisitor.visitMaxs(4, 3)
  methodVisitor.visitEnd()
  
  
  methodVisitor = classWriter.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL |Opcodes.ACC_STATIC,
                                          "toUnsignedExact", "([S)V", None, None)
  methodVisitor.visitCode()
  label0 = Label()
  methodVisitor.visitLabel(label0)
  methodVisitor.visitLineNumber(18, label0)
  methodVisitor.visitInsn(Opcodes.ICONST_0)
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 1)
  label1 = Label()
  methodVisitor.visitLabel(label1)
  methodVisitor.visitFrame(Opcodes.F_APPEND,1, [Opcodes.INTEGER], 0, None)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 1)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitInsn(Opcodes.ARRAYLENGTH)
  label2 = Label()
  methodVisitor.visitJumpInsn(Opcodes.IF_ICMPGE, label2)
  label3 = Label()
  methodVisitor.visitLabel(label3)
  methodVisitor.visitLineNumber(19, label3)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 1)
  methodVisitor.visitInsn(Opcodes.DUP2)
  methodVisitor.visitInsn(Opcodes.SALOAD)
  methodVisitor.visitIntInsn(Opcodes.SIPUSH, 31768)
  methodVisitor.visitInsn(Opcodes.IADD)
  methodVisitor.visitInsn(Opcodes.I2S)
  methodVisitor.visitInsn(Opcodes.SASTORE)
  label4 = Label()
  methodVisitor.visitLabel(label4)
  methodVisitor.visitLineNumber(18, label4)
  methodVisitor.visitIincInsn(1, 1)
  methodVisitor.visitJumpInsn(Opcodes.GOTO, label1)
  methodVisitor.visitLabel(label2)
  methodVisitor.visitLineNumber(21, label2)
  methodVisitor.visitFrame(Opcodes.F_CHOP,1, None, 0, None)
  methodVisitor.visitInsn(Opcodes.RETURN)
  methodVisitor.visitMaxs(4, 2)
  methodVisitor.visitEnd()

  
  methodVisitor = classWriter.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL | Opcodes.ACC_STATIC,
                                          "deinterleave", "([SII)[[S", None, None)
  methodVisitor.visitCode()
  label0 = Label()
  methodVisitor.visitLabel(label0)
  methodVisitor.visitLineNumber(20, label0)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 2)
  label1 = Label()
  methodVisitor.visitJumpInsn(Opcodes.IFLT, label1)
  label2 = Label()
  methodVisitor.visitLabel(label2)
  methodVisitor.visitLineNumber(22, label2)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitInsn(Opcodes.ARRAYLENGTH)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 1)
  methodVisitor.visitInsn(Opcodes.IDIV)
  methodVisitor.visitIntInsn(Opcodes.NEWARRAY, Opcodes.T_SHORT)
  methodVisitor.visitVarInsn(Opcodes.ASTORE, 3)
  label3 = Label()
  methodVisitor.visitLabel(label3)
  methodVisitor.visitLineNumber(23, label3)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 2)
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 4)
  methodVisitor.visitInsn(Opcodes.ICONST_0)
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 5)
  label4 = Label()
  methodVisitor.visitLabel(label4)
  methodVisitor.visitFrame(Opcodes.F_APPEND,3, ["[S", Opcodes.INTEGER, Opcodes.INTEGER], 0, None)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 4)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitInsn(Opcodes.ARRAYLENGTH)
  label5 = Label()
  methodVisitor.visitJumpInsn(Opcodes.IF_ICMPGE, label5)
  label6 = Label()
  methodVisitor.visitLabel(label6)
  methodVisitor.visitLineNumber(24, label6)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 3)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 5)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 4)
  methodVisitor.visitInsn(Opcodes.SALOAD)
  methodVisitor.visitInsn(Opcodes.SASTORE)
  label7 = Label()
  methodVisitor.visitLabel(label7)
  methodVisitor.visitLineNumber(23, label7)
  methodVisitor.visitIincInsn(5, 1)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 4)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 1)
  methodVisitor.visitInsn(Opcodes.IADD)
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 4)
  methodVisitor.visitJumpInsn(Opcodes.GOTO, label4)
  methodVisitor.visitLabel(label5)
  methodVisitor.visitLineNumber(26, label5)
  methodVisitor.visitFrame(Opcodes.F_CHOP,2, None, 0, None)
  methodVisitor.visitInsn(Opcodes.ICONST_1)
  methodVisitor.visitTypeInsn(Opcodes.ANEWARRAY, "[S")
  methodVisitor.visitInsn(Opcodes.DUP)
  methodVisitor.visitInsn(Opcodes.ICONST_0)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 3)
  methodVisitor.visitInsn(Opcodes.AASTORE)
  methodVisitor.visitInsn(Opcodes.ARETURN)
  methodVisitor.visitLabel(label1)
  methodVisitor.visitLineNumber(28, label1)
  methodVisitor.visitFrame(Opcodes.F_CHOP,1, None, 0, None)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 1)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitInsn(Opcodes.ARRAYLENGTH)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 1)
  methodVisitor.visitInsn(Opcodes.IDIV)
  methodVisitor.visitMultiANewArrayInsn("[[S", 2)
  methodVisitor.visitVarInsn(Opcodes.ASTORE, 3)
  label8 = Label()
  methodVisitor.visitLabel(label8)
  methodVisitor.visitLineNumber(29, label8)
  methodVisitor.visitInsn(Opcodes.ICONST_0)
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 4)
  methodVisitor.visitInsn(Opcodes.ICONST_0)
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 5)
  label9 = Label()
  methodVisitor.visitLabel(label9)
  methodVisitor.visitFrame(Opcodes.F_APPEND,3, ["[[S", Opcodes.INTEGER, Opcodes.INTEGER], 0, None)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 4)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitInsn(Opcodes.ARRAYLENGTH)
  label10 = Label()
  methodVisitor.visitJumpInsn(Opcodes.IF_ICMPGE, label10)
  label11 = Label()
  methodVisitor.visitLabel(label11)
  methodVisitor.visitLineNumber(30, label11)
  methodVisitor.visitInsn(Opcodes.ICONST_0)
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 6)
  label12 = Label()
  methodVisitor.visitLabel(label12)
  methodVisitor.visitFrame(Opcodes.F_APPEND,1, [Opcodes.INTEGER], 0, None)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 6)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 1)
  label13 = Label()
  methodVisitor.visitJumpInsn(Opcodes.IF_ICMPGE, label13)
  label14 = Label()
  methodVisitor.visitLabel(label14)
  methodVisitor.visitLineNumber(31, label14)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 3)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 6)
  methodVisitor.visitInsn(Opcodes.AALOAD)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 5)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 4)
  methodVisitor.visitInsn(Opcodes.SALOAD)
  methodVisitor.visitInsn(Opcodes.SASTORE)
  label15 = Label()
  methodVisitor.visitLabel(label15)
  methodVisitor.visitLineNumber(30, label15)
  methodVisitor.visitIincInsn(6, 1)
  methodVisitor.visitIincInsn(4, 1)
  methodVisitor.visitJumpInsn(Opcodes.GOTO, label12)
  methodVisitor.visitLabel(label13)
  methodVisitor.visitLineNumber(29, label13)
  methodVisitor.visitFrame(Opcodes.F_CHOP,1, None, 0, None)
  methodVisitor.visitIincInsn(5, 1)
  methodVisitor.visitJumpInsn(Opcodes.GOTO, label9)
  methodVisitor.visitLabel(label10)
  methodVisitor.visitLineNumber(34, label10)
  methodVisitor.visitFrame(Opcodes.F_CHOP,2, None, 0, None)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 3)
  methodVisitor.visitInsn(Opcodes.ARETURN)
  methodVisitor.visitMaxs(4, 7)
  methodVisitor.visitEnd()
  
  
  methodVisitor = classWriter.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_FINAL | Opcodes.ACC_STATIC,
                                          "applyScale", "([SFF)V", None, None)
  methodVisitor.visitCode()
  label0 = Label()
  methodVisitor.visitLabel(label0)
  methodVisitor.visitLineNumber(44, label0)
  methodVisitor.visitInsn(Opcodes.ICONST_0)
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 3)
  label1 = Label()
  methodVisitor.visitLabel(label1)
  methodVisitor.visitFrame(Opcodes.F_APPEND,1, [Opcodes.INTEGER], 0, None)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 3)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitInsn(Opcodes.ARRAYLENGTH)
  label2 = Label()
  methodVisitor.visitJumpInsn(Opcodes.IF_ICMPGE, label2)
  label3 = Label()
  methodVisitor.visitLabel(label3)
  methodVisitor.visitLineNumber(45, label3)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 3)
  methodVisitor.visitInsn(Opcodes.SALOAD)
  methodVisitor.visitInsn(Opcodes.I2F)
  methodVisitor.visitVarInsn(Opcodes.FLOAD, 1)
  methodVisitor.visitInsn(Opcodes.FSUB)
  methodVisitor.visitVarInsn(Opcodes.FLOAD, 2)
  methodVisitor.visitInsn(Opcodes.FMUL)
  methodVisitor.visitVarInsn(Opcodes.FSTORE, 4)
  label4 = Label()
  methodVisitor.visitLabel(label4)
  methodVisitor.visitLineNumber(46, label4)
  methodVisitor.visitVarInsn(Opcodes.FLOAD, 4)
  methodVisitor.visitMethodInsn(Opcodes.INVOKESTATIC, "java/lang/Math", "round", "(F)I", False)
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 5)
  label5 = Label()
  methodVisitor.visitLabel(label5)
  methodVisitor.visitLineNumber(47, label5)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 5)
  label6 = Label()
  methodVisitor.visitJumpInsn(Opcodes.IFGE, label6)
  methodVisitor.visitInsn(Opcodes.ICONST_0)
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 5)
  label7 = Label()
  methodVisitor.visitJumpInsn(Opcodes.GOTO, label7)
  methodVisitor.visitLabel(label6)
  methodVisitor.visitLineNumber(48, label6)
  methodVisitor.visitFrame(Opcodes.F_APPEND,2, [Opcodes.FLOAT, Opcodes.INTEGER], 0, None)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 5)
  methodVisitor.visitLdcInsn(Integer(65535))
  methodVisitor.visitJumpInsn(Opcodes.IF_ICMPLE, label7)
  methodVisitor.visitLdcInsn(Integer(65535))
  methodVisitor.visitVarInsn(Opcodes.ISTORE, 5)
  methodVisitor.visitLabel(label7)
  methodVisitor.visitLineNumber(49, label7)
  methodVisitor.visitFrame(Opcodes.F_SAME, 0, None, 0, None)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 3)
  methodVisitor.visitVarInsn(Opcodes.ILOAD, 5)
  methodVisitor.visitInsn(Opcodes.I2S)
  methodVisitor.visitInsn(Opcodes.SASTORE)
  label8 = Label()
  methodVisitor.visitLabel(label8)
  methodVisitor.visitLineNumber(44, label8)
  methodVisitor.visitIincInsn(3, 1)
  methodVisitor.visitJumpInsn(Opcodes.GOTO, label1)
  methodVisitor.visitLabel(label2)
  methodVisitor.visitLineNumber(51, label2)
  methodVisitor.visitFrame(Opcodes.F_CHOP,3, None, 0, None)
  methodVisitor.visitInsn(Opcodes.RETURN)
  methodVisitor.visitMaxs(3, 6)
  methodVisitor.visitEnd()
  
  
  classWriter.visitEnd()
  loader = CustomClassLoader()
  DAT_handler = loader.defineClass(classname, classWriter.toByteArray())
  return DAT_handler


DAT_handler = defineDATHandler()

