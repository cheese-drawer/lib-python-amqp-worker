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
    def encode(self, obj: Any) -> str: ...
    def default(self, obj: Any) -> JSONEncoderTypes: ...


class ResponseEncoder(JSONEncoder):
    """Extend JSONEncoder to parse Response objects."""

    def default(self, o: Any) -> JSONEncoderTypes:
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


# def _to_json(
#     serializer: Any,
#     data: Response,
#     default: Optional[Callable[[Any], Any]] = None
# ) -> Any:
#     # first try encoding using normal json encoding
#     try:
#         return serializer.dumps(
#             data,
#             ensure_ascii=False,
#         )
#
#     except TypeError as err:
#         # pass here to move on to the next try block
#         # allows cleaner code by not nesting try/except
#         # blocks unnecessarily
#         LOGGER.info('Error while using built-in default serializer:')
#         LOGGER.info(f'    Error: {err}')
#
#     # then try using a user provided default method
#     if default is not None:
#         LOGGER.info('Trying user-provided serializer...')
#         LOGGER.info(f'    Serializer: {default}')
#
#         try:
#             return serializer.dumps(
#                 vars(data),
#                 ensure_ascii=False,
#                 default=default,
#             )
#
#         except TypeError as err:
#             LOGGER.info('Error while using user-provided serializer:')
#             LOGGER.info(f'    Error: {err}')
#
#     # finally, fall back to string representation of the
#     # object using `repr()`
#     try:
#         return serializer.dumps(
#             vars(data),
#             ensure_ascii=False,
#             default=repr,
#         )
#
#     except TypeError as err:
#         LOGGER.info('Error while using `repr` for serialization:')
#         LOGGER.info(f'    Error: {err}')
#         # if non of the above try blocks worked, raise
#         # a specific TypeError
#         raise TypeError(
#             'The Route\'s response is not JSON serializable'
#         ) from err


def serialize(
    serializer: JSONEncoderProtocol,
    data: Response,
) -> bytes:
    """
    Serialize the given data with the given serialization module.

    Arguments:
        serializer: Module   -- a serialization module, must implement the same
                                API as json
        data:       Response -- the data to be serialized, must be an instance
                                of Response

    Returns:
        bytes


    The provided data must be json serializable. This method will attempt
    to serialize it by using first converting it to a dictionary using
    `vars()`, then using the string returned by calling `repr()` on it.
    If neither of those works, then a TypeError will be raised.

    After serializing the data to json, it is then encoded as UTF8 &
    compressed using gzip.
    """
    as_json = serializer.encode(data)
    LOGGER.info(f'RESPONSE JSON: {as_json}')

    return gzip.compress(as_json.encode('UTF8'))


def deserialize(data: bytes) -> str:
    """Decompresses the given data using gzip.

    Arguments:
        data: bytes -- the bytes in need of decompressing
                       & decoding

    Returns:
        str

    Used to share modifications to deserialization behavior between
    aio_pika.pattern extensions. Assumes user will be deferring the
    rest of the deserialization to the parent class via
    `super().deserialize()`
    """
    return gzip.decompress(data).decode('UTF8')
