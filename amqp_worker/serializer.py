import gzip
from json import JSONEncoder
from typing import Any, Callable, Optional

from .response import Response


def _to_json(
    serializer: Any,
    data: Response,
    default: Optional[Callable[[JSONEncoder, Any], Any]] = None
) -> Any:
    # first try encoding using normal json encoding
    try:
        return serializer.dumps(
            data,
            ensure_ascii=False,
        )

    except TypeError:
        # pass here to move on to the next try block
        # allows cleaner code by not nesting try/except
        # blocks unnecessarily
        pass

    # then try using a user provided default method
    if default is not None:
        try:
            return serializer.dumps(
                vars(data),
                ensure_ascii=False,
                default=default,
            )

        except TypeError:
            pass

    # finally, fall back to string representation of the
    # object using `repr()`
    try:
        return serializer.dumps(
            vars(data),
            ensure_ascii=False,
            default=repr,
        )

    except TypeError as err:
        # if non of the above try blocks worked, raise
        # a specific TypeError
        raise TypeError(
            'The Route\'s response is not JSON serializable'
        ) from err


def serialize(
    serializer: Any, data: Response,
    default: Optional[Callable[[JSONEncoder, Any], Any]] = None
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
    return gzip.compress(_to_json(serializer, data, default).encode('UTF8'))


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
