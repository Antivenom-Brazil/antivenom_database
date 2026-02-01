"""
Classe base para todos os checks de validação.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable
import pandas as pd
import time

from ..models import ValidationResult, ValidationError, Severity
from ..manifest import ManifestConfig


class BaseCheck(ABC):
    """Interface abstrata para checks de validação."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nome da categoria de validação."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Descrição do que este check valida."""
        pass
    
    @abstractmethod
    def run(self, df: pd.DataFrame, config: ManifestConfig) -> ValidationResult:
        """Executa a validação e retorna o resultado."""
        pass
    
    def create_error(
        self,
        severity: Severity,
        message: str,
        row_indices: Optional[list[int]] = None,
        column: Optional[str] = None,
        expected: Optional[any] = None,
        actual: Optional[any] = None,
        details: Optional[dict] = None
    ) -> ValidationError:
        """Cria um erro de validação."""
        return ValidationError(
            severity=severity,
            category=self.name,
            message=message,
            row_indices=row_indices,
            column=column,
            expected=expected,
            actual=actual,
            details=details
        )
    
    def validate_rows(
        self,
        df: pd.DataFrame,
        condition_func: Callable[[pd.Series], bool],
        error_message: str,
        severity: Severity,
        column: Optional[str] = None
    ) -> list[ValidationError]:
        """Valida linhas com base em uma condição."""
        errors = []
        
        invalid_mask = ~df.apply(condition_func, axis=1)
        invalid_indices = df[invalid_mask].index.tolist()
        
        if invalid_indices:
            errors.append(self.create_error(
                severity=severity,
                message=f"{error_message} ({len(invalid_indices)} linhas)",
                row_indices=invalid_indices[:100],  # Limita a 100 para não sobrecarregar
                column=column
            ))
        
        return errors
    
    def timed_run(self, df: pd.DataFrame, config: ManifestConfig) -> ValidationResult:
        """Executa a validação medindo o tempo."""
        start = time.time()
        result = self.run(df, config)
        result.duration_seconds = time.time() - start
        return result
