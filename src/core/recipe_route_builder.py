from src.model.process_node import (
    ProcessNode
)

from src.model.process_plan import (
    ProcessPlan
)


class RecipeRouteBuilder:

    def build(
        self,
        recipe
    ) -> ProcessPlan:

        nodes = []

        for step in recipe.steps:

            nodes.append(
                ProcessNode(
                    node_id=step.id,
                    is_bath_group=
                        step.bath_group_id
                        is not None
                )
            )

        return ProcessPlan(
            nodes=nodes
        )
