from contextlib import contextmanager

from .metaclasses.enumeration import EnumerationMeta

__all__ = ['Enum', 'ConnectionStates', 'Netmodes', 'PacketProtocols', 'Roles', 'IterableCompressionType']


class Enum(metaclass=EnumerationMeta):
    pass


class ConnectionStates(Enum):
    """Status of connection to peer"""
    failed = ...
    timeout = ...
    disconnected = ...
    init = ...
    awaiting_handshake = ...
    received_handshake = ...
    connected = ...


class Netmodes(Enum):
    server = ...
    client = ...


class PacketProtocols(Enum):
    heartbeat = ...
    request_disconnect = ...
    invoke_handshake = ...
    request_handshake = ...
    handshake_success = ...
    handshake_failed = ...
    create_scene = ...
    delete_scene = ...

    # Replication
    create_replicable = ...
    delete_replicable = ...
    update_attributes = ...
    invoke_method = ...


class IterableCompressionType(Enum):
    no_compress = ...
    compress = ...
    auto = ...


class Roles(Enum):
    none = ...
    dumb_proxy = ...
    simulated_proxy = ...
    autonomous_proxy = ...
    authority = ...

    __slots__ = "local", "remote", "_context"

    def __init__(self, local, remote):
        self.local = local
        self.remote = remote
        self._context = None

    def __description__(self):
        return hash((self._context, self.local, self.remote))

    def __repr__(self):
        return "Roles: Local: {}, Remote: {}".format(self.__class__[self.local],
                                                     self.__class__[self.remote])

    @contextmanager
    def set_context(self, is_owner):
        self._context = is_owner

        if self.remote == Roles.autonomous_proxy and not is_owner:
            self.remote = Roles.simulated_proxy
            yield
            self.remote = Roles.autonomous_proxy

        else:
            yield

        self._context = None
