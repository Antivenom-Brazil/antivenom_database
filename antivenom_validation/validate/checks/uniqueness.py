"""
Validação de unicidade (chaves primárias).
"""

import pandas as pd
from typing import List, Optional
from collections import Counter

from .base import BaseCheck
from ..models import ValidationResult, ValidationError, Severity
from ..manifest import ManifestConfig


class UniquenessCheck(BaseCheck):
    """Valida unicidade de chaves primárias e campos únicos."""
    
    @property
    def name(self) -> str:
        return "uniqueness"
    
    @property
    def description(self) -> str:
        return "Valida unicidade de CNES e outras chaves candidatas"
    
    def run(self, df: pd.DataFrame, config: ManifestConfig) -> ValidationResult:
        errors = []
        warnings = []
        info = []
        
        # Identificar colunas chave
        key_columns = self._get_key_columns(df, config)
        
        for col in key_columns:
            if col not in df.columns:
                continue
            
            result = self._validate_uniqueness(df, col, config)
            errors.extend(result.get('errors', []))
            warnings.extend(result.get('warnings', []))
            info.extend(result.get('info', []))
        
        # Validar unicidade composta (se configurado)
        if config.composite_keys:
            for key_set in config.composite_keys:
                if all(k in df.columns for k in key_set):
                    result = self._validate_composite_uniqueness(df, key_set, config)
                    errors.extend(result.get('errors', []))
                    warnings.extend(result.get('warnings', []))
        
        passed = len(errors) == 0
        
        return ValidationResult(
            category=self.name,
            passed=passed,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _get_key_columns(self, df: pd.DataFrame, config: ManifestConfig) -> List[str]:
        """Retorna colunas que devem ser únicas."""
        if config.primary_keys:
            return config.primary_keys
        
        # Padrão: CNES
        default_keys = ['CNES']
        return [k for k in default_keys if k in df.columns]
    
    def _validate_uniqueness(self, df: pd.DataFrame, column: str, config: ManifestConfig) -> dict:
        """Valida unicidade de uma coluna."""
        result = {'errors': [], 'warnings': [], 'info': []}
        
        # Filtrar valores não-nulos para análise de unicidade
        values = df[column].dropna()
        
        if len(values) == 0:
            result['info'].append(
                self.create_error(
                    severity=Severity.INFO,
                    message=f"Coluna '{column}' está vazia, unicidade não validada"
                )
            )
            return result
        
        # Normalizar valores (limpar espaços, tabs)
        normalized_values = values.astype(str).str.strip().str.replace(r'\s+', '', regex=True)
        
        # Encontrar duplicatas
        value_counts = Counter(normalized_values)
        duplicates = {v: c for v, c in value_counts.items() if c > 1}
        
        if duplicates:
            # Encontrar índices das duplicatas
            dup_indices = []
            for value in duplicates.keys():
                indices = df[normalized_values.reindex(df.index).fillna('') == value].index.tolist()
                dup_indices.extend(indices)
            
            total_dup_records = sum(duplicates.values())
            unique_dup_values = len(duplicates)
            
            # Determinar severidade
            dup_percent = total_dup_records / len(df) * 100
            if dup_percent > 5:
                severity = Severity.BLOCKER
            elif dup_percent > 1:
                severity = Severity.MAJOR
            else:
                severity = Severity.MINOR
            
            result['errors'].append(
                self.create_error(
                    severity=severity,
                    message=f"Valores duplicados em '{column}': {total_dup_records} registros ({unique_dup_values} valores únicos)",
                    row_indices=dup_indices[:50],
                    details={
                        "column": column,
                        "total_duplicates": total_dup_records,
                        "unique_duplicate_values": unique_dup_values,
                        "duplicate_percent": round(dup_percent, 2),
                        "top_duplicates": [
                            {"value": v, "count": c}
                            for v, c in sorted(duplicates.items(), key=lambda x: -x[1])[:10]
                        ]
                    }
                )
            )
        else:
            result['info'].append(
                self.create_error(
                    severity=Severity.INFO,
                    message=f"Coluna '{column}' é única ({len(values)} valores não-nulos)"
                )
            )
        
        return result
    
    def _validate_composite_uniqueness(self, df: pd.DataFrame, columns: List[str], config: ManifestConfig) -> dict:
        """Valida unicidade de chave composta."""
        result = {'errors': [], 'warnings': [], 'info': []}
        
        # Criar chave composta
        composite_key = df[columns].astype(str).agg('|'.join, axis=1)
        
        # Encontrar duplicatas
        duplicates = df[composite_key.duplicated(keep=False)]
        
        if len(duplicates) > 0:
            dup_indices = duplicates.index.tolist()
            
            result['errors'].append(
                self.create_error(
                    severity=Severity.MAJOR,
                    message=f"Chave composta duplicada {columns}: {len(duplicates)} registros",
                    row_indices=dup_indices[:50],
                    details={
                        "columns": columns,
                        "total_duplicates": len(duplicates)
                    }
                )
            )
        
        return result


def find_near_duplicates(df: pd.DataFrame, column: str, threshold: float = 0.9) -> List[tuple]:
    """Encontra valores quase duplicados usando similaridade."""
    from difflib import SequenceMatcher
    
    values = df[column].dropna().unique().tolist()
    near_duplicates = []
    
    for i, v1 in enumerate(values):
        for v2 in values[i+1:]:
            similarity = SequenceMatcher(None, str(v1), str(v2)).ratio()
            if similarity >= threshold and v1 != v2:
                near_duplicates.append((v1, v2, round(similarity, 3)))
    
    return sorted(near_duplicates, key=lambda x: -x[2])
