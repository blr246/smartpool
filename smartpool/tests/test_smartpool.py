"""
Tests for smartpool.
"""
from operator import itemgetter
from random import shuffle

import pytest

from smartpool.smartpool import SmartPool, force_pooling, pooled


class SpecialException01(Exception):
    """ Special exception type. """
    pass


class SpecialException02(Exception):
    """ Special exception type. """
    pass


_deleted_things = []


def _deleter(value):
    """ Append deleted things for debugging. """
    if _deleted_things is not None:
        _deleted_things.append(value)


def _test_state_gen(getter, exceptions):
    """
    A sequence of test operations on a particular value.

    We yield after every `with` statement so that the test execution pauses.
    This way, the outer test scope can interleave the test state for
    different values.

    N.B. Your test case must use _deleter as the deleter or else these test
    cases will fail to match in cases where items are discarded.
    """

    class DerivedException(exceptions[0]):
        """ Derived from exception type. """
        pass

    # Initialize item.
    with getter() as item:
        yield item
        prev_item = item

    # Repeat resource requests yield the same item.
    with getter() as item:
        assert item is prev_item
        yield item
        with getter() as item:
            assert item is prev_item
            yield item
            with getter() as item:
                assert item is prev_item
                yield item

    # Exception generates different item.
    for exc_type in exceptions + [DerivedException]:
        try:
            with getter() as item:
                yield item
                raise exc_type()
        except exc_type:
            assert _deleted_things[-1][1] is prev_item
            with getter() as item:
                assert item is not prev_item
                yield item
                prev_item = item

    # Non-filtered exception type does nothing.
    for _ in range(5):
        try:
            with getter() as item:
                assert item is prev_item
                yield item
                raise Exception()
        except Exception:
            pass


@pooled()
def my_pooled_loader(x):
    """ Load something. """
    return ('loaded', (x))


def test_simple_pool():
    """ Test a simple pool. """

    def my_loader(x):
        """ Load something. """
        return ('loaded', (x, 0, 1, 2))

    pool = SmartPool(my_loader)

    for x in range(10):
        with pool.get(x) as item:
            assert isinstance(item, tuple)
            assert item == ('loaded', (x, 0, 1, 2))

    pool = SmartPool(my_loader,
                     value=itemgetter(1))

    for x in range(10):
        with pool.get(x) as item:
            assert isinstance(item, tuple)
            assert item == (x, 0, 1, 2)


def _run_interleaved_tests(getter, exceptions, num_tests=11):
    """ Run a set of interleaved tests. """
    tests = [_test_state_gen(getter(x), exceptions) for x in range(num_tests)]
    operations = 0
    while tests:
        # Shuffle, advance, discard if done. This interleaves the tests.
        shuffle(tests)
        test = tests[-1]
        try:
            next(test)
            operations += 1
        except StopIteration:
            tests.pop()

    assert operations % num_tests == 0


def test_pool():
    """ Test a simple instantiated pool. """

    def my_loader(x):
        """ Load something. """
        return ('loaded', (x, 0, 1, 2))

    exceptions = [SpecialException01, SpecialException02]
    pool = SmartPool(my_loader,
                     value=itemgetter(1),
                     deleter=_deleter,
                     exceptions=exceptions)

    def getter(x):
        def func():
            return pool.get(x)
        return func

    _run_interleaved_tests(getter, exceptions)


def module_scoped_loader(x):
    """ Load something. """
    return ('loaded', (x, 0, 1, 2))


def test_force_pooled():
    """ Test a forced loader function. """

    value = itemgetter(1)
    exceptions = [SpecialException01, SpecialException02]

    force_pooling(module_scoped_loader,
                  value=value,
                  deleter=_deleter,
                  exceptions=exceptions)

    def simple_test():
        with module_scoped_loader(5) as item:
            assert isinstance(item, tuple)
            assert item[0] == 5

    simple_test()

    def getter(x):
        def func():
            return module_scoped_loader(x)
        return func

    _run_interleaved_tests(getter, exceptions)

    # Allow force pooling again with the same args.

    force_pooling(module_scoped_loader,
                  value=value,
                  deleter=_deleter,
                  exceptions=exceptions)

    simple_test()

    # Don't allow pooling with different args.

    try:
        force_pooling(module_scoped_loader,
                      deleter=_deleter,
                      exceptions=exceptions)
    except ValueError:
        pass

    try:
        force_pooling(module_scoped_loader,
                      value=value,
                      deleter=_deleter,
                      exceptions=list(reversed(exceptions)))
    except ValueError:
        pass

    simple_test()


def test_pooled():
    """ Test a decorated loader function. """

    exceptions = [SpecialException01, SpecialException02]

    @pooled(value=itemgetter(1),
            deleter=_deleter,
            exceptions=exceptions)
    def my_loader(x):
        """ Load something. """
        return ('loaded', (x, 0, 1, 2))

    def getter(x):
        def func():
            return my_loader(x)
        return func

    _run_interleaved_tests(getter, exceptions)


if __name__ == '__main__':
    pytest.main()
