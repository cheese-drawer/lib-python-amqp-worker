"""Classes for making working with RabbitMQ RPC workers easier.

Powered by aio-pika.
"""

from __future__ import annotations
import json
from typing import (cast,
                    Any,
                    Awaitable,
                    Callable,
                    List)

from aio_pika.patterns import RPC

from .connection import ConnectionParameters
from .response import Response, ErrResponse
from .serializer import serialize, deserialize
from .worker_base import Worker, Route

#
# EXTENDING aio_pika.RPC
#


class CustomJSONGzipRPC(RPC):
    """Extend RPC pattern from aio-pika.

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

    def serialize_exception(self, exception: Exception) -> bytes:
        """Wrap exceptions thrown by aio_pika.RPC in an ErrResponse."""
        return self.serialize(ErrResponse(exception))

    def deserialize(self, data: bytes) -> bytes:
        """Decompress incoming message, then defer to aio_pika.RPC."""
        # Example at https://aio-pika.readthedocs.io/en/latest/patterns.html
        # doesn't bother with decoding from bytes to string or
        # decoding json; apparently builtin `pickle` dependency
        # handles all of that on it's own.
        # FIXME: doesn't know how to handle errors in
        # decompressing/deserializing
        return super().deserialize(deserialize(data))


#
# Worker definition
#


class RPCWorker(Worker):
    """Simplify creating an RPC worker.

    Uses an overloaded version of aio-pika's RPC to add automatic
    JSON serialization/de-serialization & Gzip
    compression/decompression.

    See https://aio-pika.readthedocs.io/en/latest/patterns.html#rpc
    for more.
    """

    # property types
    _worker: RPC
    _routes: List[Route]

    # class constants
    PATTERN = CustomJSONGzipRPC

    def __init__(
            self,
            connection_params: ConnectionParameters,
            name: str = 'RPCWorker'):
        self._routes = []
        super().__init__(connection_params, name)

    async def _pre_start(self) -> Callable[[Route], Awaitable[None]]:
        # pylint doesn't seem to understand that PATTERN here is
        # a class variable & still accessible through `self`
        # pylint: disable=no-member
        self._worker = await self.PATTERN.create(self._channel)

        async def register(route: Route) -> None:
            self.logger.info(
                f"Registering handler {route['handler'].__name__} "
                f"on path {route['path']}")
            await self._worker.register(
                route['path'],
                # casting necessary because mypy gets a little confused about
                # expected type for RPC.register
                cast(Callable[[Any], Any], route['handler']))

        return register
