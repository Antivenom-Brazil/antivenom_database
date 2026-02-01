"""
Validação de vocabulários controlados.
"""

import pandas as pd
import unicodedata
from typing import Optional

from .base import BaseCheck
from ..models import ValidationResult, ValidationError, Severity
from ..manifest import ManifestConfig


class VocabCheck(BaseCheck):
    """Valida valores contra vocabulários controlados."""
    
    @property
    def name(self) -> str:
        return "vocab"
    
    @property
    def description(self) -> str:
        return "Valida Region, FU, Federal_Un contra vocabulários permitidos"
    
    def run(self, df: pd.DataFrame, config: ManifestConfig) -> ValidationResult:
        errors = []
        warnings = []
        info = []
        
        for col_name, vocab_config in config.controlled_vocab.items():
            if col_name not in df.columns:
                continue
            
            result = self._check_vocabulary(df, col_name, vocab_config)
            
            severity = Severity[vocab_config.severity]
            if severity == Severity.BLOCKER:
                errors.extend(result)
            elif severity == Severity.MAJOR:
                errors.extend(result)
            elif severity == Severity.MINOR:
                warnings.extend(result)
            else:
                info.extend(result)
        
        passed = len(errors) == 0
        
        return ValidationResult(
            category=self.name,
            passed=passed,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _check_vocabulary(self, df: pd.DataFrame, col_name: str, vocab_config) -> list[ValidationError]:
        """Verifica valores contra vocabulário permitido."""
        errors = []
        
        allowed_values = set(vocab_config.values)
        
        # Se não é case sensitive, normalizar
        if not vocab_config.case_sensitive:
            allowed_values = {v.lower() for v in allowed_values}
        
        invalid_values = {}
        invalid_indices = []
        
        for idx, val in df[col_name].items():
            if pd.isna(val):
                if not vocab_config.allow_null:
                    invalid_indices.append(idx)
                    invalid_values[str(val)] = invalid_values.get(str(val), 0) + 1
                continue
            
            val_str = str(val).strip()
            check_val = val_str if vocab_config.case_sensitive else val_str.lower()
            
            if check_val not in allowed_values:
                invalid_indices.append(idx)
                invalid_values[val_str] = invalid_values.get(val_str, 0) + 1
        
        if invalid_indices:
            # Ordenar valores inválidos por frequência
            sorted_invalid = sorted(invalid_values.items(), key=lambda x: -x[1])
            
            errors.append(
                self.create_error(
                    severity=Severity[vocab_config.severity],
                    message=f"'{col_name}' contém {len(invalid_indices)} valores fora do vocabulário",
                    column=col_name,
                    row_indices=invalid_indices[:50],
                    expected=list(vocab_config.values)[:10],
                    actual=sorted_invalid[:10],
                    details={
                        "total_invalid": len(invalid_indices),
                        "unique_invalid": len(invalid_values),
                        "invalid_values": dict(sorted_invalid[:20])
                    }
                )
            )
        
        return errors


def get_invalid_values(series: pd.Series, vocab: list[str], case_sensitive: bool = True) -> set:
    """Retorna valores que não estão no vocabulário."""
    allowed = set(vocab) if case_sensitive else {v.lower() for v in vocab}
    
    invalid = set()
    for val in series.dropna().unique():
        check_val = str(val) if case_sensitive else str(val).lower()
        if check_val not in allowed:
            invalid.add(val)
    
    return invalid


def normalize_for_comparison(value: str, remove_accents: bool = False, lowercase: bool = False) -> str:
    """Normaliza valor para comparação."""
    result = str(value).strip()
    
    if remove_accents:
        result = ''.join(
            c for c in unicodedata.normalize('NFD', result)
            if unicodedata.category(c) != 'Mn'
        )
    
    if lowercase:
        result = result.lower()
    
    return result


def fuzzy_match(value: str, vocab: list[str], threshold: float = 0.8) -> Optional[str]:
    """Encontra a melhor correspondência aproximada no vocabulário."""
    from difflib import SequenceMatcher
    
    value_normalized = normalize_for_comparison(value, remove_accents=True, lowercase=True)
    
    best_match = None
    best_ratio = 0
    
    for v in vocab:
        v_normalized = normalize_for_comparison(v, remove_accents=True, lowercase=True)
        ratio = SequenceMatcher(None, value_normalized, v_normalized).ratio()
        
        if ratio > best_ratio and ratio >= threshold:
            best_ratio = ratio
            best_match = v
    
    return best_match
