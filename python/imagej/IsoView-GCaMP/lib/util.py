from synchronize import make_synchronized
from java.util.concurrent import Callable, Future
from java.lang.reflect.Array import newInstance as newArray
from java.lang import Double, Float, Byte, Short, Integer, Long, Boolean, Character


@make_synchronized
def syncPrint(msg):
  """ Synchronized access to python's built-in print function. """
  print msg


class Getter(Future):
  """ A simulated Future that is ready to deliver its result.
      Does not implement get(self, timeout, unit) as python
      does not support multiple method arity. """
  def __init__(self, ob):
    self.ob = ob
  def get(self):
    return self.ob
  def cancel(self, mayInterruptIfRunning):
    return True
  def isCancelled(self):
    return False
  def isDone():
    return True


class Task(Callable):
  """ A wrapper for executing functions in concurrent threads. """
  def __init__(self, fn, *args):
    self.fn = fn
    self.args = args
  def call(self):
    return self.fn(*self.args)


def ndarray(classtype, dimensions):
    """ E.g. for a two-dimensional native double array, use:
        
          arr = ndarray(Double.TYPE, [3, 4])
        
        which is equivalent to, using the jython jarray library:
            
          arr = array((zeros(4, 'd'), zeros(4, 'd'), zeros(4, 'd')), Class.forName("[D"))

        but here the native array is created via java.lang.reflect.Array.newInstance(class, dimensions).
        """ 
    return newArray(classtype, dimensions)


__nativeClass = {'c': Character, 'b': Byte, 's': Short, 'h': Short,
              'i': Integer, 'l': Long, 'f': Float, 'd': Double, 'z': Boolean}

def nativeArray(stype, dimensions):
    """ Create a native java array such as a double[3][4] like:
    arr = nativeArray('d', (3, 4))

    stype is one of:
    'c': char
    'b': byte
    's': short
    'h': short (like in the jarray package)
    'i': integer
    'l': long
    'f': float
    'd': double
    'z': boolean
    """
    return newArray(__nativeClass[stype].TYPE, dimensions)

