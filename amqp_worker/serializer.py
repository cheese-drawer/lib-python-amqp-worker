import gzip
from typing import Any

from .response import Response, ErrResponse


def serialize(serializer: Any, data: Response) -> bytes:
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
    try:
        as_json = serializer.dumps(
            data,
            ensure_ascii=False,
        )
    except TypeError as err:
        err_msg = err.args[0]
        if 'not JSON serializable' in err_msg:
            try:
                as_json = serializer.dumps(
                    vars(data),
                    ensure_ascii=False,
                    default=repr,
                )
            except TypeError:
                raise TypeError(
                    'The Route\'s response is not JSON serializable'
                ) from err

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
