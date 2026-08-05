"""Build / cache composition plans for the workbench Compose UI."""

from __future__ import annotations

from typing import Any


def build_compose_plan(
    *,
    index: list | None,
    artifact: dict | None,
    template: dict | None,
    project_name: str = "",
    folder: str = "",
    doc_sections: dict | None = None,
    lang: str = "en",
) -> dict[str, Any]:
    from foldok_director import direct

    plan = direct(
        index,
        artifact=artifact,
        template=template,
        project_name=project_name,
        folder=folder,
        existing_sections=doc_sections or {},
        lang=lang,
    )
    return plan.to_dict()
