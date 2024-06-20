"""Classes for making working with RabbitMQ Queue workers easier.

Powered by aio-pika.
"""

from __future__ import annotations
import gzip
import json
import logging
from typing import cast, Any, Awaitable, Callable, List

from aio_pika.patterns import Master
from aio_pika.channel import Channel
from aio_pika.connection import Connection

from .connection import connect, ConnectionParameters
from .response import Response
from .serializer import (
    serialize,
    JSONEncoderProtocol,
    ResponseEncoder
)
from .worker_base import Worker, Route

#
# EXTENDING aio_pika.RPC
#


class JSONGzipMaster(Master):
    """Extend Master pattern from aio-pika.

    - Automates encoding as JSON & UTF8, then compresses messages with Gzip.
    - Specifies what type of data must be given in order to be serialized
    """

    SERIALIZER = json
    CONTENT_TYPE = 'application/octet-stream'

    json_encoder: JSONEncoderProtocol

    def __init__(self, channel: Channel) -> None:
        super().__init__(channel)
        self.json_encoder = ResponseEncoder()

    def serialize(self, data: Response) -> bytes:
        """Serialize the data being sent in the message.

        Arguments:
        - data: Response -- The data to be serialized

        Returns:
        - bytes

        Defers to shared serialize function to handle serialization
        using the SERIALIZER specified as a class constant.
        """
        return serialize(self.json_encoder, data)

    def deserialize(self, data: bytes) -> Any:
        """Decompress incoming message, then defer to aio_pika.Master."""
        # Example at https://aio-pika.readthedocs.io/en/latest/patterns.html
        # doesn't bother with decoding from bytes to string or
        # decoding json
        return super().deserialize(gzip.decompress(data))


PatternFactory = Callable[[Channel], JSONGzipMaster]


def json_gzip_queue_factory(channel: Channel) -> JSONGzipMaster:
    """
    Create an instance of JSONGzipMaster class.

    Used as default pattern factory in QueueWorker. Replace this method with a
    custom one if you need to modify the pattern used by QueueWorker.
    """
    return JSONGzipMaster(channel)

# Going with Producer & Worker to follow the concept of Producer &
# Consumer that's central to AMQP 0-9-1 already. Still using Worker
# because it does a better job describing what a Worker does, however.


#
# Producer & Worker definitions
#


class QueueProducer:
    """Simplify creating a Queue producer.

    Uses an overloaded version of aio-pika's Master pattern to add
    automatic JSON serialization/de-serialization & Gzip
    compression/decompression.

    See https://aio-pika.readthedocs.io/en/latest/patterns.html#master-worker
    for more.

    Exposes a method, `publish`, for creating a given task & transmitting it
    on the given queue.
    """

    # property types
    _connection: Connection
    _connection_params: ConnectionParameters
    _channel: Channel
    _json_encoder: ResponseEncoder
    _worker: Master
    logger: logging.Logger
    worker_name: str

    def __init__(
        self,
        connection_params: ConnectionParameters,
        name: str = 'QueueProducer',
        pattern_factory: PatternFactory = json_gzip_queue_factory,
        json_encoder: ResponseEncoder = ResponseEncoder(),
    ) -> None:
        self._pattern_factory = pattern_factory

        self._connection_params = connection_params
        self._json_encoder = json_encoder
        self.worker_name = name

        self.logger = logging.getLogger(self.worker_name)

    async def _start(
            self,
    ) -> None:
        """Start the worker.

        Handles initializing a connection & creating a channel,
        then uses aio-pika's RPC.create to create a new worker,
        & finally registers every route created by the user.
        """
        self.logger.info(f'Starting {self.worker_name}...')

        host, port, self._connection, self._channel = await connect(
            self._connection_params)
        self._worker = self._pattern_factory(self._channel)

        self.logger.info(
            f'{self.worker_name} connected to {host}:{port} & ready to '
            'publish tasks.')

    async def _stop(self) -> None:
        """Defers to aio-pika.Connection's close method."""
        self.logger.info(f'{self.worker_name} stopping...')
        # having mypy ignore the next line--calling close is necessary to
        # gracefully disconnect from rabbitmq broker, but aio_pika's
        # Connection.close method is untyped, throwing an "Call to untyped
        # function "close" in typed context" error when not ignored in strict
        # mode
        await self._connection.close()  # type: ignore

    async def publish(self, queue: str, task: Any) -> None:
        """Publish message with given body to a given queue."""
        self.logger.info(f'PUBLISHING TASK: {task}')
        await self._worker.create_task(queue, task=task)

    async def run(self) -> Callable[[], Awaitable[None]]:
        """Start the Worker.

        Must be called inside an asyncio event loop, such as
        `run_until_complete(run())`.
        """
        await self._start()

        return self._stop


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

    def __init__(
        self,
        connection_params: ConnectionParameters,
        name: str = 'QueueWorker',
        pattern_factory: PatternFactory = json_gzip_queue_factory,
        json_encoder: ResponseEncoder = ResponseEncoder(),
    ) -> None:
        self._pattern_factory = pattern_factory
        super().__init__(connection_params, name, json_encoder)

    async def _pre_start(self) -> Callable[[Route], Awaitable[None]]:
        self._worker = self._pattern_factory(self._channel)

        async def create_queue(route: Route) -> None:
            self.logger.info(
                f"Registering handler {route['handler'].__name__} "
                f"for queue {route['path']}")
            await self._worker.create_worker(
                route['path'],
                # casting necessary because mypy gets a little confused about
                # expected type for Master.create_worker
                cast(Callable[[Any], Any], route['handler']),
                durable=True)

        return create_queue
