"""Classes for making working with RabbitMQ RPC workers easier.

Powered by aio-pika.
"""

from __future__ import annotations
import json
from typing import (
    cast,
    Any,
    Awaitable,
    Callable,
    List,
)

from aio_pika.patterns import RPC
from aio_pika.channel import Channel

from .connection import ConnectionParameters
from .response import Response, ErrResponse
from .serializer import (
    serialize,
    deserialize,
    JSONEncoderProtocol,
    ResponseEncoder
)
from .worker_base import Worker, Route

#
# EXTENDING aio_pika.RPC
#


class JSONGzipRPC(RPC):
    """Extend RPC pattern from aio-pika.

    - Automates encoding as JSON & UTF8, then compresses messages with Gzip.
    - Specifies what type of data must be given in order to be serialized
    """

    SERIALIZER = json  # pylint: disable=duplicate-code
    CONTENT_TYPE = 'application/octet-stream'  # pylint: disable=duplicate-code

    json_encoder: JSONEncoderProtocol  # pylint: disable=duplicate-code

    def __init__(
        self,
        channel: Channel
    ) -> None:  # pylint: disable=duplicate-code
        super().__init__(channel)  # pylint: disable=duplicate-code
        self.json_encoder = ResponseEncoder()  # pylint: disable=duplicate-code

    def serialize(
        self,
        data: Response
    ) -> bytes:  # pylint: disable=duplicate-code
        """Serialize the data being sent in the message.

        Arguments:
        - data: Response -- The data to be serialized

        Returns:
        - bytes

        Defers to shared serialize function to handle serialization
        using the SERIALIZER specified as a class constant.
        """
        return serialize(
            self.json_encoder, data)  # pylint: disable=duplicate-code

    def serialize_exception(self, exception: Exception) -> bytes:
        """Wrap exceptions thrown by aio_pika.RPC in an ErrResponse."""
        return self.serialize(ErrResponse(exception))

    def deserialize(self, data: bytes) -> bytes:
        """Decompress incoming message, then defer to aio_pika.RPC."""
        # Example at https://aio-pika.readthedocs.io/en/latest/patterns.html
        # doesn't bother with decoding from bytes to string or
        # decoding json
        return super().deserialize(deserialize(data))


PatternFactory = Callable[[Channel], Awaitable[JSONGzipRPC]]


async def json_gzip_rpc_factory(channel: Channel) -> JSONGzipRPC:
    """
    Create an instance of JSONGzipRPC class.

    Used as default pattern factory in RPCWorker. Replace this method with a
    custom one if you need to modify the pattern used by RPCWorker.
    """
    # NOTE: casting to JSONGzipRPC because inherited create method
    # has signature returning RPC when class method on extended
    # JSONGzipRPC returns instance of JSONGzipRPC
    return cast(JSONGzipRPC, await JSONGzipRPC.create(channel))


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

    def __init__(
        self,
        connection_params: ConnectionParameters,
        name: str = 'RPCWorker',
        pattern_factory: PatternFactory = json_gzip_rpc_factory,
        json_encoder: ResponseEncoder = ResponseEncoder(),
    ) -> None:
        self._pattern_factory = pattern_factory
        super().__init__(connection_params, name, json_encoder)

    async def _pre_start(self) -> Callable[[Route], Awaitable[None]]:
        self._worker = await self._pattern_factory(self._channel)

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
