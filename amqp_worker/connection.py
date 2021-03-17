"""Interface & function for defining & establishing connection to RabbitMQ."""

import asyncio
from dataclasses import dataclass
import logging
from typing import Optional, Tuple

from aio_pika.channel import Channel
from aio_pika.connection import Connection
from aio_pika import connect_robust

#
# RabbitMQ Connection helper
#

LOGGER = logging.getLogger(__name__)


@dataclass
class ConnectionParameters:
    """Defines connection parameters for aio-pika."""

    host: str
    port: int
    user: str
    password: str


async def _try_connect(
    connection_params: ConnectionParameters,
    retries: int = 1
) -> Connection:
    host = connection_params.host
    port = connection_params.port

    connection: Optional[Connection] = None

    LOGGER.info(f'Attempting to connect to broker at {host}:{port}...')

    while connection is None:
        try:
            connection = await connect_robust(
                host=host,
                port=port,
                login=connection_params.user,
                password=connection_params.password)
        except ConnectionError as err:
            if retries > 12:
                raise ConnectionError(
                    'Max number of connection attempts has been reached (12)'
                ) from err

            LOGGER.info(
                f'Connection failed ({retries} time(s))'
                'retrying again in 5 seconds...')

            await asyncio.sleep(5)
            return await _try_connect(connection_params, retries + 1)

    return connection


async def connect(
    connection_params: ConnectionParameters
) -> Tuple[str, int, Connection, Channel]:
    """Attempt to connect to a RabbitMQ broker with given parameters."""
    host = connection_params.host
    port = connection_params.port

    connection: Connection = await _try_connect(connection_params)
    channel: Channel = await connection.channel()

    return host, port, connection, channel
