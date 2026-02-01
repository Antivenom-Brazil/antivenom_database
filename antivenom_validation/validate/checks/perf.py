"""
Validação de performance (smoke tests).
"""

import pandas as pd
import time
from typing import Optional, Dict, Any

from .base import BaseCheck
from ..models import ValidationResult, ValidationError, Severity
from ..manifest import ManifestConfig


class PerfCheck(BaseCheck):
    """Valida performance e tempo de carregamento."""
    
    # Thresholds padrão
    DEFAULT_THRESHOLDS = {
        "load_time_warn": 5.0,      # segundos
        "load_time_error": 30.0,    # segundos
        "memory_warn_mb": 500,      # MB
        "memory_error_mb": 2000,    # MB
        "row_threshold": 1_000_000  # linhas para warning
    }
    
    @property
    def name(self) -> str:
        return "perf"
    
    @property
    def description(self) -> str:
        return "Mede tempo de carregamento e uso de memória"
    
    def run(self, df: pd.DataFrame, config: ManifestConfig) -> ValidationResult:
        errors = []
        warnings = []
        info = []
        
        # Medir uso de memória
        memory_result = self._check_memory(df, config)
        errors.extend(memory_result.get('errors', []))
        warnings.extend(memory_result.get('warnings', []))
        info.extend(memory_result.get('info', []))
        
        # Verificar tamanho do dataset
        size_result = self._check_size(df, config)
        warnings.extend(size_result.get('warnings', []))
        info.extend(size_result.get('info', []))
        
        # Medir tempo de operações básicas
        ops_result = self._benchmark_basic_ops(df)
        info.extend(ops_result.get('info', []))
        
        passed = len(errors) == 0
        
        return ValidationResult(
            category=self.name,
            passed=passed,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _check_memory(self, df: pd.DataFrame, config: ManifestConfig) -> dict:
        """Verifica uso de memória."""
        result = {'errors': [], 'warnings': [], 'info': []}
        
        memory_bytes = df.memory_usage(deep=True).sum()
        memory_mb = memory_bytes / 1024 / 1024
        
        thresholds = self._get_thresholds(config)
        
        if memory_mb > thresholds['memory_error_mb']:
            result['errors'].append(
                self.create_error(
                    severity=Severity.BLOCKER,
                    message=f"Uso de memória muito alto: {memory_mb:.1f} MB",
                    details={
                        "memory_mb": round(memory_mb, 2),
                        "threshold_mb": thresholds['memory_error_mb']
                    }
                )
            )
        elif memory_mb > thresholds['memory_warn_mb']:
            result['warnings'].append(
                self.create_error(
                    severity=Severity.MINOR,
                    message=f"Uso de memória elevado: {memory_mb:.1f} MB",
                    details={
                        "memory_mb": round(memory_mb, 2),
                        "threshold_mb": thresholds['memory_warn_mb']
                    }
                )
            )
        else:
            result['info'].append(
                self.create_error(
                    severity=Severity.INFO,
                    message=f"Uso de memória: {memory_mb:.2f} MB",
                    details={
                        "memory_bytes": memory_bytes,
                        "memory_mb": round(memory_mb, 2)
                    }
                )
            )
        
        # Breakdown por coluna
        memory_by_col = df.memory_usage(deep=True).to_dict()
        result['info'].append(
            self.create_error(
                severity=Severity.INFO,
                message="Breakdown de memória por coluna",
                details={
                    "per_column_bytes": {
                        col: bytes_val 
                        for col, bytes_val in memory_by_col.items() 
                        if col != 'Index'
                    }
                }
            )
        )
        
        return result
    
    def _check_size(self, df: pd.DataFrame, config: ManifestConfig) -> dict:
        """Verifica tamanho do dataset."""
        result = {'warnings': [], 'info': []}
        
        thresholds = self._get_thresholds(config)
        
        if len(df) > thresholds['row_threshold']:
            result['warnings'].append(
                self.create_error(
                    severity=Severity.MINOR,
                    message=f"Dataset grande: {len(df):,} linhas",
                    details={
                        "rows": len(df),
                        "threshold": thresholds['row_threshold']
                    }
                )
            )
        
        result['info'].append(
            self.create_error(
                severity=Severity.INFO,
                message=f"Tamanho do dataset: {len(df):,} linhas × {len(df.columns)} colunas",
                details={
                    "rows": len(df),
                    "columns": len(df.columns),
                    "total_cells": len(df) * len(df.columns)
                }
            )
        )
        
        return result
    
    def _benchmark_basic_ops(self, df: pd.DataFrame) -> dict:
        """Mede tempo de operações básicas."""
        result = {'info': []}
        
        benchmarks = {}
        
        # Iteração
        start = time.perf_counter()
        _ = list(df.iterrows())[:100]  # Apenas 100 primeiras
        benchmarks['iterate_100_rows'] = time.perf_counter() - start
        
        # Filtro
        if 'Region' in df.columns:
            start = time.perf_counter()
            _ = df[df['Region'] == df['Region'].iloc[0] if len(df) > 0 else True]
            benchmarks['filter_by_region'] = time.perf_counter() - start
        
        # GroupBy
        if 'FU' in df.columns:
            start = time.perf_counter()
            _ = df.groupby('FU').size()
            benchmarks['groupby_fu'] = time.perf_counter() - start
        
        # Sort
        start = time.perf_counter()
        _ = df.sort_values(by=df.columns[0])
        benchmarks['sort_first_column'] = time.perf_counter() - start
        
        result['info'].append(
            self.create_error(
                severity=Severity.INFO,
                message="Benchmark de operações básicas",
                details={
                    "timings_seconds": {k: round(v, 4) for k, v in benchmarks.items()}
                }
            )
        )
        
        return result
    
    def _get_thresholds(self, config: ManifestConfig) -> dict:
        """Retorna thresholds do config ou padrão."""
        thresholds = self.DEFAULT_THRESHOLDS.copy()
        
        if config.perf_thresholds:
            thresholds.update(config.perf_thresholds)
        
        return thresholds


def measure_load_time(file_path: str, **kwargs) -> Dict[str, Any]:
    """Mede tempo de carregamento de arquivo."""
    import os
    
    file_size_mb = os.path.getsize(file_path) / 1024 / 1024
    
    start = time.perf_counter()
    
    if file_path.endswith('.xlsx'):
        df = pd.read_excel(file_path, **kwargs)
    elif file_path.endswith('.csv'):
        df = pd.read_csv(file_path, **kwargs)
    else:
        raise ValueError(f"Formato não suportado: {file_path}")
    
    load_time = time.perf_counter() - start
    
    return {
        "file_path": file_path,
        "file_size_mb": round(file_size_mb, 2),
        "load_time_seconds": round(load_time, 3),
        "rows": len(df),
        "columns": len(df.columns),
        "throughput_mb_per_sec": round(file_size_mb / load_time, 2) if load_time > 0 else None
    }
