"""Dependency injection in to fastapi routes"""

from typing import List
from fastapi.params import Depends
from fastapi.dependencies.utils import get_parameterless_sub_dependant
from fastapi.routing import APIRoute
from starlette.routing import Match
from starlette.types import Scope


def add_route_dependencies(
    routes: List[APIRoute], scopes: List[Scope], dependencies: List[Depends]
):
    """Inject dependencies to routes"""
    for route in routes:
        if not any(route.matches(scope)[0] == Match.FULL for scope in scopes):
            continue

        route.dependant.dependencies = [
            # Mimicking how APIRoute handles dependencies:
            # https://github.com/tiangolo/fastapi/blob/1760da0efa55585c19835d81afa8ca386036c325/fastapi/routing.py#L408-L412
            get_parameterless_sub_dependant(depends=depends, path=route.path_format)
            for depends in dependencies
        ] + route.dependant.dependencies
