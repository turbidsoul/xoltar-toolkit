## functional.py provides support for a functional style of Python programming.
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

"""
functional.py provides support for a functional style of Python programming.

It includes support for curried functions, and  some higher-order functions
for composing, sequencing, and otherwise manipulating functions.
"""

from types import *
import sys
from copy import copy
import string
import operator

__version__ = "1.1.0"

if hasattr(sys, '_getframe'):
    getStackFrame = sys._getframe
else:
    def getStackFrame():
        try:
            raise RuntimeError
        except:
            return sys.exc_info()[2].tb_frame.f_back
try:
    import new
    def closure(func, locs = {}):
        """
        Returns a function whose global namespace is a **copy of** *func*'s 
        globals, augmented with the local variables of the calling function.
        This is a common requirement for functional programming. This can
        be duplicated in standard Python using default arguments, but it
        is generally more cumbersome. Note there is little reason for this
        function under Python 2.1, which provides this capability directly.

        Example:

        #A function which returns a function which returns 1 if an item is
        #in *sequence*, 0 otherwise
        def contained(sequence):    
            def contained_helper(x):
                return x in sequence
            return closure(contained_helper)

        >>>lst = [1,2,3]
        >>>is123 = contained(lst)
        >>>is123(2)
        1
        >>>


        #An example of 'static' variables, somewhat like in C:
        def bindCallCount(func):
            callCount = ref(0)
            return closure(func)

        #Note this function uses a variable, callCount, that is not defined.
        def printAndIncrement():
            print callCount.val
            callCount.val = callCount.val + 1

        #But with closures, we can make this function work:
        >>>printAndInc = bindCallCount(printAndIncrement)
        >>>printAndInc()
        0
        >>>printAndInc()
        1    
        >>>

        So callCount is preserved across function invocations, but is not taking
        up space in the module namespace.
        """
        frame = getStackFrame().f_back
        if not locs:
            locs = frame.f_locals
        globs = {}
        globs.update(func.func_globals)
        globs.update(locs)
        newfunc = new.function(func.func_code, globs)
        globs[func.__name__] = newfunc
        return newfunc
except:
    pass

if sys.version_info[0] >= 2 and sys.version_info[1] >= 1:
    del closure
    def closure(func, locs = None):
        return func
    
class Ref:
    """
    A simple class to hold a value. Useful when one wishes to share a value
    between functions, or otherwise access the value from a local scope without
    using a 'global' statement to avoid rebinding the name locally.
    """
    def __init__(self, val):
        self.val = val

class Blank:
    """
    When passed in a call to curry, or to a curried function, this is treated as a placeholder
    for future calls to replace.
    """
    pass

def blend(func, original, mix):
    """
    This function returns a list based on *original*, with any elements that
    *func* returns nonzero for replaced one by one with items from *mix*.
    Any unused items in *mix* appear at the end of the new list. If there are
    items which should be replaced, but there are no more items in *mix*, then
    those items are left unchanged.
    """
    mixIndex = 0
    build = []
    mixlen = len(mix)
    for item in original:
        if mixIndex < mixlen and func(item):
            build.append(mix[mixIndex])
            mixIndex = mixIndex + 1
        else:
            build.append(item)
    if mixIndex < mixlen:
        build.extend(list(mix[mixIndex:]))
    return build


