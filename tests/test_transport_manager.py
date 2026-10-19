from src.core.transport_manager import (
    TransportManager
)


def test_transport_reserve_complete():

    manager = TransportManager()

    manager.reserve(1)

    assert manager.has_pending(1)

    manager.complete(1)

    assert not manager.has_pending(1)