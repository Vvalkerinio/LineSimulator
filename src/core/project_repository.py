import json

from pathlib import Path

from src.model.project import Project


class ProjectRepository:

    def save(
        self,
        project: Project,
        file_path: str
    ) -> None:

        data = {
            "name": project.name,
            "recipes": [
                recipe.id
                for recipe in project.recipes
            ],
            "bath_groups": [
                {
                    "id": group.id,
                    "name": group.name,
                    "stations": group.stations
                }
                for group in project.bath_groups
            ]
        }

        Path(file_path).write_text(
            json.dumps(
                data,
                indent=4
            ),
            encoding="utf-8"
        )