class FuncMethUnion:
    """
    This utility class exposes instance methods and functions identically.
    """
    class MethCode:
        def __init__(self, code):
            self._code = code

        def __getattr__(self, name):
            if name == 'co_argcount':
                return self._code.co_argcount - 1
            elif name == 'co_varnames':
                return self._code.co_varnames[1:]
            else:
                return getattr(self._code, name)

    def __init__(self, func):
        if type(func) == ClassType:
            if hasattr(func, '__init__'):
                #If this is a class, replace with the __init__ function
                func = getattr(func, '__init__')
            else:
                #No constructor, so we have to define a helper of our own
                #that will masquerade as the __init__ method.
                def helper():
                    pass
                func = helper
        self._methcode = None
        self._func = func

    def __getattr__(self, name):
        if name [0] == '_' and not name in ('__doc__', '__name__'):
            raise AttributeError, name
        if hasattr(self._func, name):
            return getattr(self._func, name)
        if hasattr(self._func, 'im_func'):
            if name == 'func_code':
                if self._func.im_self or self._func.__name__ == '__init__':
                    if not self._methcode:
                        self._methcode = self.MethCode(self._func.im_func.func_code)
                    return self._methcode
                else:
                    return self._func.im_func.func_code                
            return getattr(self._func.im_func, name)
        raise AttributeError, name


class SimCode:
    """
    Holds some of the same attributes a code object would have, for
    the benefit of functions like curry that work better when they
    have the information that code objects provide.
    """
    def __init__(self, functor):
        self._func = functor

    def __getattr__(self, name):
        if name == 'co_name':
            return self._func.func_name
        elif name == 'co_names':
            return self._func.getNames()
        elif name == 'co_argcount':
            return self._func.getArgCount()
        elif name == 'co_code':
            return None
        elif name == 'co_varnames':
            return self._func.getVarNames()
        elif name == 'co_flags':
            return self._func.getFlags()

        elif len(name) > 3 and name[:3] == 'co_':
            return getattr(self._func.__call__.func_code, name)
        raise AttributeError, name

class Functor:
    """
    A class to assist functors (callable class instances) in masquerading
    as functions, by providing much of the material needed by code which
    introspects functions for useful information (curry being the main
    example in this module). A functor can simply inherit from this class,
    and override any of the methods below to provide more accurate information
    if it is available.
    """
    def __init__(self, func = None):
        if not func:
            func = self.__call__
        self._func = func
        self._significant_func = FuncMethUnion(func)

    def __call__(self):
        raise NotImplementedError

    def getName(self):
        return self.__class__.__name__

    def getDefaults(self):
        try:
            return self._significant_func.func_defaults
        except:
            return None

    def getDoc(self):
        return self.__class__.__doc__

    def getNames(self):
        return self._significant_func.func_code.co_names

    def getVarNames(self):
        return self._significant_func.func_code.co_varnames

    def getArgCount(self):
        return self._significant_func.func_code.co_argcount

    def getFlags(self):
        return self._significant_func.func_code.co_flags

    def __getattr__(self, name):
        if name == "func_code":
            self.func_code = SimCode(self)
            return self.func_code
        elif name == "func_doc":
            return self.getDoc()
        elif name == "func_defaults":
            return self.getDefaults()
        elif name == "func_globals":
            return self.__call__.func_globals
        elif name == "func_name":
            return self.getName()
        raise AttributeError, name

    def __lshift__(self, other):
        return curry(self, other)

    def __rlshift__(self, other):
        return curry(other, self)

    def __add__(self, other):
        return also(self, other)

    def __radd__(self, other):
        return also(other, self)

    def __or__(self, other):
        return disjoin(self, other)

    def __ror__(self, other):
        return disjoin(other, self)

    def __and__(self, other):
        return conjoin(self, other)

    def __rand__(self, other):
        return conjoin(other, self)

    def __mul__(self, other):
        return compose(self, other)

    def __rmul__(self, other):
        return compose(other, self)

    def __not__(self):
        print "NOT!"
        return complement(self)

class wrap(Functor):
    """
    Convenience class which wraps up a function in a Functor so that
    it can be used with the functional operators.
    """
    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)
    
