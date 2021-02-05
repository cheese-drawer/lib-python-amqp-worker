# AMQP Worker Lib

A simple wrapper on [mosquito/aio-pika](https://github.com/mosquito/aio-pika) that exposes a Flask-like API for setting up workers to listen to (& sometimes respond to) messages sent via AMQP 0-9-1.

## Installation

Install with `pip` from `main` on this repo:

```
$ pip install git+https://github.com/cheese-drawer/lib-python-amqp-worker.git
```

## Usage

This library uses a very simple, Flask-like API to create a worker, add handlers to a worker, and then run the worker.
Handlers are required to be asynchronous and running the worries has to happen inside an async event loop.

There are two worker classes, `QueueWorker` & `RPCWorker`, each conforming to a different AMQP communication pattern ([work queues](https://www.rabbitmq.com/tutorials/tutorial-two-python.html) & [remote procedure call](https://www.rabbitmq.com/tutorials/tutorial-six-python.html), respectively).
Each class is used nearly exactly the same way, differing only in one key way (as far as usage goes): `RPCWorker` routes send a `Response`, while `QueueWorker` routes do not (more on that below).

Finally, the library includes a `ConnectionParameters` dataclass to help with defining the data necessary to connect to your broker (host, port, username, and password).

Putting it all together is fairly straightforward. Start by initializing a new worker, passing it your brokers connection parameters on init, then make some routes, and end by starring the worker in an asynchronous event loop:

```
import asyncio

from amqp_worker import ConnectionParameters, QueueWorker

# define broker connection data
connection_parameters = ConnectionParameters(
    host='localhost',
    port=5672,
    user='guest',
    password='guest')
# create Worker
worker = QueueWorker(connection_parameters)


# define a "route" on the worker
# messages published to a queue with the
# name given to `route` will be handled by
# the decorated function
@worker.route('a-queue')
def handler(data: str) -> None:
  print(f'data received {data}')

# run worker by getting an event loop,
# starting up the worker in the loop,
# then listen for messages in a run_forever
# loop
loop = asyncio.get_event_loop()

# QueueWorker.run returns a function that
# stops the worker, save it for later
stop_worker = loop.run_until_complete(worker.run())

# wrap run_forever in try block to catch
# KeyboardInterrupt to kill the loop
try:
    loop.run_forever()
except KeyboardInterrupt:
    loop.run_until_complete(stop_worker ())
    loop.close()
```

Using an `RPCWorker` is almost exactly the same.
Just initialize an `RPCWorker` exactly the same way as a `QueueWorker`, then define a route, this time with a handler that returns a result.
That return value is the data that will be sent back in the response to the original caller.

```
...

worker = RPCWorker(connection_params)

@worker.route('a-route')
def handler(data: str) -> str:
  return f'data received {data}'

...
```

### class `amqp_worker.QueueWorker`

### class `amqp_worker.RPCWorker`

## Testing
