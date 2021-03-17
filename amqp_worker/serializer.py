"""Shared behavior for serializing messages sent & received by Workers."""

import gzip
from json import JSONEncoder
from logging import getLogger
from typing import (
    cast,
    Any,
    Protocol,
    Optional,
    Union,
    List,
    Tuple,
    Dict,
)

from .response import Response, OkResponse, ErrResponse


LOGGER = getLogger(__name__)


JSONEncoderTypes = Optional[Union[
    int,
    float,
    str,
    bool,
    Dict[str, Any],
    List[Any],
    Tuple[Any]
]]


class JSONEncoderProtocol(Protocol):
    """Define expected behavior for an object capable of encoding JSON."""

    def encode(self, obj: Any) -> str:
        """Encode a given object as JSON."""

    def default(self, obj: Any) -> JSONEncoderTypes:
        """Convert a given object to a type that is encodable to JSON."""


class ResponseEncoder(JSONEncoder):
    """Extend JSONEncoder to parse Response objects."""

    def default(self, o: Any) -> JSONEncoderTypes:
        """Convert OkResponse & ErrResponse to dictionaries."""
        if isinstance(o, OkResponse):
            return o.__dict__

        if isinstance(o, ErrResponse):
            return o.__dict__

        # NOTE: Casting as built-in JSONEncoder's default method
        # incorrectly has signature of Any when the documentation
        # for the method states it must return either a type that is
        # serializable to JSON by the default rules, or raises a
        # TypeError.
        return cast(JSONEncoderTypes, JSONEncoder.default(self, o))


def serialize(
    serializer: JSONEncoderProtocol,
    data: Response,
) -> bytes:
    """
    Serialize the given data with the given serialization module.

    After serializing the data to json, it is then encoded as UTF8 &
    compressed using gzip.
    """
    as_json = serializer.encode(data)
    LOGGER.info(f'RESPONSE JSON: {as_json}')

    return gzip.compress(as_json.encode('UTF8'))


def deserialize(data: bytes) -> str:
    """Decompresses the given data using gzip.

    Assumes user will be deferring the rest of the deserialization to the
    parent class via `super().deserialize()`
    """
    return gzip.decompress(data).decode('UTF8')
