from org.objectweb.asm import ClassWriter, Opcodes
from java.lang import ClassLoader
from lib.asm import CustomClassLoader, initClass, initMethod, initMethodObj
from java.util.function import BiConsumer

def defineBiConsumerTypeSet(imglib2Type, classname=None):
  """ 
      A class to use in e.g. an ImgLib2 LoopBuilder.setImages(img1, img2).forEachPixel(<instance of this BiConsumer class>)
      where both image are of the same Type, and the value of one has to be set as the value of the other, like this:
        type1.set(type2)
        
      In java, this would be written as: LoopBuilder.setImages(img1, img2).forEachPixel( (type1, type2) -> type1.set(type2) );
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
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 0)
  methodVisitor.visitMethodInsn(Opcodes.INVOKESPECIAL, "java/lang/Object", "<init>", "()V", False)
  methodVisitor.visitInsn(Opcodes.RETURN)
  methodVisitor.visitMaxs(1, 1)
  methodVisitor.visitEnd()

  # BiConsumer.accept method implementation with body Type.set(Type)
  methodVisitor = classWriter.visitMethod(Opcodes.ACC_PUBLIC, "accept", "(L%s;L%s;)V" % (typeClassname, typeClassname), "(TT;TT;)V", None)
  methodVisitor.visitCode()
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 2)
  methodVisitor.visitVarInsn(Opcodes.ALOAD, 1)
  methodVisitor.visitMethodInsn(Opcodes.INVOKEVIRTUAL, typeClassname, "set", "(L%s;)V" % typeClassname, False)
  methodVisitor.visitInsn(Opcodes.RETURN)
  methodVisitor.visitMaxs(2, 3)
  methodVisitor.visitEnd()

  # BiConsumer.accept method with Object,Object arguments: to provide a bridge between the BiConsumer.accept method and the class accept method
  methodVisitor = classWriter.visitMethod(Opcodes.ACC_PUBLIC | Opcodes.ACC_BRIDGE | Opcodes.ACC_SYNTHETIC, "accept", "(Ljava/lang/Object;Ljava/lang/Object;)V", None, None)
  methodVisitor.visitCode()
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



def defineBiConsumerTypeSet2(imglib2Type,
                             classname=None,
                             return_type="V"):  # can be a class too
  """ Exactly the same as defineBiConsumerTypeSet but using lib.asm library functions to cut to the chase. """
  if classname is None:
    classname = "asm/loop/BiConsumer_%s_set" % imglib2Type.getSimpleName()
  
  cw = initClass(classname,
                 class_parameters=[("T", imglib2Type)],
                 interfaces=[BiConsumer],
                 interfaces_parameters={BiConsumer: ["T", "T"]})
  
  mv = initMethod(cw,
                  "accept",
                  argument_classes=[imglib2Type, imglib2Type],
                  return_type=return_type)
  mv.visitCode()
  # implement t2.set(t1)
  mv.visitVarInsn(Opcodes.ALOAD, 2) # load second argument first
  mv.visitVarInsn(Opcodes.ALOAD, 1) # then load the first argument
  # Use the first loaded object as the object onto which to invoke "set", and the second loaded object as its argument, so t2.set(t1)
  typeClassname = imglib2Type.getName().replace(".", "/")
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL, typeClassname, "set", "(L%s;)V" % typeClassname, False)
  mv.visitInsn(Opcodes.RETURN)
  mv.visitMaxs(2, 3)
  mv.visitEnd()
  
  # The "accept" method was from an interface, so add a bridge method that checks casts
  initMethodObj(cw, classname, "accept", argument_classes=[imglib2Type, imglib2Type], return_type=return_type)
  
  cw.visitEnd()
  
  loader = CustomClassLoader()
  biconsumerClass = loader.defineClass(classname, cw.toByteArray())
  return biconsumerClass


def createBiConsumerTypeSet2(*args, **kwargs):
  return defineBiConsumerTypeSet2(*args, **kwargs).newInstance()


def binaryLambda(objClass,
                method_name,
                argClass,
                interface=BiConsumer,
                interface_method="accept",
                classname=None,
                return_type="V", # can be a class too
                as_instance=True): # return as an instance when True, as a class when False
  """
     Define a interface<O, A> with an interface_method with body O.method_name(A).
     For example, a BiConsumer with an "accept" method that takes two arguments an has arg1.method_name(arg2) as body.
  """
  if classname is None:
    classname = "asm/loop/%s_%s_%s_%s" % (interface.getSimpleName(),
                                          objClass.getSimpleName(),
                                          method_name,
                                          argClass.getSimpleName())
  
  cw = initClass(classname,
                 class_parameters=[("O", objClass), ("A", argClass)],
                 interfaces=[interface],
                 interfaces_parameters={interface: ["O", "A"]})
  
  mv = initMethod(cw,
                  interface_method,
                  argument_classes=[objClass, argClass],
                  return_type=return_type)
  mv.visitCode()
  # implement Obj.method_name(Arg)
  mv.visitVarInsn(Opcodes.ALOAD, 1) # The first argument of the interface_method
  mv.visitVarInsn(Opcodes.ALOAD, 2) # The second argument of the interface_method
  # Use the first loaded object as the object onto which to invoke method_name
  # and the second loaded object as its argument, so Obj.method_name(Arg) 
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                     objClass.getName().replace(".", "/"),
                     method_name,
                     "(L%s;)V" % argClass.getName().replace(".", "/"),
                     False)
  mv.visitInsn(Opcodes.RETURN)
  mv.visitMaxs(2, 3)
  mv.visitEnd()
  
  # The interface_method was from an interface, so add a bridge method that checks casts
  initMethodObj(cw, classname, interface_method, argument_classes=[objClass, argClass], return_type=return_type)
  
  cw.visitEnd()
  
  lambdaClass = CustomClassLoader().defineClass(classname, cw.toByteArray())
  return lambdaClass.newInstance() if as_instance else lambdaClass


def nthLambda(objClass,
              method_name,
              argClasses, # a list, can be empty, max 14 elements
              interface, # the interface with at least one generic type
              interface_method, # with as many arguments as argClasses
              classname=None,
              return_type="V", # can be a class too
              as_instance=True): # return as an instance when True, as a class when False
  """
     Define a interface<O, A1, A2, ...> with an interface_method with body O.method_name(A1, A2, ...).
     For example, a BiConsumer with an "accept(O arg1, A1 arg2)" method that takes two arguments an has arg1.method_name(arg2) as body.
  """
  if classname is None:
    classname = "asm/loop/%s_%s_%s_%s" % (interface.getSimpleName(),
                                          objClass.getSimpleName(),
                                          method_name,
                                          "_".join(argClass.getSimpleName() for argClass in argClasses))
  
  parameters = [("O", objClass)] + zip("ABCDEFGHIJKLMN", argClasses)
  cw = initClass(classname,
                 class_parameters=parameters,
                 interfaces=[interface],
                 interfaces_parameters={interface: [letter for letter, _ in parameters]})
  
  mv = initMethod(cw,
                  interface_method,
                  argument_classes=[objClass] + argClasses,
                  return_type=return_type)
  mv.visitCode()
  # implement Obj.method_name(Arg1, Arg2, ...)
  for i in xrange(1, 1 + len(argClasses) + 1):
    mv.visitVarInsn(Opcodes.ALOAD, i) # 1-based
  # Use the first loaded object as the object onto which to invoke method_name
  # and the second loaded object as its argument, so Obj.method_name(Arg) 
  mv.visitMethodInsn(Opcodes.INVOKEVIRTUAL,
                     objClass.getName().replace(".", "/"),
                     method_name,
                     "(%s)V" % "".join("L%s;" % argClass.getName().replace(".", "/") for argClass in argClasses),
                     False)
  mv.visitInsn(Opcodes.RETURN)
  mv.visitMaxs(2, 3)
  mv.visitEnd()
  
  # The interface_method was from an interface, so add a bridge method that checks casts
  initMethodObj(cw, classname, interface_method, argument_classes=[objClass] + argClasses, return_type=return_type)
  
  cw.visitEnd()
  
  lambdaClass = CustomClassLoader().defineClass(classname, cw.toByteArray())
  return lambdaClass.newInstance() if as_instance else lambdaClass

