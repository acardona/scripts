from synchronize import make_synchronized
from java.util.concurrent import Callable, Future, Executors, ThreadFactory
from java.util.concurrent.atomic import AtomicInteger
from java.lang.reflect.Array import newInstance as newArray
from java.lang import Runtime, Thread, Double, Float, Byte, Short, Integer, Long, Boolean, Character, System


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
    t = Thread.currentThread()
    if t.isInterrupted() or not t.isAlive():
        return None
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


class ThreadFactorySameGroup(ThreadFactory):
  def __init__(self, name):
    self.name = name
    self.group = Thread.currentThread().getThreadGroup()
    self.counter = AtomicInteger(0)
  def newThread(self, runnable):
    title = "%s-%i" % (self.name, self.counter.incrementAndGet())
    t = Thread(self.group, runnable, title)
    t.setPriority(Thread.NORM_PRIORITY)
    return t

def newFixedThreadPool(n_threads=0, name="jython-worker"):
  """ Return an ExecutorService whose Thread instances belong
      to the same group as the caller's Thread, and therefore will
      be interrupted when the caller is.
      n_threads: number of threads to use.
                 If zero, use as many as available CPUs.
                 If negative, use as many as available CPUs minus that number,
                 but at least one. """
  if n_threads <= 0:
    n_threads = max(1, Runtime.getRuntime().availableProcessors() + n_threads)
  return Executors.newFixedThreadPool(n_threads, ThreadFactorySameGroup(name))


def timeit(n_iterations, fn, *args, **kwargs):
  times = []
  for i in xrange(n_iterations):
    t0 = System.nanoTime()
    imp = fn(*args, **kwargs)
    t1 = System.nanoTime()
    times.append(t1 - t0)
  print "min: %.2f ms, max: %.2f ms, mean: %.2f ms" % (min(times) / 1000000.0, max(times) / 1000000.0, sum(times)/(len(times) * 1000000.0))
