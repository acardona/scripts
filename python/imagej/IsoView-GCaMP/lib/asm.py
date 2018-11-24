from org.objectweb.asm import ClassWriter, Opcodes, Type
from java.lang import Object, ClassLoader, Class, String, Integer
from itertools import imap, izip
import sys

def initClass(name,
              signature=None,
              class_parameters=[], # list of tuples like [("I", UnsignedByteType), ("O", FloatType)]
              java_version=Opcodes.V1_8,
              access=Opcodes.ACC_PUBLIC,
              superclass=Object,
              superclass_parameters=[], # list of strings like ["I", "O"]
              superclass_prefixes=[], # list of strings like ['+', ''] where '+' means e.g. <? extends FloatType>
              interfaces=[],
              interfaces_parameters={}, # dict of class vs class or parameters like {Converter: ["I", "O"]}
              with_default_constructor=True):
  """ Returns a ClassWriter with the class already initialized.

      An example of a class signature. This class declaration:

      public class UnsignedByteToFloatConverter<I extends UnsignedByte, O extends FloatType>
        implements Converter<I, O>

      ... has this signature:

      <I:Lnet/imglib2/type/numeric/integer/UnsignedByteType;O:Lnet/imglib2/type/numeric/real/FloatType;>Ljava/lang/Object;Lnet/imglib2/converter/Converter<TI;TO;>;
      
      First the two class parameter types I and O, which extend UnsignedByteType and FloatType, respectively:
        <I:Lnet/imglib2/type/numeric/integer/UnsignedByteType;OLnet/imglib2/type/numeric/real/FloatType;>

      Then the superclass, which could also be parametrized (with parameter types between <>,
      but not in this case where it is Object (the default):
        Ljava/lang/Object;

      Then the interface, if any; in this case Converter, parametrized with I and O:
        Lnet/imglib2/converter/Converter<TI;TO;>;

      Notice each class name starts with 'L' and ends with ';', whereas
      parameters types start with 'T' followed by string of alphabetic characters
      (often just one like "TI" or "TO").

      A way to compute the fully qualified class names for the signature by
      using the Type.getInternalName from the org.objectweb.asm package:
      
      class_signature = "<I:L%s;O:L%s;>L%s;L%s<TI;TO;>;" % \
         tuple(imap(Type.getInternalName, (UnsignedByteType, FloatType, Object, Converter)))
  """

  if not signature:
    # Construct the signature
    # 1. Class parameter types, if any
    if len(class_parameters) > 0:
      p = "<" + "".join("%s:L%s;" % (t, Type.getInternalName(classname)) for t, classname in class_parameters) + ">"
    else:
      p = ""

    # 2. Superclass and its parameter types, if any
    sp = "L%s;" % Type.getInternalName(superclass)
    if len(superclass_parameters) > 0:
      sp += "<" + "".join("T%s;" % t for t in superclass_parameters) + ">"

    # 3. Interfaces and their parameter types, if any
    ips = []
    for interface in interfaces:
      ip = "L%s" % Type.getInternalName(interface)
      types = interfaces_parameters.get(interface, None)
      if types:
        ip += "<" + "".join("%s" % makeType(t) for t in types) + ">"
      ip += ";"
      ips.append(ip)
    
    signature = p + sp + "".join(ips)

  print "class '%s' signature:\n%s" % (name, signature)
  
  cw = ClassWriter(ClassWriter.COMPUTE_FRAMES)
  cw.visit(java_version,                         # java version
           access,                               # default to public
           name,                                 # package and class name
           signature,                            # signature
           Type.getInternalName(superclass),     # superclass
           map(Type.getInternalName, interfaces))# array or list of interfaces
  
  if with_default_constructor:
    initConstructor(cw, superclass=superclass, default=True)
  
  return cw


