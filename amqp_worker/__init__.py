"""Clients for building services that communicate via AMQP.

Top-level exports:
    ConnectionParameters: dataclass for encapsulating necessary data to connect
    to a broker
    RPCWorker: a worker client built to communicate in a Request & Response
    (or RPC) pattern
    QueueWorker: a worker client build to communicate in a Producer & Worker
    (e.g. Master/Worker, work queues) pattern
"""

from .connection import ConnectionParameters
from .rpc_worker import RPCWorker
from .queue_worker import QueueWorker
