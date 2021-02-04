"""Tests for QueueWorker."""
# pylint: disable=redefined-outer-name
# pylint: disable=no-method-argument
# pylint: disable=missing-function-docstring

import asyncio
from typing import (Any,
                    Awaitable,
                    Callable,
                    Tuple,
                    TypedDict
                    )

from aio_pika import Connection, Channel
import pytest

# pylint won't be able to find these imports until the local package is
# installed, which shouldn't be necessary just to test; instead, run
# tests with `python -m pytest` from root to resolve imports correctly
# pylint: disable=import-error
from amqp_worker.queue_worker import CustomJSONGzipMaster
from amqp_worker import ConnectionParameters, QueueWorker

conn_params = pytest.mark.usefixtures('conn_params')
connection_and_channel = pytest.mark.usefixtures('connection_and_channel')


# pylint: disable=too-few-public-methods
# pylint: disable=inherit-non-class
class Message(TypedDict):
    """Message struct/interface."""
    data: Any


@pytest.fixture
def publish(
    connection_and_channel: Tuple[Connection, Channel]
) -> Callable[[str, Any], Awaitable[Any]]:
    _, channel = connection_and_channel
    master = CustomJSONGzipMaster(channel)

    def pub(queue: str, data: Message) -> Awaitable[Any]:
        return master.create_task(queue, kwargs=data)

    return pub


class TestQueueWorker:
    """Tests for QueueWorker."""

    @staticmethod
    def test_can_initialize_queue_worker(
        conn_params: ConnectionParameters
    ) -> None:
        assert QueueWorker(conn_params) is not None

    @staticmethod
    def test_worker_listens_for_messages_on_routes(
        conn_params: ConnectionParameters,
        publish: Callable[[str, Any], Awaitable[Any]]
    ) -> None:
        worker = QueueWorker(conn_params)
        state = []

        # Pylint is confused about this decorated function
        # for some reason & thinks it's not being used
        # pylint: disable=unused-variable

        @worker.route('add-to-state')
        async def add_to_state(message: Any) -> None:
            state.append(message)

        # start an event loop to run worker & publish message to it
        loop = asyncio.get_event_loop()
        # start worker & save returned stop method
        stop_worker = loop.run_until_complete(worker.run())
        # publish a message
        loop.run_until_complete(publish('add-to-state', {'data': 'message'}))
        # stop the worker
        loop.run_until_complete(stop_worker())

        assert 'message' in state
