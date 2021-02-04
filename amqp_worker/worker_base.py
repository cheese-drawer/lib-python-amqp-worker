"""Base classes for building Request & Response & Server 2 Server Workers."""

import asyncio
import inspect
import logging
from typing import Callable, Awaitable, Any, Union, List, TypedDict

from aio_pika.patterns import RPC, Master
from aio_pika.channel import Channel
from aio_pika.connection import Connection

from .connection import connect, ConnectionParameters
from .response import Response, OkResponse, ErrResponse


#
# WORKER ROUTE TYPES
#


# PENDS python 3.9 support in pylint
# pylint: disable=unsubscriptable-object
RouteHandler = Callable[[Any], Awaitable[Any]]


class Route(TypedDict):
    """Defines a Route for aio_pika.RPC.register."""

    # PENDS python 3.9 support in pylint
    # pylint: disable=inherit-non-class
    # pylint: disable=too-few-public-methods

    path: str
    handler: RouteHandler


class Worker:
    """Base Worker class, to be used as an ABC."""

    # property types
    _connection: Connection
    _connection_params: ConnectionParameters
    _channel: Channel
    _routes: List[Route]
    # PENDS python 3.9 support in pylint
    # pylint: disable=unsubscriptable-object
    _worker: Union[RPC, Master]
    logger: logging.Logger
    worker_name: str
    PATTERN: Any

    def __init__(
            self,
            connection_params: ConnectionParameters,
            name: str):
        self._connection_params = connection_params
        self.worker_name = name
        self.logger = logging.getLogger(self.worker_name)

    async def _pre_start(self) -> Callable[[Route], Awaitable[None]]:
        pass

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

        build_route = await self._pre_start()

        await asyncio.gather(*[build_route(route) for route in self._routes])

        self.logger.info(
            f'Worker waiting for tasks from {host}:{port}')

    async def _stop(self) -> None:
        """Defers to aio-pika.Connection's close method."""
        self.logger.info('Worker stopping...')
        # having mypy ignore the next line--calling close is necessary to
        # gracefully disconnect from rabbitmq broker, but aio_pika's
        # Connection.close method is untyped, throwing an "Call to untyped
        # function "close" in typed context" error when not ignored in strict
        # mode
        await self._connection.close()  # type: ignore

    def route(self, path: str) -> Callable[[RouteHandler], None]:
        """Add new 'route' (consumer queue) to the worker with this Decorator.

        Similar to creating a route in Flask, this method listens on a given
        'path' (queue name) & executes the given handler (callback) when a
        message is received in that queue.

        Returns the data returned by the decorated function, wrapped in a
        Response object. Not all Worker types will use this response, but
        any Worker that doesn't will simply ignore the return value.
        """
        self.logger.debug(
            f'Begin processing route decorator with given path: {path}')

        def wrap_handler(
                path: str,
                handler: RouteHandler) -> RouteHandler:
            async def wrapped(data: Any) -> Response:
                self.logger.info(f'TASK RECEIVED {path}')

                response: Response

                try:
                    result = await handler(data)
                    response = OkResponse(result)
                # Ignoring broad-except pylint warning here because the intent
                # is to catch every error thrown while awaiting & executing a
                # handler; this allows it to be wrapped in an ErrResponse &
                # communicated clearly to the original Requester
                except Exception as err:  # pylint: disable=broad-except
                    response = ErrResponse(err)

                self.logger.info(
                    f'TASK COMPLETED {path}: {repr(response)}')

                return response

            return wrapped

        def decorate_route(handler: RouteHandler) -> None:
            if inspect.iscoroutinefunction(handler):
                new_route = Route(
                    path=path,
                    handler=wrap_handler(path, handler))

                self.logger.debug(
                    f'Created new route: {new_route}')

                self._routes.append(new_route)

                self.logger.debug(
                    f'Pushed new route to _routes: {self._routes}')
            else:
                raise TypeError(
                    f'Handler {handler} must be a coroutine function')

        return decorate_route

    async def run(self) -> Callable[[], Awaitable[None]]:
        """Start the RPC Worker.

        Must be called inside an asyncio event loop, such as
        `run_until_complete(run())`.
        """
        await self._start()

        return self._stop
