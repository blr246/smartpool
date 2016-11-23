smartpool
=========
A library for resource pooling in Python.

Introduction
------------
Resource pooling is a common pattern during application programming whereby
objects such as server connections, large buffers, and other resource-intensive
things should be captured and re-used rather than reinitialized at every
statement where they are referenced.

Resource pooling abstracts away from the client the management of such
instances. This library supports an explicit pattern of initializing pools or a
decorator pattern that marks function return values as pooled.

It's helpful to think of the resource pool as a key-value store where they key
is the arguments to the initializer function and the value is the function
return value for those arguments.

Getting started
---------------
Pooling with `SmartPool` is simple.

```Python
from importantlib import ResourceIntensiveThing, foo_loader
from otherlib import expensive_connection_maker
from smartpool import SmartPool, pooled, force_pooling

# Here, mark pooled a function that makes a thing.
@pooled()
def my_pooled_thing(something):
    """ Makes a thing. Whoof, what a task! """
    return ResourceIntensiveThing(something)

# Here's some mischief: we'll pool expensive connections for all clients in
# this application. Boy, will they be surprised.
force_pooling(expensive_connection_maker)

def main():
    """ I'm about to run this program! """

    # We pool foos because they're expensive to make and re-usable.
    pool = SmartPool(foo_loader)

    ...

    while True:

        # Get the requested foo.
        request = conn.read()
        foo = pool.get(request)

        ...
```

Further comments
----------------
It's preferable to pool resources at the application level since library
designers cannot anticipate that clients will need pooling, nor can they
account for identical resource instance needs across libraries.