class curry(Functor):
    """
    A curried function (named after the person who pioneered the idea,
    Haskell Currry) is one which some arguments are already defined,
    something like default arguments in Python, but much more
    general. When you curry a function with some arguments, the
    result is a function which requires only those arguments that
    haven't been supplied already. For example:

    def addTwo(x, y):
        return x + y

    addFive = curry(addTwo, 5)

    Now addFive is a function which takes one argument, and returns
    that argument added to 5, since x is pre-bound to 5 by the curry().

    In functional languages, currying must take place either from the
    beginning of the argument list, or the end (this is sometimes called
    an rcurry, or reverse curry). In Python, with keyword arguments,
    and *args and **kwargs, the situation is a little more complicated,
    so these are the rules:

    - All currying starts from the left side of the argument list.
    - Keyword arguments can be curried.
    - If you wish to supply an argument that occurs later in the
      paramter list without supplying the one before it, you can
      supply the special value Blank in the places you don't want
      filled. For example:
          addFive = curry(addTwo, Blank, 5)
      would result in the 5 argument being bound to y instead of x.

    If curry() can determine the minimum number of arguments for the
    function (func.func_code.co_argcount is present), then calls to
    the curried function with fewer than the remaining required arguments
    will only return a new curried function with the new arguments
    bound as well. For example:

    def threeArgs(x, y, z):
        return x + y + z

    twoArgs = curry(threeArgs, 5)

    Now twoArgs is a function which takes two arguments, and adds them to 5.
    If we now do:

    NewThing = twoArgs(20)

    NewThing is now a function which takes one argument, and returns that value
    plus 20 + 5. As soon as the function has accumulated enough arguments to
    reach the required argument count of the original function, the original
    function is called with all the accumulated arguments.

    In the case of explicity calling curry, however, if all arguments are
    supplied, the function is not called, rather a no-arguments function is
    returned. For example:

    oneArg = curry(twoArgs, 5)
    oneArg(5)

    would result in a call to twoArgs with arguments 5, 5. However:

    noArgs = curry(twoArgs, 5, 5)

    does not call twoArgs, until noArgs is called:

    noArgs()

    which again calls twoArgs, passing 5, 5 as the arguments.

    When applied to a function which has default arguments, only a number of
    arguments equal to the number of basic (non-defaulted) paramters will be
    required before the function is executed. For example:

    >>> def defaultTest(x, y, z, q = 4):
    ... 	return x, y, z, q
    ...
    >>> c = curry(defaultTest, 1, 2, 3)
    >>> c()
    (1, 2, 3, 4)
    >>>

    Of course, this doesn't prevent default arguments from being supplied either
    initially or at a later time, so long as that minimum count hasn't been met.
    Example:
    >>> c = curry(defaultTest, 1)
    >>> c(q = 7)
    <functional.curry instance at 1317a70>
    >>> c(2,3)
    (1, 2, 3, 4)
    >>>
    """
    def __init__(self, func, *args, **kwargs):
        Functor.__init__(self, func)
        self._args = args
        self._kwargs = kwargs
        
    def getArgCount(self):
        basic = Functor.getArgCount(self)
        filterArgs = filter(lambda x:not x is Blank, self._args)
        filterKwargs = filter(lambda x:not x is Blank, self._kwargs.values())
        adjusted = basic - (len(filterArgs) + len(filterKwargs))
        return max(adjusted, 0)


    def getVarNames(self):
        varnames = Functor.getVarNames(self)
        varnames = varnames[len(self._args):]
        names = []
        for name in varnames:
            if not self._kwargs.has_key(name):
                names.append(name)
        return tuple(names)

    def __call__(self, *args, **kwargs):
        buildArgs = blend(lambda x:x is Blank, self._args, args)
        buildKwargs = self._kwargs.copy()
        buildKwargs.update(kwargs)
        hasblank = Blank in buildArgs or Blank in buildKwargs.values()
        argcount = 0
        try:
            argcount = self.getArgCount()
            defs = self.getDefaults()
            if defs:
                argcount = argcount - len(defs)
        except:
            pass
        argcount = argcount - len(args)
        if hasblank or (argcount > 0):
            cur = curry(self._func)
            cur._args = buildArgs
            cur._kwargs = buildKwargs
            return cur
        else:
            return apply(self._func, tuple(buildArgs), buildKwargs)

