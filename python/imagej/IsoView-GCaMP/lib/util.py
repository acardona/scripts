from synchronize import make_synchronized
from java.util.concurrent import Callable, Future, Executors, ThreadFactory
from java.util.concurrent.atomic import AtomicInteger
from java.lang.reflect.Array import newInstance as newArray
from java.lang import Runtime, Thread, Double, Float, Byte, Short, Integer, Long, Boolean, Character, System
from net.imglib2.realtransform import AffineTransform3D
from net.imglib2.view import Views
from java.util import LinkedHashMap, Collections
from java.lang.ref import SoftReference
from java.util.concurrent import locks.ReentrantLock


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
  def __init__(self, fn, *args, **kwargs):
    self.fn = fn
    self.args = args
    self.kwargs = kwargs
  def call(self):
    t = Thread.currentThread()
    if t.isInterrupted() or not t.isAlive():
        return None
    return self.fn(*self.args, **self.kwargs)


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

def numCPUs():
  return Runtime.getRuntime().availableProcessors()

class ParallelTasks:
  def __init__(self, name, exe=None):
    self.exe = exe if exe else newFixedThreadPool(name=name)
    self.futures = []
  def add(self, fn, *args, **kwargs):
    future = self.exe.submit(Task(fn, *args, **kwargs))
    self.futures.append(future)
    return future
  def chunkConsume(self, chunk_size, tasks):
    """ 
    chunk_size: number of tasks to submit prior to start waiting and yielding their results.
    tasks: a generator (or an iterable) with Task instances.
    Returns a generator with the results.
    """
    for task in tasks:
      self.futures.add(self.exe.submit(task))
      if len(futures) > chunk_size:
        while len(self.futures) > 0:
          yield self.futures.pop(0).get()
  def awaitAll(self):
    while len(self.futures) > 0:
      self.futures.pop(0).get()
  def generateAll(self):
    while len(self.futures) > 0:
      yield self.futures.pop(0).get()
  def destroy(self):
    self.exe.shutdownNow()
    self.exe = None
    self.futures = None


def timeit(n_iterations, fn, *args, **kwargs):
  times = []
  for i in xrange(n_iterations):
    t0 = System.nanoTime()
    imp = fn(*args, **kwargs)
    t1 = System.nanoTime()
    times.append(t1 - t0)
  print "min: %.2f ms, max: %.2f ms, mean: %.2f ms" % (min(times) / 1000000.0, max(times) / 1000000.0, sum(times)/(len(times) * 1000000.0))


def affine3D(matrix):
  aff = AffineTransform3D()
  aff.set(*matrix)
  return aff


def cropView(img, minCoords, maxCoords):
  return Views.zeroMin(Views.interval(img, minCoords, maxCoords))



class LRUCache(LinkedHashMap):
  def __init__(self, max_entries):
    # initialCapacity 16 (the default)
    # loadFactor 0.75 (the default)
    # accessOrder True (default is False)
    super(LinkedHashMap, self).__init__(10, 0.75, True)
    self.max_entries = max_entries
  def removeEldestEntry(self, eldest):
    if self.size() > self.max_entries:
      return True

class SoftMemoize:
  def __init__(self, fn, maxsize=30):
    self.fn = fn
    # Synchronize map to ensure correctness in a multi-threaded application:
    # (I.e. concurrent threads will wait on each other to access the cache)
    self.m = Collections.synchronizedMap(LRUCache(maxsize))
    self.locks = {}
  
  @make_synchronized
  def getOrMakeLock(self, key):
    lock = self.locks.get(key, None)
    if not lock:
      lock = ReentrantLock()
      self.locks[key] = lock
    return lock

  @make_synchronized
  def releaseLock(self, lock):
    lock = self.locks.get(key, None)
    if lock:
      lock.unlock()
    # cleanup
    for key, lock in self.locks.items(): # a copy
      if lock.getQueuedThreads() < 1:
        del self.locks[key]

  def __call__(self, key):
    """ Locks on the key, and waits, when needing to execute the memoized function. """
    lock = self.getOrMakeLock(key)
    try:
      lock.lockInterruptibly()
      softref = self.m.get(key, None) # self.m is a synchronized map
      o = softref.get() if softref else None
      if o:
        return o
      else:
        # Either not present, or garbage collector discarded it
        # Invoke the memoized function
        o = this.fn(key)
        # Store return value wrapped in a SoftReference
        this.m.put(key, SoftReference(o))
        return o
    finally:
      self.releaseLock(lock)
