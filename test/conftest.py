"""Shared fixtures for tests."""
# pylint: disable=redefined-outer-name
# pylint: disable=no-method-argument

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Tuple

import pytest
from aio_pika import connect, Connection, Channel

# pylint won't be able to find these imports until the local package is
# installed, which shouldn't be necessary just to test; instead, run
# tests with `python -m pytest` from root to resolve imports correctly
# pylint: disable=import-error
from amqp_worker import ConnectionParameters


@pytest.fixture(scope='module')
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Redefined event loop fixture to module scope."""
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='module')
def conn_params() -> ConnectionParameters:
    return ConnectionParameters('localhost', 5672, 'test', 'pass')


@pytest.fixture(scope='module')
async def connection_and_channel(
    conn_params: ConnectionParameters
) -> AsyncGenerator[Tuple[Connection, Channel], None]:
    connection: Connection = await connect(
        host=conn_params.host,
        port=conn_params.port,
        login=conn_params.user,
        password=conn_params.password)
    channel: Channel = await connection.channel()

    yield connection, channel

    await channel.close()  # type: ignore
    await connection.close()  # type: ignore
