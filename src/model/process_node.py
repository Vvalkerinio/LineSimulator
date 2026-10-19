from dataclasses import dataclass


@dataclass
class ProcessNode:

    node_id: str

    is_bath_group: bool = False