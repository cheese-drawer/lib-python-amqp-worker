"""Classes for making working with RabbitMQ Queue workers easier.

Powered by aio-pika.
"""

from __future__ import annotations
import json
from typing import cast, Any, Awaitable, Callable, List

from aio_pika.patterns import Master

from .connection import ConnectionParameters
from .response import Response
from .serializer import serialize, deserialize
from .worker_base import Worker, Route

#
# EXTENDING aio_pika.RPC
#


class CustomJSONGzipMaster(Master):
    """Extend Master pattern from aio-pika.

    - Automates encoding as JSON & UTF8, then compresses messages with Gzip.
    - Specifies what type of data must be given in order to be serialized
    """

    SERIALIZER = json
    CONTENT_TYPE = 'application/octet-stream'

    def serialize(self, data: Response) -> bytes:
        """Serialize the data being sent in the message.

        Arguments:
        - data: Response -- The data to be serialized

        Returns:
        - bytes

        Defers to shared serialize function to handle serialization
        using the SERIALIZER specified as a class constant.
        """
        return serialize(self.SERIALIZER, data)

    def deserialize(self, data: bytes) -> bytes:
        """Decompress incoming message, then defer to aio_pika.RPC."""
        # Example at https://aio-pika.readthedocs.io/en/latest/patterns.html
        # doesn't bother with decoding from bytes to string or
        # decoding json; apparently builtin `pickle` dependency
        # handles all of that on it's own.
        # FIXME: doesn't know how to handle errors in
        # decompressing/deserializing
        return super().deserialize(deserialize(data))

# Going with Producer & Worker to follow the concept of Producer &
# Consumer that's central to AMQP 0-9-1 already. Still using Worker
# because it does a better job describing what a Worker does, however.


#
# Producer & Worker definitions
#


# class QueueProducer:
#     pass


class QueueWorker(Worker):
    """Simplify creating Queue worker/consumer.

    Uses an overloaded version of aio-pika's Master pattern to add
    automatic JSON serialization/de-serialization & Gzip
    compression/decompression.

    See https://aio-pika.readthedocs.io/en/latest/patterns.html#master-worker
    for more.
    """

    # property types
    _worker: Master
    _routes: List[Route]

    # class constants
    PATTERN = CustomJSONGzipMaster

    def __init__(
            self,
            connection_params: ConnectionParameters,
            name: str = 'QueueWorker'):
        self._routes = []
        super().__init__(connection_params, name)

    async def _pre_start(self) -> Callable[[Route], Awaitable[None]]:
        # pylint doesn't seem to understand that PATTERN here is
        # a class variable & still accessible through `self`
        # pylint: disable=no-member
        self._worker = self.PATTERN(self._channel)

        async def create_queue(route: Route) -> None:
            self.logger.info(
                f"Registering handler {route['handler'].__name__} "
                f"for queue {route['path']}")
            await self._worker.create_worker(
                route['path'],
                # casting necessary because mypy gets a little confused about
                # expected type for RPC.register
                cast(Callable[[Any], Any], route['handler']),
                durable=True)

        return create_queue
