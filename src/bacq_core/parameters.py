"""
Define an abstract Parameter inyterface.
"""

from dataclasses import dataclass
from typing import Callable

@dataclass
class Parameter:
    name: str
    constraint: Callable
    description: str
    sequence: bool = False
    meta: bool = False

class ParameterSet(dict):
    def __init__(self, parameters: list[Parameter]):
        for parameter in parameters:
            self[parameter.name] = parameter

    @property
    def meta_params(self):
        return ParameterSet([param for param in self.values() if param.meta is True])
    
