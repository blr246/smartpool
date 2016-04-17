"""
A smart resource pool.
"""
from functools import wraps
import itertools as its
import sys


def identity(x):
    """ The identity function. """
    return x


class SmartPool(object):
    """ A generalized resource pool. """

    class PoolItemContext(object):
        """ A contextmanager for a leased item belonging to a SmartPool. """

        def __init__(self, pool, args, kwargs):
            """ Store pool and arguments until __enter__() is called. """
            self._pool = pool
            self._args = args
            self._kwargs = kwargs

        def __enter__(self):
            """ Load the requested instance from the pool. """
            args, kwargs = self._args, self._kwargs
            del self._args
            del self._kwargs

            key = tuple(its.chain(sorted(args), sorted(kwargs.iteritems())))

            if key in self._pool._pool:
                value = self._pool._pool[key]
            else:
                value = self._pool._loader(*args, **kwargs)
                self._pool._pool[key] = value

            self._key = key
            self._value = value
            return self._pool._value(value)

        def __exit__(self, type, value, tb):
            """ Return the leased instance to the pool. """
            # Invalidate pool entry when the exception is a targeted type.
            if any(isinstance(value, exc) for exc in self._pool._exceptions):
                key, value = self._key, self._value
                if key in self._pool._pool and self._pool._pool[key] is value:
                    del self._pool._pool[key]

                self._pool._deleter(value)

            # Always re-raise exceptions.
            return False

    def __init__(self, loader, value=identity,
                 deleter=identity, exceptions=None):
        """
        :param function loader: function that loads a pooled value
        :param function value: function that extracts the part of the loaded
            value that we want to return from the contextmanager
        :param function deleter: function to run when an item is discarded
            from the pool either on a filtered exception type or on shutdown
        :param list[type] exceptions: exception types to filter in
            contextmanager __exit__() where a match will discard the pooled
            instance and run deleter
        """
        self._loader = loader
        self._value = value
        self._deleter = deleter
        if exceptions:
            self._exceptions = [exc for exc in exceptions]
        else:
            self._exceptions = []
        self._pool = {}

    def get(self, *args, **kwargs):
        """
        Get a contextmanager providing the requested item from the pool.

        The given arguments are forwarded to the loader function passed to
        __init__().

        Example:
            >>> with pool.get('arg1', 12345, ...) as item:
                    ...
        """
        return SmartPool.PoolItemContext(self, args, kwargs)

    def flush(self):
        """ Flush the pool. """
        for value in self._pool.itervalues():
            self._deleter(value)
        self._pool.clear()

    def __del__(self):
        """
        Delete all of the pool's held references using the supplied deleter
        function.

        N.B. Because PoolItemContext instances retain a reference to their
        owning SmartPool, this __del__() cannot be called until all
        PoolItemContext are disposed.
        """
        self.flush()


_func_to_pooled_args = {}


def _pooled(func, *args, **kwargs):
    """ Add resource pooling to a function. """

    # Sort pooling arguments and any of the values of the arguments. Assume
    # that we don't need to recurse deeper than 1 level to sort.

    pool_args = []

    for value in args:
        try:
            next(value)
            value = tuple(sorted(value))
        except TypeError:
            pass
        pool_args.append(value)

    for key, value in kwargs.iteritems():
        try:
            next(value)
            value = tuple(sorted(value))
        except TypeError:
            pass
        pool_args.append((key, value))

    pool_args = tuple(sorted(pool_args))

    # Don't pool if we've pooled already.
    if func in _func_to_pooled_args:
        if func.__module__ != '__main__':
            fn_name = '{}.{}'.format(func.__module__, func.__name__)
        else:
            fn_name = func.__name__

        # Make sure we have the same pool_args.
        if pool_args != _func_to_pooled_args[func]:
            prev_args = _func_to_pooled_args[func]
            raise ValueError((
                "Previous pooling of {fn_name}() had arguments "
                "SmartPool({fn_name}, {prev_args}) != "
                "SmartPool({fn_name}, {curr_args})"
            ).format(fn_name=fn_name,
                     curr_args=", ".join("{}={}".format(*arg) if len(arg) == 2
                                         else str(arg)
                                         for arg in pool_args),
                     prev_args=", ".join("{}={}".format(*arg) if len(arg) == 2
                                         else str(arg)
                                         for arg in prev_args)))
        return func

    pool = SmartPool(func, *args, **kwargs)

    @wraps(func)
    def wrapper(*args, **kwargs):
        return pool.get(*args, **kwargs)

    docstring_prefix = (
        "Returns a contextmanager for a pooled resource loaded from {fn}.\n"
        "\n"
        "Example:\n"
        "    >>> with {fn}(...) as pooled_resource:\n"
        "            # Use the pooled resource.\n"
        "            ...\n"
        "\n"
        "The pooled resource is managed automatically by the contextmanager"
        " and the \npool. Exceptions that hit the contextmanager scope and "
        "match the pool's\nexception filter will free the resource.\n"
    ).format(fn=func.__name__)

    if not wrapper.__doc__:
        wrapper.__doc__ = docstring_prefix
    else:
        wrapper.__doc__ = (
            docstring_prefix.format(fn=func.__name__)
            + "\n" + wrapper.__doc__)

    # Mark the function as pooled. We won't get pooled again!
    _func_to_pooled_args[wrapper] = pool_args

    return wrapper


def force_pooling(func, *args, **kwargs):
    """
    Force add resource pooling to a module-scope function.

    N.B. This will update the function where it is defined. Any imports already
    made for the function will not be pooled. To control pooling behavior at
    your project scope, apply force_pooling() at the top-level module's
    __init__.py so that all subsequent imports use the pooling override.

    :param function func: the function with values to pool
    """
    pooled_func = _pooled(func, *args, **kwargs)
    setattr(sys.modules[func.__module__], func.__name__, pooled_func)


def pooled(*args, **kwargs):
    """
    A decorator factory to pool a resource returned by a function.

    The arguments are forwarded to SmartPool.__init__() and the decorated
    function is used as the SmartPool's loader parameter.

    Note that
        >>> @pooled(exceptions=[ValueError])
            def my_func(x):
                reutrn ('item', x)

    is identical to
        >>> SmartPool(my_func, exceptions=[ValueError])

    where my_func is the decorated function. The pool is retained by pooled()
    and is invoked automatically whenever my_func is called.
    """
    def decorator(func):
        """ A decorator to pool a resource returned by a function. """
        return _pooled(func, *args, **kwargs)

    return decorator