def initConstructor(cw,
                    superclass=Object,
                    default=False,
                    descriptor="()V",
                    signature=None,
                    exceptions=None,
                    super_descriptor="()V"):
  """ Adds to the ClassWriter cw a public constructor without arguments that calls super().
      Returns the constructor MethodWriter.
      If default=True, then the constructor is built without arguments and is completed without a body.
      Otherwise, the descriptor is used and the MethodWriter is returned without having finished. It is
      then the responsibility of the caller to invoke RETURN and specifiy the Maxs (stack size and number of local variables). """
  
  constructor = cw.visitMethod(Opcodes.ACC_PUBLIC,  # public
                               "<init>",            # method name
                               descriptor,          # descriptor
                               signature,           # signature
                               exceptions)          # Exceptions (array of String, or None)

  # ... has to invoke the super() for Object
  constructor.visitCode()
  constructor.visitVarInsn(Opcodes.ALOAD, 0) # load "this" onto the stack: the first local variable is "this"
  constructor.visitMethodInsn(Opcodes.INVOKESPECIAL, # invoke an instance method (non-virtual)
                              Type.getInternalName(superclass), # class on which the method is defined
                              "<init>",              # name of the method (<init> for a constructor)
                              super_descriptor,      # descriptor of super constructor
                              False)                 # not an interface
  if not default:
    # Return half-way, allowing for the caller to complete the body
    return constructor

  # Else, finish the constructor
  constructor.visitInsn(Opcodes.RETURN) # End the constructor method
  constructor.visitMaxs(1, 1) # The maximum number of stack slots (1, for ALOAD) and local vars (1: "this", implicit)
  return constructor

def makeReturnType(t):
  """ Figures out if the t type is a string, and returns it as is,
     or a class, and returns its internal name in L%s; format. """
  if isinstance(t, str): # A String like a native integer "I" or long "J" or float "F", etc., or void "V".
    return t
  elif isinstance(t, type): # Class
    return "L%s;" % Type.getInternalName(t)
  else:
    print "error at makeReturnType for %s" % t

def makeType(t):
  """ Figures out if the t type is a string, and returns it as "T%s;",
      or a class, and returns its internal name in L%s; format. """
  if isinstance(t, str): # A String like a native integer "I" or long "J" or float "F", etc., or void "V".
    return "T%s;" % t
  elif isinstance(t, type): # Class
    return "L%s;" % Type.getInternalName(t)
  else:
    print "error at makeType"


def initMethod(cw,
               name,
               access=Opcodes.ACC_PUBLIC,
               descriptor=None,
               signature=None,
               argument_classes=[],    # Used to create the descriptor (and signature) when it is absent
               argument_parameters=[], # idem, if populated, requires argument_prefixes to have corresponding String instances
               argument_prefixes=[],   # idem, like ['+'] to mean <? extends UnsignedByteType>, or [''] for nothing
               return_type="V",        # 'V' means void
               exceptions=[]):
  """ Starts a visit to a method, does not finish it:
      the body and closing has to be done by the caller.
      Returns the MethodVisitor. """
  
  if not descriptor:
    if len(argument_classes) > 0:
      descriptor = "(" + "".join("L%s;" % Type.getInternalName(c) for c in argument_classes) + ")" + makeReturnType(return_type)
    else:
      descriptor = "()" + makeReturnType(return_type)

  if not signature:
    if len(argument_parameters) > 0:
      signature = "("
      signature += "".join("L%s<%s%s>;" % (Type.getInternalName(clazz), prefix, makeType(param))
                           for clazz, prefix, param in izip(argument_classes, argument_prefixes, argument_parameters))
      signature += ")" + makeReturnType(return_type)
    else:
      signature = descriptor

  print "Method '%s' descriptor:\n%s" % (name, descriptor)
  print "Method '%s' signature:\n%s" % (name, signature)
  
  method = cw.visitMethod(access,             # default to public method
                          name,               # name of the method we are implementing
                          descriptor,
                          signature,
                          map(Type.getInternalName, exceptions)) # Exceptions (array of String of class internal names)
  return method



class CustomClassLoader(ClassLoader):
  def defineClass(self, name, bytes):
    # Inheritance of protected methods is complicated in jython
    m = super(ClassLoader, self).__thisclass__.getDeclaredMethod("defineClass", String, Class.forName("[B"), Integer.TYPE, Integer.TYPE)
    m.setAccessible(True)
    try:
      return m.invoke(self, name.replace("/", "."), bytes, 0, len(bytes))
    except:
      print sys.exc_info()

