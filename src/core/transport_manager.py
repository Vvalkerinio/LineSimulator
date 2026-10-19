class TransportManager:

    def __init__(self):

        self._active_hangers: set[int] = set()

    def has_pending(
        self,
        hanger_id: int
    ) -> bool:

        return (
            hanger_id
            in self._active_hangers
        )

    def reserve(
        self,
        hanger_id: int
    ) -> None:

        self._active_hangers.add(
            hanger_id
        )

    def complete(
        self,
        hanger_id: int
    ) -> None:

        self._active_hangers.discard(
            hanger_id
        )

    def count(self) -> int:

        return len(
            self._active_hangers
        )