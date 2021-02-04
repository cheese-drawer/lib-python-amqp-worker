"""Module to normalize Response shape across all workers.

Contains 2 classes to consume & a base class they both inherit from:

    Response:    base class
    OkResponse:  used to build a response successfully includes data
    ErrResponse: used to build a response that encountered an error
"""
import traceback
from typing import (Literal,
                    Any,
                    Union,
                    List,
                    Tuple,
                    TypedDict,
                    Dict)

#
# RESPONSE TYPES
#


class Response:
    """Normalizes a successful response on a Route."""

    # class is essentially a @dataclass, but needs ABC inheritance to work
    # correctly for mypy, ignoring pylint error about number of methods
    # pylint: disable=too-few-public-methods

    success: bool

    def __init__(self, success: bool) -> None:
        self.success = success


# PENDS python 3.9 support in pylint
# pylint: disable=unsubscriptable-object
OkResponseData = Union[str,
                       Dict[str, Any],
                       List[Any],
                       Tuple[Any],
                       int,
                       float,
                       bool]


class OkResponse(Response):
    """Response type to communicate a successful reply to the Request."""

    # class is essentially a @dataclass, but needs ABC inheritance to work
    # correctly for mypy, ignoring pylint error about number of methods
    # pylint: disable=too-few-public-methods

    # PENDS python 3.9 typing support in pylint
    # pylint: disable=unsubscriptable-object
    success: Literal[True]
    data: OkResponseData

    def __init__(self, data: OkResponseData) -> None:
        super().__init__(True)
        self.data = data


class ErrResponse(Response):
    """Response type to communicate an error with processing the Request."""

    # class is essentially a @dataclass, but needs ABC inheritance to work
    # correctly for mypy, ignoring pylint error about number of methods
    # pylint: disable=too-few-public-methods

    ErrorData = TypedDict('ErrorData', {
        'type': str,
        'message': str,
        'args': Tuple[Any, ...],
        'trace': str,
    })

    # PENDS python 3.9 typing support in pylint
    success: Literal[False]  # pylint: disable=unsubscriptable-object
    error: ErrorData

    def __init__(self, error: Exception) -> None:
        super().__init__(False)
        self.error = {
            'type': error.__class__.__name__,
            'message': repr(error),
            'args': error.args,
            'trace': ''.join(
                traceback.format_exception(
                    etype=type(error),
                    value=error,
                    tb=error.__traceback__)),
        }
