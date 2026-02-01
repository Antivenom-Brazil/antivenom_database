"""
Validação de schema/colunas.
"""

import pandas as pd
from typing import Optional

from .base import BaseCheck
from ..models import ValidationResult, ValidationError, Severity
from ..manifest import ManifestConfig


class SchemaCheck(BaseCheck):
    """Valida estrutura de colunas do DataFrame."""
    
    @property
    def name(self) -> str:
        return "schema"
    
    @property
    def description(self) -> str:
        return "Valida presença e tipos de colunas esperadas"
    
    def run(self, df: pd.DataFrame, config: ManifestConfig) -> ValidationResult:
        errors = []
        warnings = []
        info = []
        
        # Colunas presentes no DataFrame
        df_columns = set(df.columns)
        
        # Verificar colunas esperadas
        for col_config in config.columns:
            col_name = col_config.name
            
            # Verificar se coluna existe (diretamente ou via alias)
            found = col_name in df_columns
            found_alias = None
            
            if not found:
                for alias in col_config.aliases:
                    if alias in df_columns:
                        found = True
                        found_alias = alias
                        break
            
            if not found and col_config.required:
                errors.append(self.create_error(
                    severity=Severity.BLOCKER,
                    message=f"Coluna obrigatória '{col_name}' não encontrada",
                    column=col_name,
                    expected=col_name,
                    actual=None,
                    details={"aliases_checked": col_config.aliases}
                ))
            elif not found and not col_config.required:
                info.append(self.create_error(
                    severity=Severity.INFO,
                    message=f"Coluna opcional '{col_name}' não encontrada",
                    column=col_name
                ))
            elif found_alias:
                info.append(self.create_error(
                    severity=Severity.INFO,
                    message=f"Coluna '{col_name}' encontrada via alias '{found_alias}'",
                    column=col_name,
                    details={"alias_used": found_alias}
                ))
        
        # Verificar colunas inesperadas
        expected_names = set()
        for col_config in config.columns:
            expected_names.add(col_config.name)
            expected_names.update(col_config.aliases)
        
        unexpected = df_columns - expected_names
        if unexpected:
            info.append(self.create_error(
                severity=Severity.INFO,
                message=f"Colunas não documentadas encontradas: {sorted(unexpected)}",
                details={"unexpected_columns": sorted(unexpected)}
            ))
        
        # Verificar tipos de dados
        type_errors = self._check_column_types(df, config)
        warnings.extend(type_errors)
        
        passed = len(errors) == 0
        
        return ValidationResult(
            category=self.name,
            passed=passed,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _check_column_types(self, df: pd.DataFrame, config: ManifestConfig) -> list[ValidationError]:
        """Verifica se os tipos de dados estão corretos."""
        type_errors = []
        
        type_mapping = {
            'string': ['object', 'string'],
            'float': ['float64', 'float32', 'float'],
            'int': ['int64', 'int32', 'int'],
            'bool': ['bool']
        }
        
        for col_config in config.columns:
            if col_config.name not in df.columns:
                continue
            
            actual_type = str(df[col_config.name].dtype)
            expected_types = type_mapping.get(col_config.type, [col_config.type])
            
            if actual_type not in expected_types:
                type_errors.append(self.create_error(
                    severity=Severity.MINOR,
                    message=f"Tipo de '{col_config.name}' é '{actual_type}', esperado '{col_config.type}'",
                    column=col_config.name,
                    expected=col_config.type,
                    actual=actual_type
                ))
        
        return type_errors


def validate_expected_columns(df: pd.DataFrame, config: ManifestConfig) -> list[ValidationError]:
    """Função utilitária para validar colunas."""
    check = SchemaCheck()
    result = check.run(df, config)
    return result.errors + result.warnings


def resolve_aliases(df: pd.DataFrame, config: ManifestConfig) -> pd.DataFrame:
    """Renomeia colunas usando aliases para nomes canônicos."""
    df = df.copy()
    
    for col_config in config.columns:
        for alias in col_config.aliases:
            if alias in df.columns and col_config.name not in df.columns:
                df = df.rename(columns={alias: col_config.name})
                break
    
    return df
