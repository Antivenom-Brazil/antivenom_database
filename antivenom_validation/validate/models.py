"""
Modelos de dados para a suite de validação.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from datetime import datetime


class Severity(Enum):
    """Níveis de severidade para erros de validação."""
    BLOCKER = "BLOCKER"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"
    
    def __lt__(self, other):
        order = [Severity.INFO, Severity.MINOR, Severity.MAJOR, Severity.BLOCKER]
        return order.index(self) < order.index(other)


@dataclass
class ValidationError:
    """Representa um erro individual de validação."""
    severity: Severity
    category: str
    message: str
    row_indices: Optional[list[int]] = None
    column: Optional[str] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    details: Optional[dict] = None
    
    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "row_indices": self.row_indices,
            "column": self.column,
            "expected": self.expected,
            "actual": self.actual,
            "details": self.details
        }


@dataclass
class ValidationResult:
    """Resultado de uma categoria de validação."""
    category: str
    passed: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    info: list[ValidationError] = field(default_factory=list)
    duration_seconds: float = 0.0
    
    @property
    def total_issues(self) -> int:
        return len(self.errors) + len(self.warnings) + len(self.info)
    
    def to_dict(self) -> dict:
        def convert_error(e):
            return e.to_dict() if hasattr(e, 'to_dict') else e
        
        return {
            "category": self.category,
            "passed": self.passed,
            "errors": [convert_error(e) for e in self.errors],
            "warnings": [convert_error(e) for e in self.warnings],
            "info": [convert_error(e) for e in self.info],
            "duration_seconds": self.duration_seconds
        }


@dataclass
class ValidationReport:
    """Relatório completo de validação."""
    timestamp: datetime
    manifest_path: str = ""
    data_file: str = ""
    row_count: int = 0
    column_count: int = 0
    results: list[ValidationResult] = field(default_factory=list)
    data_quality: dict = field(default_factory=dict)
    duration_seconds: float = 0.0
    
    # Aliases para compatibilidade
    @property
    def file_path(self) -> str:
        return self.data_file
    
    @property
    def total_rows(self) -> int:
        return self.row_count
    
    @property 
    def total_columns(self) -> int:
        return self.column_count
        
    @property
    def execution_time(self) -> float:
        return self.duration_seconds
        
    @property
    def passed(self) -> bool:
        """True se todos os checks passaram."""
        return all(r.passed for r in self.results)
    
    @property
    def total_checks(self) -> int:
        return len(self.results)
    
    @property
    def passed_checks(self) -> int:
        return sum(1 for r in self.results if r.passed)
    
    @property
    def failed_checks(self) -> int:
        return self.total_checks - self.passed_checks
    
    def count_by_severity(self) -> dict[str, int]:
        counts = {s.value: 0 for s in Severity}
        for result in self.results:
            for error in result.errors:
                severity = error.severity if hasattr(error, 'severity') else error.get('severity', 'UNKNOWN')
                if hasattr(severity, 'value'):
                    counts[severity.value] += 1
                else:
                    counts[str(severity)] = counts.get(str(severity), 0) + 1
            for warning in result.warnings:
                severity = warning.severity if hasattr(warning, 'severity') else warning.get('severity', 'UNKNOWN')
                if hasattr(severity, 'value'):
                    counts[severity.value] += 1
                else:
                    counts[str(severity)] = counts.get(str(severity), 0) + 1
            for info in result.info:
                severity = info.severity if hasattr(info, 'severity') else info.get('severity', 'UNKNOWN')
                if hasattr(severity, 'value'):
                    counts[severity.value] += 1
                else:
                    counts[str(severity)] = counts.get(str(severity), 0) + 1
        return counts
    
    @property
    def has_blockers(self) -> bool:
        return self.count_by_severity()["BLOCKER"] > 0
    
    @property
    def has_majors(self) -> bool:
        return self.count_by_severity()["MAJOR"] > 0
    
    def to_dict(self) -> dict:
        severity_counts = self.count_by_severity()
        return {
            "metadata": {
                "timestamp": self.timestamp.isoformat(),
                "manifest_path": self.manifest_path,
                "data_file": self.data_file,
                "row_count": self.row_count,
                "column_count": self.column_count,
                "validation_version": "1.0.0",
                "duration_seconds": self.duration_seconds
            },
            "summary": {
                "total_checks": self.total_checks,
                "passed": self.passed_checks,
                "failed": self.failed_checks,
                "by_severity": severity_counts,
                "pass_rate": self.passed_checks / self.total_checks if self.total_checks > 0 else 0
            },
            "data_quality": self.data_quality,
            "results": [r.to_dict() for r in self.results]
        }