class rcurry(Functor):
    """
    *rcurry* works much like *curry*, but applies its arguments to the
    other end of the argument list. Note that rcurry does not work on
    callables which provide no information about the number of arguments
    they take (such as builtin functions), nor does it work on ones
    with default or open ended (*args, **kwargs) arguments.
    For example:
    >>> def threeArgs(x, y, z):
    ... 	return x, y, z
    ...
    >>> rc = rcurry(threeArgs, 2, 3)
    >>> rc(1)
    (1, 2, 3)
    >>>
    """
    def __init__(self, func, *args, **kwargs):
        Functor.__init__(self, func)
        self._args = []
        self._kwargs = kwargs
        try:
            self.getArgCount()
        except:
            raise RuntimeError, "No info about number of args on func, use curry with Blanks instead."
        argcount = Functor.getArgCount(self)
        defs = Functor.getDefaults(self)
        if defs:
            raise RuntimeError, "Use curry with keyword arguments for callables which take keyword arguments"
        if self.getFlags() & 4:
            raise RuntimeError, "Use curry for callables which take a variable number of arguments"
        if self.getFlags() & 8:
            raise RuntimeError, "Use curry for callables which take a variable number of keyword arguments"
        argdiff = argcount - len(args)
        if argdiff >= 1:
            self._args = ((Blank,) * argdiff) + args
        else:
            self._args = args

    def getArgCount(self):
        basic = Functor.getArgCount(self)
        filterArgs = filter(lambda x:not x is Blank, self._args)
        filterKwargs = filter(lambda x:not x is Blank, self._kwargs.values())
        adjusted = basic - (len(filterArgs) + len(filterKwargs))
        return max(adjusted, 0)

    def getVarNames(self):
        varnames = Functor.getVarNames(self)
        varnames = varnames[:len(varnames) - len(filter(lambda x:not x is Blank, self._args))]
        names = []
        for name in varnames:
            if not self._kwargs.has_key(name):
                names.append(name)
        return tuple(names)

    def getDefaults(self):        
        defs = Functor.getDefaults(self)
        if defs:
            defs = defs[:len(defs) - len(filter(lambda x:not x is Blank, self._args))]
        if not defs:
            defs = None
        return defs

    def __call__(self, *args, **kwargs):
        buildArgs = blend(lambda x:x is Blank, self._args, args)
        buildKwargs = self._kwargs.copy()
        buildKwargs.update(kwargs)
        hasblank = Blank in buildArgs or Blank in buildKwargs.values()
        argcount = 0
        try:
            argcount = self.getArgCount()
            defs = self.getDefaults()
            if defs:
                argcount = argcount - len(defs)
        except:
            pass
        argcount = argcount - len(args)
        if hasblank or (argcount > 0):
            cur = curry(self._func)
            cur._args = buildArgs
            cur._kwargs = buildKwargs
            return cur
        else:
            return apply(self._func, tuple(buildArgs), buildKwargs)
        
class compose(Functor):
    """
    Takes any number of functions, and when called, applies them in
    reverse order. The first function to be called (the last to be passed
    in the call to compose()) is called with the arguments, and the
    other functions are called with the results of the previous function
    as its arguments. For example:

    def f(x):
        return x * 2

    def g(x):
        return x + 5

    h = compose(f, g)

    h(3) will now equal f(g(3)), or 16.
    """
    def __init__(self, *args):
        Functor.__init__(self, args[-1])
        args = list(args)
        if not all(args, callable):
            raise TypeError, "All arguments must be callable."
        args.reverse()
        self._funcs = args

    def __call__(self, *args, **kwargs):
        ret = apply(self._funcs[0], args, kwargs)
        for func in self._funcs[1:]:
            ret = func(ret)
        return ret

