"""Tests for RequestAndResponseWorker."""
# pylint: disable=redefined-outer-name
# pylint: disable=no-method-argument
# pylint: disable=missing-function-docstring

import asyncio
from typing import (Any,
                    Optional,
                    Hashable,
                    Awaitable,
                    Callable,
                    Tuple,
                    Dict
                    )

from aio_pika import Connection, Channel
import pytest

# pylint won't be able to find these imports until the local package is
# installed, which shouldn't be necessary just to test; instead, run
# tests with `python -m pytest` from root to resolve imports correctly
# pylint: disable=import-error
from amqp_worker.rpc_worker import CustomJSONGzipRPC
from amqp_worker import ConnectionParameters, RPCWorker

conn_params = pytest.mark.usefixtures('conn_params')
connection_and_channel = pytest.mark.usefixtures('connection_and_channel')


@pytest.fixture
def rpc_request(
    connection_and_channel: Tuple[Connection, Channel]
) -> Callable[[str, Any], Awaitable[Any]]:
    _, channel = connection_and_channel

    # pylint: disable=unsubscriptable-object
    async def req(
        queue: str,
        data: Optional[Dict[Hashable, Any]]
    ) -> Any:
        rpc = await CustomJSONGzipRPC.create(channel)

        response = await rpc.call(queue, kwargs=data)

        return response

    return req


class TestRPCWorker:
    """Tests for RPCWorker."""

    @staticmethod
    def test_can_initialize_rpc_worker(
        conn_params: ConnectionParameters
    ) -> None:
        assert RPCWorker(conn_params) is not None

    @staticmethod
    def test_worker_sends_response_to_request_received_on_route(
        conn_params: ConnectionParameters,
        rpc_request: Callable[[str, Any], Awaitable[Any]]
    ) -> None:
        worker = RPCWorker(conn_params)

        # Pylint is confused about this decorated function
        # for some reason & thinks it's not being used
        # pylint: disable=unused-variable

        @worker.route('process')
        async def add_to_state(message: Any) -> str:
            return f'{message} processed'

        # start an event loop to run worker & publish message to it
        loop = asyncio.get_event_loop()
        # start worker & save returned stop method
        stop_worker = loop.run_until_complete(worker.run())
        # publish a message
        response = loop.run_until_complete(
            rpc_request('process', {'data': 'message'}))
        # stop the worker
        loop.run_until_complete(stop_worker())

        assert response['data'] == 'message processed'

    @staticmethod
    def test_response_indicates_if_it_is_successful(
        conn_params: ConnectionParameters,
        rpc_request: Callable[[str, Any], Awaitable[Any]]
    ) -> None:
        worker = RPCWorker(conn_params)

        # Pylint is confused about this decorated function
        # for some reason & thinks it's not being used
        # pylint: disable=unused-variable

        @worker.route('process')
        async def add_to_state(message: Any) -> str:
            return f'{message} processed'

        # start an event loop to run worker & publish message to it
        loop = asyncio.get_event_loop()
        # start worker & save returned stop method
        stop_worker = loop.run_until_complete(worker.run())
        # publish a message
        response = loop.run_until_complete(
            rpc_request('process', {'data': 'message'}))
        # stop the worker
        loop.run_until_complete(stop_worker())

        assert response['success']

    @staticmethod
    def test_response_indicates_if_it_is_not_successful(
        conn_params: ConnectionParameters,
        rpc_request: Callable[[str, Any], Awaitable[Any]]
    ) -> None:
        worker = RPCWorker(conn_params)

        # Pylint is confused about this decorated function
        # for some reason & thinks it's not being used
        # pylint: disable=unused-variable

        @worker.route('error')
        async def add_to_state(message: Any) -> str:
            raise Exception('an error')

        # start an event loop to run worker & publish message to it
        loop = asyncio.get_event_loop()
        # start worker & save returned stop method
        stop_worker = loop.run_until_complete(worker.run())
        # publish a message
        response = loop.run_until_complete(
            rpc_request('error', {'data': 'message'}))
        # stop the worker
        loop.run_until_complete(stop_worker())

        assert response['success'] is False

    @staticmethod
    def test_an_unsuccessful_response_includes_error_data(
        conn_params: ConnectionParameters,
        rpc_request: Callable[[str, Any], Awaitable[Any]]
    ) -> None:
        worker = RPCWorker(conn_params)

        # Pylint is confused about this decorated function
        # for some reason & thinks it's not being used
        # pylint: disable=unused-variable

        @worker.route('error')
        async def add_to_state(message: Any) -> str:
            raise Exception('an error')

        # start an event loop to run worker & publish message to it
        loop = asyncio.get_event_loop()
        # start worker & save returned stop method
        stop_worker = loop.run_until_complete(worker.run())
        # publish a message
        response = loop.run_until_complete(
            rpc_request('error', {'data': 'message'}))
        # stop the worker
        loop.run_until_complete(stop_worker())

        assert response['error']['message'] == "Exception('an error')"
