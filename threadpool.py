#  threadpool.py provides classes for thread pooling and inter-thread communication.
#  Copyright (C) 2000 Bryn Keller

#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2.1 of the License, or (at your option) any later version.

#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.

#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#  Author/Maintainer: Bryn Keller <xoltar@starship.python.net>

"""
This module uses the threading and Queue modules to create a pool of reusable
threads. After creating an instance of ThreadPool, one queues functions to be
excecuted. The pool dispatches the functions to the waiting threads, which
call them.

When queueing a function on the pool with *pool*.put(), an instance
of ReturnValue is returned. ReturnValue is a subclass of lazy.Lazy, and
can be used in any context that a regular lazy expression can. When evaluating
a ReturnValue, the evaluating thread will block until the other thread has
completed its work and loaded the return value of the function into the
ReturnValue instance.

VLocks are an alternative to RLocks which include a visible queue threads waiting
for the lock.

lock, unlock, getLockFor, and deleteLockFor work with a module-level
dictionary of objects to locks, and can be more convenient than working with
lock objects directly.

Locked and Async are callable wrappers around a function. Async calls return
immediately after queueing their function on a thread pool, while Locked calls
first acquire the lock they were passed on creation, call their function, and
release the lock.

"""
import threading
import time
import sys
import lazy
import Queue

__version__ == "1.0.1"

class Worker(threading.Thread):
    """
    A Thread which works for a ThreadPool, getting work from that queue,
    executing, and then returning to the queue again to wait for more
    work. The work that it does is to call a no-args function. Using
    functional.py it is possible to make this include any number of
    callbacks, arbitrary error reporting, etc.
    """
    def __init__(self, getJobFunc, group = None, name = None,
                 exitFunc = None, trap_errors = 0):
        threading.Thread.__init__(self, group = group, name = name)
        self._getJob = getJobFunc
        self._busy = 0
        self._error = 0
        self._job = None
        self._ignore_error = trap_errors
        self._exitFunc = exitFunc

    def isBusy(self):
        return self._busy

    def getJob(self):
        return self._job

    def getAssociatedValue(self):
        return self._job[2]    

    def run(self):
        while 1:
            self._busy = 0
            job = self._getJob()
            #Jobs are 2-tuples with the function to call in the first
            #position, and the ReturnValue instance in the second.
            self._busy = 1
            self._job = job
            if not job[0]:
                #We treat an empty job as a command to terminate.
                #if job[1] would call __nonzero__ on ReturnValue, which would
                #cause a deadlock as it tried to eval() the unloaded ReturnValue.
                if not job[1] is None:
                    job[1].load(None)
                return
            else:
                try:
                    val = job[0]()
                    asException = 0
                except StandardError, e:
                    val = e
                    asException = 1
                    #if job[1] would call __nonzero__ on ReturnValue, which would
                    #cause a deadlock as it tried to eval() the unloaded ReturnValue.
                if not job[1] is None:
                    job[1].load(val, asException = asException)
            self._job = None
        if self._exitFunc:
            self._exitFunc()


class ReturnValue(lazy.LazyExpr):
    """
    A lazy return value. Calls to eval block until the value is loaded,
    but the ReturnValue instance can be stored or passed to other
    functions in the meantime.
    """
    def __init__(self):
        pass

    def eval(self):
        if not self.__dict__.has_key("_value"):
            self.__dict__['_condition'] = threading.Condition()
            self._condition.acquire()
            self._condition.wait()
            self._condition.release()
        if self.__dict__['_asException']:
            raise self._value
        else:
            return self._value

    def load(self, val, asException = 0):
        self.__dict__['_asException'] = asException
        self.__dict__['_value'] = val
        if self.__dict__.has_key("_condition"):
            self._condition.acquire()
            self._condition.notifyAll()
            self._condition.release()

    def __repr__(self):
        return "<ReturnValue instance at " + str(hex(id(self))) + ">"



class Async:
    """
    Wrapped around a normal method or function, this will cause calls to the
    function to return ReturnValue tokens immediately, while the function
    runs in a different thread. Example:
    >>> p = ThreadPool()
    >>> threading.currentThread()
    <_MainThread(MainThread, started)>
    >>> def pr():
    ...     print threading.currentThread()
    ...
    >>> pr()
    <_MainThread(MainThread, started)>
    >>> f = Async(pr, p)
    >>> f()
    <ReturnValue instance at 0x7c08d0>
    >>> <Worker(Thread Pool - 1, started)>

    """
    def __init__(self, func, pool):
        self._func = func
        self._pool  = pool

    def __call__(self, *args, **kwargs):
        return self._pool.put(self._func)


