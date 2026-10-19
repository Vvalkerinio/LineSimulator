"""Fast, isolated configuration copies for candidate evaluation hot paths."""

from copy import copy


def clone_configuration_for_candidate(configuration):
    """Clone mutable simulation state without recursively copying static data.

    Candidate evaluation changes manipulator positions and may update runtime
    fields on stations (for example shared-bath selection state).  The top-level
    configuration, every manipulator and every station are therefore copied.
    Other list/dict containers are copied shallowly so candidate-local container
    mutations cannot leak while immutable or read-only payloads remain shared.
    """
    cloned = copy(configuration)
    attributes = vars(configuration) if hasattr(configuration, "__dict__") else {}
    for name, value in attributes.items():
        if name == "manipulators":
            setattr(cloned, name, [copy(item) for item in value])
        elif name == "stations":
            setattr(cloned, name, [copy(item) for item in value])
        elif isinstance(value, list):
            setattr(cloned, name, list(value))
        elif isinstance(value, dict):
            setattr(cloned, name, dict(value))
        elif isinstance(value, set):
            setattr(cloned, name, set(value))
    return cloned
