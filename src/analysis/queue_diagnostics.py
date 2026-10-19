class QueueDiagnostics:

    def __init__(
        self
    ):

        self.enqueue_count = 0

        self.dequeue_count = 0

        self.max_queue_size = 0

    def register_enqueue(
        self,
        queue_size
    ):

        self.enqueue_count += 1

        self.max_queue_size = max(
            self.max_queue_size,
            queue_size
        )

    def register_dequeue(
        self,
        queue_size
    ):

        self.dequeue_count += 1

        self.max_queue_size = max(
            self.max_queue_size,
            queue_size
        )

    def print_summary(
        self
    ):

        print()
        print(
            "=" * 60
        )
        print(
            "QUEUE DIAGNOSTICS"
        )
        print(
            "=" * 60
        )

        print(
            f"enqueue_count: "
            f"{self.enqueue_count}"
        )

        print(
            f"dequeue_count: "
            f"{self.dequeue_count}"
        )

        print(
            f"max_queue_size: "
            f"{self.max_queue_size}"
        )

        print(
            "=" * 60
        )