class Locked:
    """
    Wrapped around a normal method or function, this will cause calls to the
    function to block if another thread has the lock. Note that this
    shortcut only protects things that use the same lock.
    """
    def __init__(self, func, lock):
        self._func = func
        self._lock = lock
    def __call__(self, *args, **kwargs):
        self._lock.acquire()
        try:
            apply(self._func, args, kwargs)
        finally:
            self._lock.release()

class VLock:
    """
    Similar to an RLock, but with a (V)isible queue of waiting threads.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.owner = None
        self.queue = []
        self.ownerlocks = 0

    def isLocked(self):
        return not self.owner is None

    def getOwner(self):
        return self.owner

    def getWaiting(self):
        return self.queue

    def acquire(self, blocking = 1):
        thread = threading.currentThread()
        self.queue.append(thread)
        self.lock.acquire(blocking)
        self.queue.remove(thread)
        self.ownerlocks = self.ownerlocks + 1
        self.owner = thread

    def release(self):
        assert threading.currentThread() == self.owner
        self.ownerlocks = self.ownerlocks - 1
        if self.ownerlocks == 0:
            self.owner = None
            self.lock.release()
            return 1
        else:
            return 0

    def __str__(self):
        return "<VLock owner = " + str(self.owner) + " waiting = " + str(self.queue) + " >"


_locks = {}

def getLockFor(object):
    """
    Returns a VLock associated with the object, creating one if necessary.
    """
    if not _locks.has_key(object):
        _locks[object] = VLock()
    lock = _locks[object]
    return lock

def deleteLockFor(object):
    """
    Deletes the VLock associated with *object*, if one exists.
    """
    try:
        del _locks[object]
    except:
        pass

def lock(object):
    """
    Acquires a VLock for any arbitrary object. Note that this lock only protects
    against access by other threads that use lock/unlock or a LockedObjectMethod,
    below.
    """
    lock = getLockFor(object)
    lock.acquire()

def unlock(object):
    """
    Releases a held lock on an object. Every lock must be balanced by an unlock
    before any other thread may access the object.
    """
    if not _locks.has_key(object):
        return
    lock = _locks[object]
    lock.release()


class ThreadPool(Queue.Queue):
    """
    Creates and maintains a pool of threads. Jobs are queued by calling put.
    """
    def __init__(self, name = "Thread Pool", minThreads = 2, maxThreads = 10, daemon = 1):
        Queue.Queue.__init__(self, 0)
        self._pool = []
        self._name = name
        self._minThreads = minThreads
        self._maxThreads = maxThreads
        self._threadCounter = 0
        self._dead = 0
        self._daemon = daemon
        self.checkThreads()

    def isDaemon(self):
        return self._daemon
    

    def getThreads(self):
        """
        Returns a list of all threads in this pool, whether alive, dead, busy, or idle.
        """
        return self._pool[:]

    def getBusyThreads(self):
        return filter(lambda x:x.isBusy(), self._pool)

    def getIdleThreads(self):
        return filter(lambda x:not x.isBusy(), self._pool)

    def getLiveThreads(self):
        return filter(lambda x:x.isAlive(), self._pool)

    def _addThread(self):
        w = Worker(self.get, name = self._name + " - " + str(self._threadCounter ))
        self._threadCounter  = self._threadCounter  + 1
        self._pool.append(w)
        w.setDaemon(self.isDaemon())
        w.start()

    def shutDown(self):
        """
        Cause this pool to shut down gracefully, by refusing to create new threads,
        and scheduling None (treated as a command to end) jobs for all its live
        threads.
        """
        self._dead = 1
        for thread in self._pool :
            #Bypass the call to checkThreads in our own put method...
            Queue.Queue.put(self, (None, None, None))

    def restart(self):
        if not self._dead:
            self.shutDown()
        while self.getLiveThreads():
            sleep(100)

    def checkThreads(self):
        """
        Ensure that the correct number of (live) threads are available for doing work.
        It is not normally necessary for clients to call this method.
        """
        if self._dead:
            raise RuntimeError, "This pool has been shut down."
        self._pool = self.getLiveThreads()
        while len(self._pool ) < self._minThreads:
            self._addThread()
        while len(self.getIdleThreads()) < self.qsize():
            if len(self._pool) < self._maxThreads:
                self._addThread()
            else:
                break

    def put(self, item, block = 1, associated = None):
        self.checkThreads()
        rv = ReturnValue()
        Queue.Queue.put(self, (item, rv, associated), block)
        return rv