class applycompose(compose):
    def __call__(self, *args, **kwargs):
        ret = apply(self._funcs[0], args, kwargs)
        for func in self._funcs[1:]:
            ret = self.__fixret(func(*ret))
        return ret
    
    def __fixret(self, ret, TupleType=type(())):
        if type(ret) is not TupleType:
            ret = (ret,)
        return ret
  
class joinfuncs(Functor):
    """
    Takes a number of functions, and returns a function which, when called,
    returns a tuple of all the values the original functions would return
    if called with those arguments. Example:

    def timesFive(x):
        return x * 5

    def square(x):
        return x * X

    >>>myfunc = joinfuncs(timesFive, square, str)
    >>>myfunc(2)
    (10, 4, '2')

    """
    def __init__(self, *args):
        Functor.__init__(self, args[0])
        if not all(args, callable):
            raise TypeError, "All arguments must be callable."
        self._funcs = args

    def __call__(self, *args, **kwargs):
        lst = []
        for func in self._funcs:
            lst.append(apply(func, args, kwargs))
        return tuple(lst)


class complement(Functor):
    """
    When called, returns the logical not of a call to *func* with the same
    arguments.
    """
    def __init__(self, func):
        Functor.__init__(self, func)

    def __call__(self, *args, **kwargs):
        return not apply(self._func, args, kwargs)

class disjoin(Functor):
    """
    Takes the functions *funcs*, and when called will return 1 if any of
    *funcs* returns nonzero when applied to the arguments the disjoin was called with.
    This is basically equivalent to logical or-ing calls to all the functions in *funcs*.
    Note that if one function returns nonzero, the remaining functions are not
    evaluated. Example:

    #We need to find whether something is a sequence, other than a string.
    isTuple = lambda x:type(x) == type(())
    isList = lambda x:type(x) == type([])
    isUserSeq = lambda x:hasattr(x, '__getslice__')

    isSequence = disjoin(isTuple, isList, isUserSeq)
    """
    def __init__(self, *funcs):
        Functor.__init__(self, funcs[0])
        if not all(funcs, callable):
            raise TypeError("All arguments must be callable.")
        self._funcs = funcs

    def __call__(self, *args, **kwargs):
        for func in self._funcs:
            if apply(func, args, kwargs):
                return 1
        return 0

class conjoin(Functor):
    """
    Takes the functions *funcs*, and when called will return 1 if all of
    *funcs* return nonzero when applied to the arguments the conjoin was called with.
    This is basically equivalent to logical and-ing all the functions in *funcs*.
    Note that if a function returns a false (not nonzero) result, the remaining
    functions are not evaluated.
    Example:

    #Function to decide if a number is greater than 5 and less than 10...
    gt5 = lambda x:x > 5
    lt10 = lambda x:x < 10

    between_5_and_10 = conjoin(gt5, lt10)
    """
    def __init__(self, *funcs):
        Functor.__init__(self, funcs[0])
        if not all(funcs, callable):
            raise TypeError, "All arguments must be callable."
        self._funcs = funcs
    def __call__(self, *args, **kwargs):
        for func in self._funcs:
            if not apply(func, args, kwargs):
                return 0
        return 1


class sequential(Functor):
    """
    Take a number of functions, and when called, call each of them in turn. The
    first function in the list is the "main", or significant function, and the
    others are taken for side-effects only. Their return values do not affect
    the return value of the also function, and any errors they raise are
    silently disregarded. If a function is explicity specified via the *main*
    parameter, that function will be the one whose return value is used, regardless
    of where in the sequence it appears. Example:
    >>> def one():
    ...     print "one"
    ...     return 1
    ...
    >>> def two():
    ...     print "two"
    ...     return 2
    ...
    >>> def three():
    ...     print "three"
    ...     return 3
    ...
    >>> x = one()
    one
    >>> x
    1
    >>> x = sequential([one, two, three])()
    one
    two
    three
    >>> x
    1
    >>>
    >>> x = sequential([one, two, three], main = three)()
    one
    two
    three
    >>> x
    3
    >>>

    """
    def __init__(self, funcs, main = None):
        if not all(funcs, callable):
            raise TypeError, "All arguments must be callable."
        self._funcs = funcs
        if not main:
            main = funcs[0]
        Functor.__init__(self, main)
        self._main = main

    def __call__(self, *args, **kwargs):
        for func in self._funcs:
            if func is self._main:
                ret = apply(func, args, kwargs)
            else:
                try:
                    apply(func, args, kwargs)
                except:
                    pass
        return ret

