## lazy.py provides support for lazy expressions and datastructures.
## Copyright (C) 2000 Bryn Keller

## This library is free software; you can redistribute it and/or
## modify it under the terms of the GNU Lesser General Public
## License as published by the Free Software Foundation; either
## version 2.1 of the License, or (at your option) any later version.

## This library is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## Lesser General Public License for more details.

## You should have received a copy of the GNU Lesser General Public
## License along with this library; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


from types import *
from functional import *
import sys


__version__ = '0.8.0'



        
def isLazy(thing):
    """
    Returns 1 if *thing* is a Lazy expression, 0 otherwise.
    """
    try:
        return isinstance(thing, Lazy)
    except:
        return 0

class Lazy:
    """
    Abstract base class for lazy things.
    """
    def eval(self):
        """
        Forces this lazy object to evaulate itself fully. Returns
        the final, strict version of the object, if appropriate.
        For instance, LazyExpr.eval returns the result of evaluating
        its expression, and LazyTuple.eval returns a normal tuple.
        """
        raise NotImplementedError

    def isEvaluated(self):
        """
        Should return 1 if the object has been fully evaluated,
        0 otherwise.
        """
        raise NotImplementedError

class LazyExpr(Lazy):
    """
    Lazy expressions are expressions which are not computed until needed.
    Many functional languages (Haskell, Scheme, OCaml, etc.) provide support
    for this as a language feature, but a large class of those things can
    be simulated in Python with this class and/or LazyTuple.
    Things that will force a lazy expression *expr* to be evaluated:
        - *expr*.eval()
        - any value comparison, such as *expr* < 5, or *expr* == "abc"
        - any sort of operation such as slicing, getattrs, or mathematical
          opertions, **unless the other operands involved are also lazy.**
        - calling str(*expr*). Same for int, float, long.
    A lazy expression is evaluated in the namespaces of the code which constructed
    it, unless the defaults are overridden. For example:

    a = 5
    laz = LazyExpr("a * 5")
    a = 7
    assert laz == 25

    #Now laz can be used in any context, and will always evaluate to 25, even if
    #a changes or goes out of scope.
    """
    def __init__(self, code, globs = {}, locs = {}):
        """
        *code* can be either a code object or a string. Either way, it should
        be an expression, not a statement. If the *globs* or *locs* params are
        omitted, the global and local namespaces of the caller will be used
        for evaluation.
        """
        if type(code) == StringType:
            code = compile(code, 'Lazy expr: ' + code, 'eval')
        self.__dict__['_code'] = code
        if not globs or not locs:
            frame = getStackFrame().f_back
            l, g = frame.f_locals, frame.f_globals
            if not locs:
                locs = l.copy()
            if not globs:
                globs = g.copy()
        self.__dict__['_globs'] = globs
        self.__dict__['_locs'] = locs

    def eval(self):
        """
        Forces (and returns) the evaluation of the expression.
        """
        if not self.__dict__.has_key('_value'):
            self.__dict__['_value'] = eval(self._code, self._globs, self._locs)
            #Delete namespaces so we don't prevent GC on their contents...
            del self.__dict__['_globs']
            del self.__dict__['_locs']
        return self.__dict__['_value']

    def __str__(self):
        """
        Will cause evaluation.
        """
        return str(self.eval())

    def __repr__(self):
        """
        Does **not** cause evaluation.
        """
        return self._code.co_filename

    def __len__(self):
        """
        Will cause evaluation.
        """
        return len(self.eval())

    def __mul__(self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("self.eval() * other.eval()", locs = locals())
        return self.eval() * other

    def __rmul__(self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("other.eval() * self.eval()")
        return other * self.eval()

    def __div__(self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("self.eval() * other.eval()")
        return self.eval()/other

    def __rdiv__(self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("other.eval()/self.eval()")
        return other/self.eval()

    def __mod__(self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("other.eval() % self.eval()")
        return other % self.eval()

    def __rmod__(self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("self.eval() % other.eval()")
        return self.eval() % other

    def __divmod__ (self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("divmod(other.eval(),self.eval())")
        return divmod(other, self.eval())

    def __pow__ (self, other, modulo):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("pow(self.eval(), other.eval(), modulo)")
        return pow(self.eval(), other, modulo)

    def __lshift__ (self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("self.eval() << other.eval()")
        return self.eval() << other

    def __rshift__ (self, other) :
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("self.eval() >> other.eval()")
        return self.eval() >> other

    def __and__ (self, other) :
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("self.eval() & other.eval()")
        return self.eval() & other

    def __xor__ (self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("self.eval() ^ other.eval()")
        return self.eval() ^ other
    def __or__ (self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("self.eval() | other.eval()")

    def __radd__ (self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("other.eval() + self.eval()")
        return other + self.eval()

    def __rsub__ (self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("other.eval() - self.eval()")
        return other - self.eval()

    def __rdivmod__ (self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("divmod(other.eval(), self.eval())")
        return divmod(other + self.eval())

    def __rpow__ (self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("pow(other.eval(), self.eval())")
        return pow(other, self.eval())

    def __rlshift__ (self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("other.eval() << self.eval()")
        return other << self.eval()

    def __rrshift__ (self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("other.eval() >> self.eval()")
        return other >> self.eval()

    def __rand__ (self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("other.eval() & self.eval()")
        return other & self.eval()

    def __rxor__ (self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("other.eval() ^ self.eval()")
        return other ^ self.eval()

    def __ror__ (self, other):
        """
        Will cause evaluation, unless *other* is also lazy.
        """
        if isLazy(other):
            return LazyExpr("other.eval() | self.eval()")
        return other | self.eval()

    def __neg__ (self):
        """
        Will cause evaluation.
        """
        return -self.eval()

    def __pos__ (self):
        """
        Will cause evaluation.
        """
        return +self.eval()

    def __abs__ (self):
        """
        Will cause evaluation.
        """
        return abs(self.eval())

    def __invert__ (self):
        """
        Will cause evaluation.
        """
        return not self.eval()

    def __complex__ (self):
        """
        Will cause evaluation.
        """
        return complex(self.eval())

    def __oct__ (self):
        """
        Will cause evaluation.
        """
        return oct(self.eval())

    def __hex__ (self):
        """
        Will cause evaluation.
        """
        return hex(self.eval())

    def __getitem__(self, ntx):
        """
        Does **not** cause evaluation.
        """
        if isLazy(ntx):
            return LazyExpr("self.eval()[ntx.eval()]")
        else:
            return LazyExpr("self.eval()[ntx]")

    def __getslice__(self, i, j):
        """
        Does **not** cause evaluation.
        """
        return LazyExpr("self.eval()[i:j]")

    def __delslice__(self, i, j):
        """
        Will cause evaluation.
        """
        del self.eval()[i:j]

    def __setitem__(self, key, value):
        """
        Will cause evaluation.
        """
        self.eval()[key] = value

    def __cmp__(self, other):
        """
        Will cause evaluation.
        """
        return cmp(self.eval(), other)

    def __call__(self, *args, **kwargs):
        """
        Will cause evaluation.
        """
        return self.eval()(*args, **kwargs)

    def __eq__(self, other):
        """
        Will cause evaluation.
        """
        return self.eval() == other

    def __lt__(self, other):
        """
        Will cause evaluation.
        """
        return self.eval() < other
        
    def __gt__(self, other):
        """
        Will cause evaluation.
        """
        return self.eval() > other
    
    def __getattr__(self, name):
        """
        Does **not** cause evaluation.
        """
        if name == '__coerce__':
            raise AttributeError, name
        return LazyExpr("getattr(self.eval(), name)")

    def __setattr__(self, name, value):
        """
        Will cause evaluation.
        """
        setattr(self.eval(), name, value)

    def __delattr__(self, name):
        """
        Will cause evaluation.
        """
        delattr(self.eval(), name)

    def __int__(self):
        """
        Will cause evaluation.
        """
        return int(self.eval())

    def __float__(self):
        """
        Will cause evaluation.
        """
        return float(self.eval())

    def __long__(self):
        """
        Will cause evaluation.
        """
        return long(self.eval())

    def __copy__(self):
        """
        Does **not** cause evaluation.
        """
        import copy
        return LazyExpr("copy.copy(self.eval())")

    def __deepcopy__(self, dict):
        """
        Does **not** cause evaluation.
        """
        import copy
        return LazyExpr("copy.deepcopy(self.eval())")

class Uncomputed:
    """
    Placeholder value used in LazyTuples when an index is known to exist, but
    does not need to be computed yet.
    """
    pass


class LazySequence(Lazy):
    """
    Abstract base class for lazy sequences.
    """
    def isTerminating(self):
        """
        Return 1 if this is a finite sequence, 0 if it is infinitely long.
        """
        raise NotImplementedError

    def __str__(self):
        val = ""
        try:
            for i in range(3):
                if val:
                    val = val + ", "
                val = val + str(self[i])
        except IndexError:
            pass
        else:
            val = val + ", .."

        return "%s (%s)" % (self.__class__.__name__, val)
        
    def __mul__(self, other):
        #TODO: Should this and __add__ play nicely with lazy values?
        if not self.isTerminating():
            return self
        return self.eval() * other

    def __add__(self, other):
        if not self.isTerminating():
            return self
        return self.eval() + other

    def __cmp__(self, other):
        if self is other:
            return 0
        if isinstance(other, LazySequence):
            if self.isTerminating():
                if not other.isTerminating():
                    return -1
            elif other.isTerminating():
                return 1
        elif type(other) == type(()):
            if not self.isTerminating():
                return 1
            else:
                if cmp(len(self), len(other)):
                    return cmp(len(self), len(other))
                else:
                    for sthing, othing in lazyzip(self, other):
                        if cmp(sthing, othing):
                            return cmp(string, othing)
                    return 0
        else:
            return 1

class LazyTuple(LazySequence):
    """
    Lazy tuples (equivalent to lazy lists in functional languages) are sequences
    whose values are calculated on demand. In a normal (strict) tuple, every
    value in the tuple must be known at the time it is constructed, and it has a
    definite length. Not so with LazyTuples, which may have potentially infinite
    length, and the value at a given index is computed only when needed for some
    other calculation.

    In this implementation, a function is defined which takes two arguments, an
    index, and the LazyTuple the index is being done on. Whatever this function
    returns is the value of the LazyTuple at that index. The function will only
    be called once for each index, and the cached value will be used in
    subsequent indexing operations.

    For example:

    #Build a lazy list of squares:
    def square(index, seq):
        return index * index

    >>>laz = LazyList(itemFunc = square)
    >>>print laz[2]
    4
    >>>

    #But this is a simple case which can be extrapolated directly from the
    #index. A better example:

    def factorial(index, seq):
        if index == 0:
            return 1
        else:
            return seq[index -1] * index

    >>>laz = LazyList(itemFunc = factorial)
    >>>laz[3]
    6
    >>>

    In this last example, laz[3] caused factorial to be called with index == 3,
    which in turn forced the evaluation (because it's necessary for factorial
    construction) of all the indices prior to 3. In the first example, no
    other indices need to be computed.

    Note that neither of these examples *terminates*, that is they are both
    of infinite length (actually they'll overflow from integer multiplication
    eventually, but's that's not important for this discussion). When dealing
    with infinite tuples, a few rules apply:

    - *lazytuple*.isTerminating() will return 1 if the tuple has definite length,
        0 otherwise.
    - len(*lazytuple*) will raise a RuntimeError if the list is infinite.
    - if *lazytuple*: will always be true for an infinite tuple.
    - LazyTuples may be compared normally.
    - iteration over a LazyTuple with for works fine, but if the tuple doesn't
      terminate, neither will your loop!

    """
    def __init__(self, itemFunc = None, length = -1):
        """
        *itemFunc* is a function which takes two arguments, *index* and
        *sequence*, and is used to generate the value at an arbitrary
        index. If *length* is zero or more, then this is a bounded (finite)
        LazyTuple. A *length* of -1 indicates a (possibly) infinite tuple,
        a -2 value indicates a tuple which will eventually terminate, but
        its exact length is not known at this time.
        
        Storage space is never duplicated for LazyTuples and slices taken
        from them.
        """
        self._itemFunc = itemFunc
        self._memo = []
        self._evaluated = 0
        self._length = length
        
    def isTerminating(self):
        """
        Return 1 if this is a finite tuple, 0 if it is infinitely long.
        """
        return self._length >= 0 or self._length == -2

    def __getitem__(self, i):
        if self._length >= 0 and i >= self._length:
            raise IndexError, i
        if i < 0:
            #Convert to a positive index. Note this forces
            #the tuple to be completely evaluated if its length isn't
            #already known. Taking the len() of an infinite tuple
            #will cause an error.
            i = len(self) + i            
        if len(self._memo) > i:
            val = self._memo[i]
            if not val is Uncomputed:
                return self._memo[i]
        try:
            val = self._itemFunc(i, self)
        except IndexError:
            #Either there was in internal error in the function, or the tuple
            #is finished. Like errors in __getattr__ methods which cause spurious
            #AttributeErrors, this may produce unintended results. However, it's
            #the only way for a possibly infinite tuple to announce it's reached
            #a limit.
            self._length = i
            raise
        if len(self._memo) <= i:
            #There are other values at lesser indices that have not been computed
            #yet. We extend the memo to be at least as big as this (now known)
            #index. The spots in between we fill with Uncomputed. In the future,
            #it might be worthwhile to create a variation on this class which
            #uses a dictionary for _memo instead of a list - such a subclass would
            #be more efficient for "sparse" tuples, where the value at an index
            #doesn't depend on the value at a previous index.
            self._memo.extend([Uncomputed] * ((i+1) - len(self._memo)))
        self._memo[i] = val
        return val

    def __getslice__(self, i, j):
        #TODO: Check for reversed slices?
        print "LT getslice", i, j
        if j != sys.maxint:
            sliceEnd = j
        else:
            sliceEnd = -1
        if self._length > 0:
            if i >= self._length:
                raise IndexError, i
            if j >= self._length and j != sys.maxint:
                raise IndexError, j
        return LazySlice(source = self, start = i, end = sliceEnd)

    def __len__(self):
        if not self.isTerminating():
            raise RuntimeError, "Non-terminating structure, cannot evaluate len()."
        if self._length >= 0:
            return self._length
        else:
            self.eval()
            return len(self._memo)

    def __nonzero__(self):
        return 1

    def eval(self):
        if self._length == -1:
            raise RuntimeError, "Cannot eval a non-terminating sequence."
        if not self._evaluated:
            i = 0
            while 1:
                try:
                    self[i]
                    i = i + 1
                except IndexError:
                    self._evaluated = 1
                    break
        #This tuple is now fully evaluated, make the _memo a tuple,
        #so that we don't have spine-copying problems when we have to
        #return a tuple to clients of .eval(). We can just return them
        #the original memo.
        self._memo = tuple(self._memo)
        return self._memo
    

class LazySlice(LazySequence):
    def __init__(self, source, start, end):
        """
        """
        self._start = start
        self._end = end
        self._source = source
        self._evaluated = 0
        
    def isTerminating(self):
        """
        Return 1 if this is a finite tuple, 0 if it is infinitely long.
        A value of 2 means unknown.
        """
        return self._end > 1 or self._source.isTerminating()

    def __getitem__(self, i):
        if i >= 0:
            if i < self._end or self._end < 0:
                return self._source[i + self._start]
            else:
                raise IndexError, i
        else:
            if self._end < 0:
                if not self._source.isTerminating():
                    raise IndexError, i
                self._source.eval()
                if (len(self._source)+ i) >= self._start:
                    return self._source[i]
                else:
                    raise IndexError, i
            else:
                adjusted = (self._end - self.start) + i
                if adjusted >=0:
                    return self._source[i + self._start]
                else:
                    raise IndexError, i
                
    def __getslice__(self, i, j):
        print "LS getslice", i, j
        newStart = self._start + i
        if j == sys.maxint:
            print "Max slice, end is:", self._end            
            newEnd = self._end
        elif self._end >= 0 and j > self._end:
            raise IndexError, j
        else:
            if j >= 0:
                newEnd = self._start + j               
            else:
                newEnd = self._end + j
        return LazySlice(self._source, newStart, newEnd)
        

    def __len__(self):
        if not self.isTerminating():
            raise RuntimeError, "Non-terminating structure, cannot evaluate len()."
        if self._end >= 0:
            return self._end - self._start
        else:
            self.eval()
            return len(self)

    def __nonzero__(self):
        if self._start == self._end:
            return 0
        else:
            return 1

    def eval(self):
        if self._end < 0:
            raise RuntimeError, "Cannot eval a non-terminating sequence."
        if not self._evaluated:
            i = 0
            while 1:
                try:
                    self[i]
                    i = i + 1
                except IndexError:
                    self._evaluated = 1
                    self._end = i
                    break
        return tuple(self._source._memo[self._start:self._end])
        



def integers(index, seq, startFrom = 0, step = 1):
    """
    An index function for LazyTuples of consecutive integers.
    """
    if index == 0:
        return startFrom
    else:
        return seq[index -1] + step

def naturals(index, seq, startFrom = 1, step = 1):
    """
    An index function for LazyTuples of consecutive natural numbers.
    """
    assert startFrom > 0
    return integers(index, seq, startFrom, step)

def lazymap(func, seq):
    """
    Lazy equivalent for the map builtin function.
    lazymap returns a LazyTuple whose contents are computed on demand
    by applying *func* to seq[i], where i is the index that's being accessed.
    """
    if isinstance(seq, LazySequence):
        if seq.isTerminating():
            length = len(seq)
        else:
            length = -1
    else:
        length = len(seq)
    newItemFunc = lambda index, sequence, orig = seq, f = func:f(orig[index])
    return LazyTuple(itemFunc = newItemFunc, length = length)

def lazyfilter(func, seq):
    """
    Lazy equivalent for the filter builtin function.
    lazyfilter returns a LazyTuple whose contents are computed on demand
    by filtering as much of the original sequence as necessary to reach
    a value for the necessary index.
    """
    seqIndex = 0
    class filterhelper:
        def __init__(self, seq, seqIndex, func):
            self.seq = seq
            self.seqIndex = seqIndex
            self.func = func

        def __call__(self, index, sequence):            
            while 1:
                val = self.seq[self.seqIndex]
                self.seqIndex = self.seqIndex + 1
                if self.func(val):
                    return val
    if isinstance(seq, LazySequence):
        if seq.isTerminating():
            length = -2
        else:
            length = -1
    else:
        length = -2
    return LazyTuple(itemFunc = filterhelper(seq, seqIndex, func), length = length)

def lazyreduce(func, seq):
    """
    Lazy equivalent for the reduce builtin function.
    lazyreduce can only be applied to terminating (non-infinite) tuples.
    """
    if isinstance(seq, LazyTuple) and not seq.isTerminating():
        raise RuntimeError, "Cannot reduce infinite tuple."
    return LazyExpr("reduce(func, tuple(seq))")

def lazyzip(*seqs):
    """
    Lazy equivalent for the zip builtin function.
    """
    def newItemFunc(index, seq, origseqs = seqs):
        tup = []
        for orig in origseqs:
            tup.append(orig[index])
        return tuple(tup)
    return LazyTuple(itemFunc = newItemFunc)



def when(expr, truepart, falsepart = None, force = 0):
    """
    Functional equivalent for the if(else) statement.
    Note that unlike a real if, both truepart and falsepart will be evaluated,
    unless of couse they are Lazy. If they are lazy, only the selected
    expression will be returned. To get the selected lazy expression to be
    evaluated, call with *force* = 1 Example:

    >>> def printAndReturn(arg):
    ... 	print arg
    ... 	return arg
    ...
    >>> when(0, printAndReturn(0), printAndReturn(1))
    0
    1
    1
    #Note printAndReturn was called twice.

    >>> when(0, LazyExpr("printAndReturn(0)"), LazyExpr("printAndReturn(1)"))
    Lazy expr: printAndReturn(1)
    >>> when(0, LazyExpr("printAndReturn(0)"), LazyExpr("printAndReturn(1)"), 1)
    1
    1
    #because of the last (force) parameter, the chosen lazy expression was
    #evaluated before returning.
    >>>
    """
    if expr:
        retval = truepart
    else:
        retval = falsepart
    if isLazy(retval) and force:
        retval = retval.eval()
    return retval
