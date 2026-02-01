"""
Validação de reprodutibilidade (hash, estabilidade).
"""

import pandas as pd
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any

from .base import BaseCheck
from ..models import ValidationResult, ValidationError, Severity
from ..manifest import ManifestConfig


class ReproducibilityCheck(BaseCheck):
    """Valida reprodutibilidade do dataset (hash, estabilidade)."""
    
    @property
    def name(self) -> str:
        return "reproducibility"
    
    @property
    def description(self) -> str:
        return "Calcula hash do dataset e verifica estabilidade"
    
    def run(self, df: pd.DataFrame, config: ManifestConfig) -> ValidationResult:
        errors = []
        warnings = []
        info = []
        
        # Calcular hash do dataset
        dataset_hash = self._compute_dataset_hash(df)
        
        info.append(
            self.create_error(
                severity=Severity.INFO,
                message=f"Hash do dataset: {dataset_hash[:16]}...",
                details={
                    "full_hash": dataset_hash,
                    "algorithm": "sha256",
                    "rows": len(df),
                    "columns": len(df.columns),
                    "computed_at": datetime.now().isoformat()
                }
            )
        )
        
        # Verificar hash esperado se configurado
        if config.expected_hash:
            if dataset_hash != config.expected_hash:
                errors.append(
                    self.create_error(
                        severity=Severity.BLOCKER,
                        message="Hash do dataset não corresponde ao esperado",
                        details={
                            "expected": config.expected_hash,
                            "actual": dataset_hash
                        }
                    )
                )
        
        # Verificar tamanho esperado
        if config.expected_rows:
            if len(df) != config.expected_rows:
                severity = Severity.MAJOR if abs(len(df) - config.expected_rows) > 10 else Severity.MINOR
                errors.append(
                    self.create_error(
                        severity=severity,
                        message=f"Número de linhas ({len(df)}) difere do esperado ({config.expected_rows})",
                        details={
                            "expected_rows": config.expected_rows,
                            "actual_rows": len(df),
                            "difference": len(df) - config.expected_rows
                        }
                    )
                )
        
        # Verificar colunas esperadas
        if config.expected_columns:
            missing_cols = set(config.expected_columns) - set(df.columns)
            extra_cols = set(df.columns) - set(config.expected_columns)
            
            if missing_cols:
                errors.append(
                    self.create_error(
                        severity=Severity.MAJOR,
                        message=f"Colunas esperadas ausentes: {missing_cols}",
                        details={"missing_columns": list(missing_cols)}
                    )
                )
            
            if extra_cols:
                warnings.append(
                    self.create_error(
                        severity=Severity.MINOR,
                        message=f"Colunas extras não esperadas: {extra_cols}",
                        details={"extra_columns": list(extra_cols)}
                    )
                )
        
        # Calcular estatísticas de estabilidade
        stability_info = self._compute_stability_stats(df)
        info.append(
            self.create_error(
                severity=Severity.INFO,
                message="Estatísticas de estabilidade calculadas",
                details=stability_info
            )
        )
        
        passed = len(errors) == 0
        
        return ValidationResult(
            category=self.name,
            passed=passed,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _compute_dataset_hash(self, df: pd.DataFrame) -> str:
        """Computa hash SHA256 do dataset."""
        # Ordenar para garantir reprodutibilidade
        df_sorted = df.sort_values(by=list(df.columns)).reset_index(drop=True)
        
        # Converter para string JSON-like (determinístico)
        content = df_sorted.to_json(orient='records', date_format='iso')
        
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _compute_stability_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Computa estatísticas de estabilidade."""
        stats = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "total_cells": len(df) * len(df.columns),
            "null_cells": df.isna().sum().sum(),
            "null_percent": round(df.isna().sum().sum() / (len(df) * len(df.columns)) * 100, 2),
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2)
        }
        
        # Hash por coluna (para detectar mudanças específicas)
        column_hashes = {}
        for col in df.columns:
            col_content = df[col].astype(str).to_json()
            column_hashes[col] = hashlib.md5(col_content.encode()).hexdigest()[:8]
        
        stats["column_hashes"] = column_hashes
        
        return stats


def compare_datasets(df1: pd.DataFrame, df2: pd.DataFrame) -> Dict[str, Any]:
    """Compara dois datasets para detectar diferenças."""
    comparison = {
        "rows_added": len(df2) - len(df1),
        "columns_match": list(df1.columns) == list(df2.columns),
        "columns_added": list(set(df2.columns) - set(df1.columns)),
        "columns_removed": list(set(df1.columns) - set(df2.columns))
    }
    
    # Comparar valores se colunas são iguais
    if comparison["columns_match"]:
        common_len = min(len(df1), len(df2))
        df1_subset = df1.head(common_len).reset_index(drop=True)
        df2_subset = df2.head(common_len).reset_index(drop=True)
        
        differences = (df1_subset != df2_subset).sum().sum()
        comparison["cell_differences"] = int(differences)
        comparison["match_percent"] = round((1 - differences / (common_len * len(df1.columns))) * 100, 2)
    
    return comparison