def also(*args):
    """
    Handles the common case for **sequential**, in which the first function
    passed is the significant one. It takes free arguments instead of a single
    sequence argument. Example:
    >>> def one():
    ...     print "one"
    ...     return 1
    ...
    >>> def two():
    ...     print "two"
    ...     return 2
    ...
    >>> def three():
    ...     print "three"
    ...     return 3
    ...
    >>> one()
    one
    1
    >>> x = one()
    one
    >>> x
    1
    >>> x = also(one, two, three)()
    one
    two
    three
    >>> x
    1
    >>> x = also(two, one, three)()
    two
    one
    three
    """
    return sequential(args)

class always(Functor):
    """
    Returns a callable which always returns a given object.
    Example:
    >>> f = always(5)
    >>> f()
    5
    >>>
    """
    def __init__(self, object):
        Functor.__init__(self)
        self._object = object

    def __call__(self, *args, **kwargs):
        return self._object

class any_args(Functor):
    """
    Returns a callable which will take any arguments, and ignore them,
    calling *func* with no arguments. Useful with map(), or in the common
    case of GUI event handlers which need to accept an event parameter,
    but do not use it. Example:

    >>> def return5():
    ...     return 5
    ...
    >>> return5("unneeded", "unnecessary")
    Traceback (innermost last):
      File "<stdin>", line 1, in ?
    TypeError: no arguments expected
    >>> f = any_args(return5)
    >>> f("unneeded", "unnecessary")
    5
    >>>
    """
    def __call__(self, *args, **kwargs):
        return self._func()

class error_handler(Functor):
    """
    Takes a function, and either a function or some piece of data (or None,
    by default). This error_handler instance, when called, calls the first
    function. If any errors are raised, the second function is called,
    passing it sys.exc_info(). Whatever the second function returns is used
    as the final return value. If the second argument is not callable, then
    it is simply returned.
    If the error-handler function re-raises the exception (or another),
    the exception will propagate back to the caller. It is possible to
    chain error-handlers together with **attempt**, below.
    Example:
    >>> from operator import div
    >>> div(1/0)
    Traceback (innermost last):
      File "<stdin>", line 1, in ?
    ZeroDivisionError: integer division or modulo
    >>> def recover(exc):
    ...     return sys.maxint
    ...
    >>> safediv = error_handler(div, recover)
    >>> safediv(1, 0)
    2147483647
    >>> safediv2 = error_handler(div, sys.maxint)
    >>> safediv2(1, 0)
    2147483647
    
    """

    def __init__(self, func, errorfunc = None):
        Functor.__init__(self, func)
        if not callable(func):
            raise TypeError, "First argument to error_handler must be callable"
        self._errorfunc = errorfunc

    def __call__(self, *args, **kwargs):
        try:
            return apply(self._func, args, kwargs)
        except:
            exc_info = sys.exc_info()
            try:
                if callable(self._errorfunc):
                    return self._errorfunc(exc_info)
                else:
                    return self._errorfunc                
            except:
                raise exc_info[0], exc_info[1], exc_info[2]

def trap_error(func, on_error = None):
    """
    Where error_handler builds a new functor with built-in error handling
    capability, this function calls *func* immediately, and calls *on_error*
    if it is callable, passing it sys.exc_info(), or returns *on_error*
    if it is not callable.
    Example:
    >>> trap_error(lambda:1/0, "Yup")
    'Yup'
    >>> trap_error(lambda:1/0, lambda x: x[1])
    <exceptions.ZeroDivisionError instance at 007A73FC>
    >>>    
    """
    try:
        return func()
    except:
        if callable(on_error):
            return on_error(sys.exc_info())
        else:
            return on_error

    
