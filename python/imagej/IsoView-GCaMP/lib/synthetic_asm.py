from org.objectweb.asm import ClassWriter, Label, Opcodes
from lib.asm import CustomClassLoader

def makeNativeRadiusBounds(classloader=None):
  # Class my/RadiusBounds
  cw = ClassWriter(0)

  cw.visit(52, Opcodes.ACC_PUBLIC + Opcodes.ACC_FINAL + Opcodes.ACC_SUPER, "my/RadiusBounds",
          "<T::Lnet/imglib2/type/numeric/RealType<TT;>;>Lnet/imglib2/RealPoint;Lnet/imglib2/RealRandomAccess<TT;>;",
          "net/imglib2/RealPoint", ["net/imglib2/RealRandomAccess"])

  fv = cw.visitField(Opcodes.ACC_PRIVATE + Opcodes.ACC_FINAL, "search", "Lnet/imglib2/neighborsearch/NearestNeighborSearchOnKDTree;", "Lnet/imglib2/neighborsearch/NearestNeighborSearchOnKDTree<TT;>;", None)
  fv.visitEnd()

  fv = cw.visitField(Opcodes.ACC_PRIVATE + Opcodes.ACC_FINAL, "kdtree", "Lnet/imglib2/KDTree;", "Lnet/imglib2/KDTree<TT;>;", None)
  fv.visitEnd()

  fv = cw.visitField(Opcodes.ACC_PRIVATE + Opcodes.ACC_FINAL, "radius", "D", None, None)
  fv.visitEnd()

  fv = cw.visitField(Opcodes.ACC_PRIVATE + Opcodes.ACC_FINAL, "radius_squared", "D", None, None)
  fv.visitEnd()

  fv = cw.visitField(Opcodes.ACC_PRIVATE + Opcodes.ACC_FINAL, "inside", "Lnet/imglib2/type/numeric/RealType;", "TT;", None)
  fv.visitEnd()

  fv = cw.visitField(Opcodes.ACC_PRIVATE + Opcodes.ACC_FINAL, "outside", "Lnet/imglib2/type/numeric/RealType;", "TT;", None)
  fv.visitEnd()

  mv = cw.visitMethod(Opcodes.ACC_PUBLIC, "<init>", "(ILnet/imglib2/KDTree;DLnet/imglib2/type/numeric/RealType;Lnet/imglib2/type/numeric/RealType;)V", "(ILnet/imglib2/KDTree<TT;>;DTT;TT;)V", None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitVarInsn(Opcodes.ILOAD, 1)
  mv.visitMethodInsn(Opcodes.INVOKESPECIAL, "net/imglib2/RealPoint", "<init>", "(I)V", False)
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitVarInsn(Opcodes.ALOAD, 2)
  mv.visitFieldInsn(Opcodes.PUTFIELD, "my/RadiusBounds", "kdtree", "Lnet/imglib2/KDTree;")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitVarInsn(Opcodes.DLOAD, 3)
  mv.visitFieldInsn(Opcodes.PUTFIELD, "my/RadiusBounds", "radius", "D")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitVarInsn(Opcodes.DLOAD, 3)
  mv.visitVarInsn(Opcodes.DLOAD, 3)
  mv.visitInsn(Opcodes.DMUL)
  mv.visitFieldInsn(Opcodes.PUTFIELD, "my/RadiusBounds", "radius_squared", "D")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitVarInsn(Opcodes.ALOAD, 5)
  mv.visitFieldInsn(Opcodes.PUTFIELD, "my/RadiusBounds", "inside", "Lnet/imglib2/type/numeric/RealType;")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitVarInsn(Opcodes.ALOAD, 6)
  mv.visitFieldInsn(Opcodes.PUTFIELD, "my/RadiusBounds", "outside", "Lnet/imglib2/type/numeric/RealType;")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitTypeInsn(Opcodes.NEW, "net/imglib2/neighborsearch/NearestNeighborSearchOnKDTree")
  mv.visitInsn(Opcodes.DUP)
  mv.visitVarInsn(Opcodes.ALOAD, 2)
  mv.visitMethodInsn(Opcodes.INVOKESPECIAL, "net/imglib2/neighborsearch/NearestNeighborSearchOnKDTree", "<init>", "(Lnet/imglib2/KDTree;)V", False)
  mv.visitFieldInsn(Opcodes.PUTFIELD, "my/RadiusBounds", "search", "Lnet/imglib2/neighborsearch/NearestNeighborSearchOnKDTree;")
  mv.visitInsn(Opcodes.RETURN)
  mv.visitMaxs(5, 7)
  mv.visitEnd()

  mv = cw.visitMethod(Opcodes.ACC_PUBLIC, "get", "()Lnet/imglib2/type/numeric/RealType;", "()TT;", None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBounds", "search", "Lnet/imglib2/neighborsearch/NearestNeighborSearchOnKDTree;")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "net/imglib2/neighborsearch/NearestNeighborSearchOnKDTree", "search", "(Lnet/imglib2/RealLocalizable;)V", False)
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBounds", "search", "Lnet/imglib2/neighborsearch/NearestNeighborSearchOnKDTree;")
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "net/imglib2/neighborsearch/NearestNeighborSearchOnKDTree", "getSquareDistance", "()D", False)
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBounds", "radius_squared", "D")
  mv.visitInsn(Opcodes.DCMPG)
  l0 = Label()
  mv.visitJumpInsn(Opcodes.IFGE, l0)
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBounds", "inside", "Lnet/imglib2/type/numeric/RealType;")
  mv.visitInsn(Opcodes.ARETURN)
  mv.visitLabel(l0)
  mv.visitFrame(Opcodes.F_SAME, 0, None, 0, None)
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBounds", "outside", "Lnet/imglib2/type/numeric/RealType;")
  mv.visitInsn(Opcodes.ARETURN)
  mv.visitMaxs(4, 1)
  mv.visitEnd()

  mv = cw.visitMethod(Opcodes.ACC_PUBLIC, "copy", "()Lnet/imglib2/RealRandomAccess;", "()Lnet/imglib2/RealRandomAccess<TT;>;", None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "my/RadiusBounds", "copyRealRandomAccess", "()Lnet/imglib2/RealRandomAccess;", False)
  mv.visitInsn(Opcodes.ARETURN)
  mv.visitMaxs(1, 1)
  mv.visitEnd()

  mv = cw.visitMethod(Opcodes.ACC_PUBLIC, "copyRealRandomAccess", "()Lnet/imglib2/RealRandomAccess;", "()Lnet/imglib2/RealRandomAccess<TT;>;", None)
  mv.visitCode()
  mv.visitTypeInsn(Opcodes.NEW, "my/RadiusBounds")
  mv.visitInsn(Opcodes.DUP)
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "my/RadiusBounds", "numDimensions", "()I", False)
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBounds", "kdtree", "Lnet/imglib2/KDTree;")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBounds", "radius", "D")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBounds", "inside", "Lnet/imglib2/type/numeric/RealType;")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBounds", "outside", "Lnet/imglib2/type/numeric/RealType;")
  mv.visitMethodInsn(Opcodes.INVOKESPECIAL, "my/RadiusBounds", "<init>", "(ILnet/imglib2/KDTree;DLnet/imglib2/type/numeric/RealType;Lnet/imglib2/type/numeric/RealType;)V", False)
  mv.visitInsn(Opcodes.ARETURN)
  mv.visitMaxs(8, 1)
  mv.visitEnd()

  mv = cw.visitMethod(Opcodes.ACC_PUBLIC + Opcodes.ACC_BRIDGE + Opcodes.ACC_SYNTHETIC, "copy", "()Lnet/imglib2/Sampler;", None, None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "my/RadiusBounds", "copy", "()Lnet/imglib2/RealRandomAccess;", False)
  mv.visitInsn(Opcodes.ARETURN)
  mv.visitMaxs(1, 1)
  mv.visitEnd()

  mv = cw.visitMethod(Opcodes.ACC_PUBLIC + Opcodes.ACC_BRIDGE + Opcodes.ACC_SYNTHETIC, "get", "()Ljava/lang/Object;", None, None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "my/RadiusBounds", "get", "()Lnet/imglib2/type/numeric/RealType;", False)
  mv.visitInsn(Opcodes.ARETURN)
  mv.visitMaxs(1, 1)
  mv.visitEnd()

  cw.visitEnd()

  if not classloader:
    classloader = CustomClassLoader()
  return classloader.defineClass("my/RadiusBounds", cw.toByteArray())



