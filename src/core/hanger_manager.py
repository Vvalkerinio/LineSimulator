from src.model.hanger import Hanger


class HangerManager:

    def __init__(self) -> None:
        self._hangers: dict[int, Hanger] = {}

    def add_hanger(
        self,
        hanger: Hanger
    ) -> None:
        self._hangers[hanger.id] = hanger

    def get(
        self,
        hanger_id: int
    ) -> Hanger:
        return self._hangers[hanger_id]

    def all(self):
        return list(
            self._hangers.values()
        )

    def move(
        self,
        hanger_id: int,
        current_time: float
    ) -> None:

        hanger = self.get(
            hanger_id
        )

        hanger.advance()

        if hasattr(
            hanger,
            "entered_station_at"
        ):
            hanger.entered_station_at = (
                current_time
            )