class attempt(Functor):
    """
    Given a function sequence, attempt to call and return each in turn. The
    return value of the first function to successfully return is returned.
    Errors are silently ignored. This could be used to implement something
    like the pattern matching techniques used in functional languages. A
    common use would be attaching error handlers to functions after the
    fact. Suppose we want a want a version of the div() function that returns
    sys.maxint when we attempt to divide by zero, and zero if we attempt to
    divide by something other than a number as in this example:
    >>> def zeroHandler(exc_info):
    ...     exc = exc_info[1]
    ...     if isinstance(exc, ZeroDivisionError):
    ...             return sys.maxint
    ...     else:
    ...             raise
    ...
    >>> safediv = with_error(div, zeroHandler)
    >>> safediv(1, 0)
    2147483647
    >>> def typeHandler(exc_info):
    ...     exc = exc_info[1]
    ...     if isinstance(exc, TypeError):
    ...             return 0
    ...     else:
    ...             raise
    ...
    >>> safediv = with_error(div, attempt(zeroHandler, typeHandler))
    >>> safediv(1,0)
    2147483647
    >>> safediv(1, "abc")
    0
    >>>
    """
    def __init__(self, *funcs):
        Functor.__init__(self, funcs[0])
        if not all(funcs, callable):
            raise TypeError, "All arguments must be callable."
        self._funcs = funcs

    def __call__(self, *args, **kwargs):
        for func in self._funcs:
            try:
                return apply(func, args, kwargs)
            except:
                pass


def even(x):
    """
    Returns 1 if x is even, 0 otherwise.
    """
    return x % 2 == 0

def positive(x):
    """
    Returns 1 if x is positive, 0 otherwise.
    """
    return x > 0

def negative(x):
    """
    Returns 1 if x is negative, 0 otherwise.
    """
    return x < 0



def any(sequence, test_func = None):
    """
    Returns 1 if for any member of a sequence, test_func returns a non-zero
    result. If test_func is not supplied, returns 1 if any member of the
    sequence is nonzero (e.g., not one of (), [], None, 0).
    """
    for item in sequence:
        if test_func:
            if test_func(item):
                return 1
        elif item:
            return 1
    return 0

def all(sequence, test_func = None):
    """
    Returns 1 if for all members of a sequence, test_func returns a non-zero
    result. If test_func is not supplied, returns 1 if all members of the
    sequence are nonzero (i.e., not one of (), [], None, 0).
    """
    for item in sequence:
        if test_func:
            if not test_func(item):
                return 0
        elif not item:
            return 0
    return 1

none_of = complement(any)
none_of.__doc__ = """
none_of(sequence, test_func = None)
Returns 1 if for every element in *sequence*, test_func returns false.
If test_func is not supplied, returns 0 if all members of the sequence
are nonzero (i.e., not one of (), [], None, 0), and 1 otherwise.
"""

def head(sequence):
    """
    Returns the first element of a sequence.
    """
    return sequence[0]

def tail(sequence):
    """
    Returns the slice of *sequence* containing all elements after the first.
    """
    return sequence[1:]

car = head
cdr = tail
class BindingError(StandardError):
    pass

