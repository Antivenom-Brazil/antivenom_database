"""
Checks de validação - módulo base e exportações.
"""

from .base import BaseCheck
from .schema import SchemaCheck
from .parsing import ParsingCheck
from .constraints import ConstraintsCheck
from .vocab import VocabCheck
from .coherence import CoherenceCheck
from .geospatial import GeospatialCheck
from .uniqueness import UniquenessCheck
from .reproducibility import ReproducibilityCheck
from .perf import PerfCheck

ALL_CHECKS = [
    SchemaCheck,
    ParsingCheck,
    ConstraintsCheck,
    VocabCheck,
    CoherenceCheck,
    GeospatialCheck,
    UniquenessCheck,
    ReproducibilityCheck,
    PerfCheck
]

__all__ = [
    'BaseCheck',
    'SchemaCheck',
    'ParsingCheck',
    'ConstraintsCheck',
    'VocabCheck',
    'CoherenceCheck',
    'GeospatialCheck',
    'UniquenessCheck',
    'ReproducibilityCheck',
    'PerfCheck',
    'ALL_CHECKS'
]