def makeNativeRadiusBoundsEach(classloader=None):
  """ Like RadiusBoundsEach, but each RealPoint can have its own value."""
  #class my/RadiusBoundsEach
  cw = ClassWriter(0)

  cw.visit(52, Opcodes.ACC_PUBLIC + Opcodes.ACC_FINAL + Opcodes.ACC_SUPER, "my/RadiusBoundsEach", "<T::Lnet/imglib2/type/numeric/RealType<TT;>;>Lnet/imglib2/RealPoint;Lnet/imglib2/RealRandomAccess<TT;>;", "net/imglib2/RealPoint", ["net/imglib2/RealRandomAccess"])


  fv = cw.visitField(Opcodes.ACC_PRIVATE + Opcodes.ACC_FINAL, "search", "Lnet/imglib2/neighborsearch/NearestNeighborSearchOnKDTree;", "Lnet/imglib2/neighborsearch/NearestNeighborSearchOnKDTree<TT;>;", None)
  fv.visitEnd()


  fv = cw.visitField(Opcodes.ACC_PRIVATE + Opcodes.ACC_FINAL, "kdtree", "Lnet/imglib2/KDTree;", "Lnet/imglib2/KDTree<TT;>;", None)
  fv.visitEnd()


  fv = cw.visitField(Opcodes.ACC_PRIVATE + Opcodes.ACC_FINAL, "radius", "D", None, None)
  fv.visitEnd()


  fv = cw.visitField(Opcodes.ACC_PRIVATE + Opcodes.ACC_FINAL, "radius_squared", "D", None, None)
  fv.visitEnd()


  fv = cw.visitField(Opcodes.ACC_PRIVATE + Opcodes.ACC_FINAL, "outside", "Lnet/imglib2/type/numeric/RealType;", "TT;", None)
  fv.visitEnd()


  mv = cw.visitMethod(Opcodes.ACC_PUBLIC, "<init>", "(ILnet/imglib2/KDTree;DLnet/imglib2/type/numeric/RealType;)V", "(ILnet/imglib2/KDTree<TT;>;DTT;)V", None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitVarInsn(Opcodes.ILOAD, 1)
  mv.visitMethodInsn(Opcodes.INVOKESPECIAL, "net/imglib2/RealPoint", "<init>", "(I)V", False)
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitVarInsn(Opcodes.ALOAD, 2)
  mv.visitFieldInsn(Opcodes.PUTFIELD, "my/RadiusBoundsEach", "kdtree", "Lnet/imglib2/KDTree;")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitVarInsn(Opcodes.DLOAD, 3)
  mv.visitFieldInsn(Opcodes.PUTFIELD, "my/RadiusBoundsEach", "radius", "D")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitVarInsn(Opcodes.DLOAD, 3)
  mv.visitVarInsn(Opcodes.DLOAD, 3)
  mv.visitInsn(Opcodes.DMUL)
  mv.visitFieldInsn(Opcodes.PUTFIELD, "my/RadiusBoundsEach", "radius_squared", "D")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitVarInsn(Opcodes.ALOAD, 5)
  mv.visitFieldInsn(Opcodes.PUTFIELD, "my/RadiusBoundsEach", "outside", "Lnet/imglib2/type/numeric/RealType;")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitTypeInsn(Opcodes.NEW, "net/imglib2/neighborsearch/NearestNeighborSearchOnKDTree")
  mv.visitInsn(Opcodes.DUP)
  mv.visitVarInsn(Opcodes.ALOAD, 2)
  mv.visitMethodInsn(Opcodes.INVOKESPECIAL, "net/imglib2/neighborsearch/NearestNeighborSearchOnKDTree", "<init>", "(Lnet/imglib2/KDTree;)V", False)
  mv.visitFieldInsn(Opcodes.PUTFIELD, "my/RadiusBoundsEach", "search", "Lnet/imglib2/neighborsearch/NearestNeighborSearchOnKDTree;")
  mv.visitInsn(Opcodes.RETURN)
  mv.visitMaxs(5, 6)
  mv.visitEnd()


  mv = cw.visitMethod(Opcodes.ACC_PUBLIC, "get", "()Lnet/imglib2/type/numeric/RealType;", "()TT;", None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBoundsEach", "search", "Lnet/imglib2/neighborsearch/NearestNeighborSearchOnKDTree;")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "net/imglib2/neighborsearch/NearestNeighborSearchOnKDTree", "search", "(Lnet/imglib2/RealLocalizable;)V", False)
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBoundsEach", "search", "Lnet/imglib2/neighborsearch/NearestNeighborSearchOnKDTree;")
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "net/imglib2/neighborsearch/NearestNeighborSearchOnKDTree", "getSquareDistance", "()D", False)
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBoundsEach", "radius_squared", "D")
  mv.visitInsn(Opcodes.DCMPG)
  l0 = Label()
  mv.visitJumpInsn(Opcodes.IFGE, l0)
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBoundsEach", "search", "Lnet/imglib2/neighborsearch/NearestNeighborSearchOnKDTree;")
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "net/imglib2/neighborsearch/NearestNeighborSearchOnKDTree", "getSampler", "()Lnet/imglib2/Sampler;", False)
  mv.visitMethodInsn(Opcodes.INVOKEINTERFACE, "net/imglib2/Sampler", "get", "()Ljava/lang/Object;", True)
  mv.visitTypeInsn(Opcodes.CHECKCAST, "net/imglib2/type/numeric/RealType")
  mv.visitInsn(Opcodes.ARETURN)
  mv.visitLabel(l0)
  mv.visitFrame(Opcodes.F_SAME, 0, None, 0, None)
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBoundsEach", "outside", "Lnet/imglib2/type/numeric/RealType;")
  mv.visitInsn(Opcodes.ARETURN)
  mv.visitMaxs(4, 1)
  mv.visitEnd()


  mv = cw.visitMethod(Opcodes.ACC_PUBLIC, "copy", "()Lnet/imglib2/RealRandomAccess;", "()Lnet/imglib2/RealRandomAccess<TT;>;", None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "my/RadiusBoundsEach", "copyRealRandomAccess", "()Lmy/RadiusBoundsEach;", False)
  mv.visitInsn(Opcodes.ARETURN)
  mv.visitMaxs(1, 1)
  mv.visitEnd()


  mv = cw.visitMethod(Opcodes.ACC_PUBLIC, "copyRealRandomAccess", "()Lmy/RadiusBoundsEach;", "()Lmy/RadiusBoundsEach<TT;>;", None)
  mv.visitCode()
  mv.visitTypeInsn(Opcodes.NEW, "my/RadiusBoundsEach")
  mv.visitInsn(Opcodes.DUP)
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "my/RadiusBoundsEach", "numDimensions", "()I", False)
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBoundsEach", "kdtree", "Lnet/imglib2/KDTree;")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBoundsEach", "radius", "D")
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitFieldInsn(Opcodes.GETFIELD, "my/RadiusBoundsEach", "outside", "Lnet/imglib2/type/numeric/RealType;")
  mv.visitMethodInsn(Opcodes.INVOKESPECIAL, "my/RadiusBoundsEach", "<init>", "(ILnet/imglib2/KDTree;DLnet/imglib2/type/numeric/RealType;)V", False)
  mv.visitInsn(Opcodes.ARETURN)
  mv.visitMaxs(7, 1)
  mv.visitEnd()


  mv = cw.visitMethod(Opcodes.ACC_PUBLIC + Opcodes.ACC_BRIDGE + Opcodes.ACC_SYNTHETIC, "copyRealRandomAccess", "()Lnet/imglib2/RealRandomAccess;", None, None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "my/RadiusBoundsEach", "copyRealRandomAccess", "()Lmy/RadiusBoundsEach;", False)
  mv.visitInsn(Opcodes.ARETURN)
  mv.visitMaxs(1, 1)
  mv.visitEnd()


  mv = cw.visitMethod(Opcodes.ACC_PUBLIC + Opcodes.ACC_BRIDGE + Opcodes.ACC_SYNTHETIC, "copy", "()Lnet/imglib2/Sampler;", None, None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "my/RadiusBoundsEach", "copy", "()Lnet/imglib2/RealRandomAccess;", False)
  mv.visitInsn(Opcodes.ARETURN)
  mv.visitMaxs(1, 1)
  mv.visitEnd()


  mv = cw.visitMethod(Opcodes.ACC_PUBLIC + Opcodes.ACC_BRIDGE + Opcodes.ACC_SYNTHETIC, "get", "()Ljava/lang/Object;", None, None)
  mv.visitCode()
  mv.visitVarInsn(Opcodes.ALOAD, 0)
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, "my/RadiusBoundsEach", "get", "()Lnet/imglib2/type/numeric/RealType;", False)
  mv.visitInsn(Opcodes.ARETURN)
  mv.visitMaxs(1, 1)
  mv.visitEnd()

  cw.visitEnd()

  if not classloader:
    classloader = CustomClassLoader()
  return classloader.defineClass("my/RadiusBoundsEach", cw.toByteArray()))