class Bindings:
    """
    Binding establishes an immutable mapping between names and values.
    Functions which rely on normal module (or other) bindings can be
    accidentally sabotaged if the name is rebound. Since the bindings
    on a Bindings object cannot be changed, they are a somewhat safer means
    of providing context.
    >>> let = Bindings()
    >>> let.x = 5
    >>> let.y = 10
    >>> let.add_xyz = lambda z, let = let: let.x + let.y + z
    >>> let.add_xyz(5)
    20
    >>> let.x = 2
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
      File "functional.py", line 855, in __setattr__
        raise RuntimeError, "Binding cannot be re-bound."
    RuntimeError: Binding cannot be re-bound.
    >>>
    """
    
    def __setattr__(self, name, value):
        if self.__dict__.has_key('__hidden_' + name):
            raise BindingError, "Binding '%s' cannot be modified." % name
        else:
            self.__dict__['__hidden_' + name] = value

    def __getattr__(self, name):
        if self.__dict__.has_key('__hidden_' + name):
            return self.__dict__['__hidden_' + name]
        else:
            raise AttributeError
            
def namespace(bindings):
    """
    Given a Bindings object, return a dictionary with a snapshot of the current
    bindings suitable for use with eval().
    """
    return mapdict(
        lambda (key, value):(key[len('__hidden_'):], value),
            bindings.__dict__)

def mapdict(itemfunc, dictionary):
    """
    Much like the builtin function 'map', but works on dictionaries.
    *itemfunc* should be a function which takes one parameter, a (key,
    value) pair, and returns a new (or same) (key, value) pair to go in
    the dictionary.
    """
    return dict(map(itemfunc, dictionary.items()))
    

def filterdict(itemfunc, dictionary):
    """
    Filters a dictionary like 'filter' filters a list. *itemfunc*
    should be a function which takes two parameter, a(key, value) pair
    and returns 1 if the pair should be in the new dictionary,
    0 otherwise.
    """
    return dict(filter(itemfunc, dictionary.items()))

def invertdict(dictionary):
    """
    Takes a dictionary and returns a new one, with the keys and values
    exchanged.
    """
    return mapdict(lambda (key, value):(value, key), dictionary)

def dict(*args, **kwargs):
    """
    Takes arguments and builds a dictionary from them. The actual arguments
    can vary widely. A single list of (key, value) pairs, or an unlimited
    number of (key, value) pairs may be passed. In addition, any number of
    keyword arguments may be passed, which will be added to the dictionary
    as well.
    """
    dict = {}
    if len(args) == 1:
        listOfPairs = args[0]
    else:
        listOfPairs = args
    for key, value in listOfPairs:
        dict[key] = value
    dict.update(kwargs)
    return dict

def error(err, arg = None, trace = None):
    """
    A function which allows an error to be raised within a lambda
    or other expression. For example:
    >>> f = lambda x:   (x == 3 and "Three!") \
    ...              or (x == 5 and "Five!") \
    ...              or error(RuntimeError)
    >>>
    >>> f(3)
    'Three!'
    >>> f(5)
    'Five!'
    >>> f(6)
    Traceback (most recent call last):
      File "<stdin>", line 1, in ?
      File "<stdin>", line 1, in <lambda>
      File "functional.py", line 874, in error
        raise err
    RuntimeError
    >>>    
    """
    if trace:
        raise err, arg, trace
    elif arg:
        raise err, arg
    else:
        raise err
    #It would be nice to do:
##        #Here we catch the error to remove ourselves from the
##        #traceback, and then re-raise.
##        clazz, inst, tb = sys.exc_info()
##        tb.tb_frame = tb.tb_frame.f_back
##        raise clazz, inst, tb
    #But we can't because traceback objects don't have writable attributes.

def do(*args):
    """
    Returns the last argument passed to it. This is useful because
    arguments are evaluated from left to right before a function call.
    This can enable "imperative" style in a lambda expression. For example:    
    """
    return args[-1]
    
        
class dispatch(Functor):
    """
    Given a name, find and call a method with that name on a passed-in argument.
    """
    def __init__(self, name):
        self._name = name
        Functor.__init__(self, None)

    def bind(self, obj):
        self._func = getattr(obj, self._name)

    def __call__(self, *args, **kwargs):
        if not self._func:
            self.bind(args[0])
        Functor.__call__(self, args[1:], **kwargs)
        
        
                
