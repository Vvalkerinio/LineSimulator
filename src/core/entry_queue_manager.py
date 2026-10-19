from collections import deque


class EntryQueueManager:

    def __init__(
        self
    ):

        self._queue = deque()

    def enqueue(
        self,
        hanger_id
    ):

        self._queue.append(
            hanger_id
        )

    def dequeue(
        self
    ):

        if not self._queue:

            return None

        return (
            self._queue.popleft()
        )

    def peek(
        self
    ):

        if not self._queue:

            return None

        return self._queue[0]

    def empty(
        self
    ):

        return (
            len(
                self._queue
            ) == 0
        )

    def size(
        self
    ):

        return len(
            self._queue
        )