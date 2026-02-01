"""
Módulo de geração de relatórios.
"""

from .json_report import generate_json_report
from .markdown_report import generate_markdown_reports, generate_markdown_summary

__all__ = [
    'generate_json_report',
    'generate_markdown_reports',
    'generate_markdown_summary'
]
