from enum import Enum


class StartMode(Enum):
    EMPTY = "EMPTY"
    ACTIVE_BATHS = "ACTIVE_BATHS"

    @classmethod
    def from_value(
        cls,
        value
    ):
        if isinstance(
            value,
            StartMode
        ):
            return value

        if value is None:
            return cls.EMPTY

        text = (
            str(value)
            .strip()
            .upper()
        )

        for mode in cls:
            if (
                mode.value
                ==
                text
            ):
                return mode

        return cls.EMPTY