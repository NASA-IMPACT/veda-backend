"""Dependency injection in to fastapi routes"""

from typing import Dict, List

from fastapi.dependencies.utils import get_parameterless_sub_dependant
from fastapi import Security
from fastapi.routing import APIRoute


def add_route_dependencies(
    routes: List[APIRoute], scopes: Dict[str,tuple[str, str]], valid_token_dependency: str
):
    """Inject dependencies to routes"""
    
    for endpoint, (method, scope) in scopes.items():
        for route in routes:
            if route.path == endpoint and method in route.methods:
        
                depends = Security(valid_token_dependency, scopes=[scope])
                # Mimicking how APIRoute handles dependencies:
                # https://github.com/tiangolo/fastapi/blob/1760da0efa55585c19835d81afa8ca386036c325/fastapi/routing.py#L408-L412
                route.dependant.dependencies.insert(
                    0,
                    get_parameterless_sub_dependant(depends=depends, path=route.path_format)
                )
                
                route.dependencies.extend([depends])