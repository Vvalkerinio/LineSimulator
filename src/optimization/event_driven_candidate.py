from dataclasses import dataclass


@dataclass(frozen=True)
class SharedBathCandidateParameter:
    """One shared-bath scheduling rule supported by SharedBathSelector."""

    group_name: str
    mode: str
    value: float

    SUPPORTED_MODES = ("percent", "seconds", "alternate")

    def normalized(self):
        mode = str(self.mode).strip().lower()
        if mode not in self.SUPPORTED_MODES:
            raise ValueError(
                f"Unsupported shared bath mode {self.mode!r}; "
                f"supported={self.SUPPORTED_MODES}"
            )
        value = float(self.value)
        if mode == "percent" and not 0.0 <= value <= 100.0:
            raise ValueError("Shared bath percent must be in range 0..100.")
        if mode == "seconds" and value < 0.0:
            raise ValueError("Shared bath seconds cannot be negative.")
        if mode == "alternate":
            value = 0.0
        return SharedBathCandidateParameter(
            group_name=str(self.group_name).strip(),
            mode=mode,
            value=value
        )


@dataclass(frozen=True)
class EventDrivenCandidate:
    """Parameters changed before EventDriven generates a new PLC program."""

    start_positions: tuple[int, int, int, int]
    shared_bath_parameters: tuple[SharedBathCandidateParameter, ...] = ()

    def normalized(self):
        if len(self.start_positions) != 4:
            raise ValueError("Exactly four manipulator start positions are required.")
        parameters = tuple(
            sorted(
                (item.normalized() for item in self.shared_bath_parameters),
                key=lambda item: item.group_name
            )
        )
        names = [item.group_name for item in parameters]
        if len(names) != len(set(names)):
            raise ValueError("Shared bath group must occur once per candidate.")
        return EventDrivenCandidate(
            start_positions=tuple(int(value) for value in self.start_positions),
            shared_bath_parameters=parameters
        )
