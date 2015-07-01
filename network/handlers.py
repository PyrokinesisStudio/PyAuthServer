from contextlib import contextmanager
from logging import getLogger

handlers = {}
descriptions = {}

__all__ = ['static_description', 'register_handler', 'register_description',
           'get_handler', 'default_logger_as', 'IHandler']

# Default loggers for handlers, handlers can be a class or an instance, so don't force user to set the logger
_DEFAULT_LOGGER = getLogger("<Default Handler Logger>")
LOGGER = _DEFAULT_LOGGER


@contextmanager
def default_logger_as(logger):
    global LOGGER
    LOGGER = logger
    yield
    LOGGER = _DEFAULT_LOGGER


def static_description(value):
    """"A Hash-like representation of a data type.

    Will default to hash() when no function is registered for value type

    :param value: object to describe
    :rtype: int
    """
    value_type = type(value)

    # First handle registered descriptions
    try:
        description_func = descriptions[value_type]

    except KeyError:
        # Now handle object attribute descriptions
        try:
            return value.__description__()

        # Now search for handled superclass descriptions
        except AttributeError:
            try:
                handled_superclasses = (cls for cls in value_type.__mro__ if cls in descriptions)
                handled_type = next(handled_superclasses)

            # Default to Python hashing, remember for next call (optimisation)
            except (AttributeError, StopIteration):
                description_func = descriptions[value_type] = hash

            # Remember description for next call (optimisation)
            else:
                description_func = descriptions[value_type] = descriptions[handled_type]

    return description_func(value)


def register_handler(value_type, handler):
    """Registers new handler for custom serialisers

    :param value_type: type of object
    :param handler: handler object for value_type
    :param is_callable: whether handler should be called with the TypeFlag that
    requests it
    """
    handlers[value_type] = handler


def register_description(value_type, callback):
    """Registers description callback for types which cannot define
    __description__
    and are not directly hash-able

    :param value_type: type of object
    :param callback: description function
    """
    descriptions[value_type] = callback


def get_handler(type_flag, logger=None):
    """Takes a TypeFlag (or subclass thereof) and return handler.

    If a handler cannot be found for the provided type, look for a handled
    superclass, assign it to the requested type and return it.

    :param type_flag: TypeFlag subclass
    :returns: handler object
    """

    value_type = type_flag.data_type

    try:
        handler = handlers[value_type]

    except KeyError:
        try:
            handled_superclasses = (cls for cls in value_type.__mro__ if cls in handlers)
            handled_type = next(handled_superclasses)

        except StopIteration as err:
            raise TypeError("No handler found for object with type {}".format(value_type)) from err

        except AttributeError as err:
            raise TypeError("Invalid handler type provided: {}".format(value_type)) from err

        else:
            # Remember this for later call
            handler = handlers[value_type] = handlers[handled_type]

    # Add default logger
    if logger is None:
        logger = LOGGER

    return handler(type_flag, logger=logger)


class IHandler:

    def __init__(self, flag, logger=None):
        pass

    def pack(self, value):
        raise NotImplementedError

    def pack_multiple(self, values, count):
        raise NotImplementedError

    def unpack_from(self, bytes_string, offset=0):
        raise NotImplementedError

    def unpack_multiple(self, bytes_string, count, offset=0):
        raise NotImplementedError

    def size(self, bytes_string):
        raise NotImplementedError
