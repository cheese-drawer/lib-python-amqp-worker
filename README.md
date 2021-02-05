# AMQP Worker Lib

A simple wrapper on [mosquito/aio-pika](https://github.com/mosquito/aio-pika) that exposes a Flask-like API for setting up workers to listen to (& sometimes respond to) messages sent via AMQP 0-9-1.

## Installation

Install with `pip` from releases on this repo. For example, you can install version 0.1.0 with the following command:

```
$ pip install https://github.com/cheese-drawer/lib-python-amqp-worker/releases/download/0.1.1/amqp_worker-0.1.1.tar.gz
```

If looking for a different release version, just replace the two instances of `0.1.1` in the command with the version number you need.

## Usage

This library uses a very simple, Flask-like API to create a worker, add handlers to a worker, and then run the worker.
Handlers are required to be asynchronous and running the worries has to happen inside an async event loop.

There are two worker classes, `QueueWorker` & `RPCWorker`, each conforming to a different AMQP communication pattern ([work queues](https://www.rabbitmq.com/tutorials/tutorial-two-python.html) & [remote procedure call](https://www.rabbitmq.com/tutorials/tutorial-six-python.html), respectively).
Each class is used nearly exactly the same way, differing only in one key way (as far as usage goes): `RPCWorker` routes send a `Response`, while `QueueWorker` routes do not (more on that below).
Additionally, all worker classes expect incoming data to be gzip-compressed, UTF8-encoded, json-serializable strings & all outgoing messages are the same.

Finally, the library includes a `ConnectionParameters` dataclass to help with defining the data necessary to connect to your broker (host, port, username, and password).

### Example: `QueueWorker`

Putting it all together is fairly straightforward. Start by initializing a new worker, passing it your brokers connection parameters on init, then make some routes, and end by starring the worker in an asynchronous event loop:

```python
# queue_worker.py

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


# define a "route" on the worker messages published to a queue with
# the name given to `route` will be handled by the decorated function
@worker.route('a-queue')
def handler(data: str) -> None:
    print(f'data received {data}')

# you can define as many routes as you need
@worker.route('another-route')
def another_route(data: Dict[str, Any]) -> None:
    print(f'got data on another-route:\n{data}')

# run worker by getting an event loop, starting up the worker in
# the loop, then listen for messages in a run_forever loop
loop = asyncio.get_event_loop()

# QueueWorker.run returns a function that stops the worker, save it
# for later
stop_worker = loop.run_until_complete(worker.run())

# wrap run_forever in try block to catch KeyboardInterrupt to kill
# the loop
try:
    loop.run_forever()
except KeyboardInterrupt:
    loop.run_until_complete(stop_worker ())
    loop.close()
```

To see it in action, first start a RabbitMQ broker (with Docker, for example: `docker run -itd rabbitmq`), then start the above `queue_worker.py` script in one terminal, then open another & send it some gzip-compressed, UTF8-encoded, json-serialzed data using any AMQP client, such as `pika`:

```python
import gzip
import json
from typing import Any

import pika

credentials = pika.PlainCredentials('guest', 'guest')
connection_parameters = pika.ConnectionParameters(
    host='localhost',
    port=5672,
    credentials=credentials)
connection = pika.BlockingConnection(connection_parameters)
channel = connection.channel()

message = 'a test message'

channel.basic_publish(
    exchange='',
    routing_key='a-queue',
    body=gzip.compress(json.dumps(message).encode('UTF8')))
```

In this example, you'll see the terminal running `queue_worker.py` print 'data received a test message' to stdout.

### Example: `RPCWorker`

Using an `RPCWorker` is almost exactly the same.
Just initialize an `RPCWorker` exactly the same way as a `QueueWorker`, then define a route, this time with a handler that returns a result.
That return value is the data that will be sent back in the response to the original caller.

For an example, just copy the above `queue_worker.py` example & replace the following lines:

```python
# rpc_worker.py
...

# in place of QueueWorker import
from amqp_worker import ConnectionParameters, RPCWorker
...

# in place of the orignal worker definition
worker = RPCWorker(connection_params)

# in place of the previous two routes
@worker.route('a-route')
def handler(data: str) -> str:
  return f'data received {data}'

...
```

Again, to see it in action, start your broker (if it's not still running), run the `rpc_worker.py` script, & send it messages from another shell:

```python
import gzip
import json
import uuid
from typing import Any

import pika

Connection = pika.BlockingConnection
# for some reason pika types Channels & Connections the same
Channel = pika.BlockingConnection


class Client:
    """Set up RPC response consumer with handler & provide request caller."""

    channel: Channel
    connection: Connection
    correlation_id: str
    response: Any

    def __init__(
        self,
        connection: Connection,
        channel: Channel
    ):
        self.connection = connection
        self.channel = channel

        result = self.channel.queue_declare(
            queue='', exclusive=True, auto_delete=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self._on_response,
            auto_ack=True)

    def _on_response(self, _, __, props, body):
        if self.correlation_id == props.correlation_id:
            self.response = json.loads(gzip.decompress(body).decode('UTF8'))

    def call(self, target_queue: str, message: Any) -> Any:
        """Send message as RPC Request to given queue & return Response."""
        self.response = None
        self.correlation_id = str(uuid.uuid4())
        message_props = pika.BasicProperties(
            reply_to=self.callback_queue,
            correlation_id=self.correlation_id)

        message_as_dict = {
            'data': message,
        }

        self.channel.basic_publish(
            exchange='',
            routing_key=target_queue,
            properties=message_props,
            body=gzip.compress(json.dumps(message_as_dict).encode('UTF8')))

        while self.response is None:
            self.connection.process_data_events(time_limit=120)

        return self.response

credentials = pika.PlainCredentials('guest', 'guest')
connection_parameters = pika.ConnectionParameters(
    host='localhost',
    port=5672,
    credentials=credentials)
connection = pika.BlockingConnection(connection_parameters)
channel = connection.channel()

client = Client(connection, channel)
response = client.call('a-route', 'a message') # => 'data received a message'
```
