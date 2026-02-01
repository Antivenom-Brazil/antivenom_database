"""
Validação de parsing e normalização de dados.
"""

import pandas as pd
import unicodedata
from typing import Optional

from .base import BaseCheck
from ..models import ValidationResult, ValidationError, Severity
from ..manifest import ManifestConfig


class ParsingCheck(BaseCheck):
    """Valida e normaliza parsing de dados."""
    
    @property
    def name(self) -> str:
        return "parsing"
    
    @property
    def description(self) -> str:
        return "Valida normalização de dados (whitespace, unicode, decimais)"
    
    def run(self, df: pd.DataFrame, config: ManifestConfig) -> ValidationResult:
        errors = []
        warnings = []
        info = []
        
        # Verificar whitespace extra
        whitespace_issues = self._check_whitespace(df)
        if whitespace_issues:
            warnings.append(self.create_error(
                severity=Severity.MINOR,
                message=f"Valores com whitespace extra em {len(whitespace_issues)} colunas",
                details={"columns": whitespace_issues}
            ))
        
        # Verificar caracteres Unicode problemáticos
        unicode_issues = self._check_unicode(df)
        if unicode_issues:
            info.append(self.create_error(
                severity=Severity.INFO,
                message=f"Caracteres Unicode especiais em {len(unicode_issues)} colunas",
                details={"columns": unicode_issues}
            ))
        
        # Verificar valores numéricos em colunas de coordenadas
        if 'Lat' in df.columns:
            lat_issues = self._check_numeric_column(df, 'Lat')
            if lat_issues:
                errors.append(self.create_error(
                    severity=Severity.MAJOR,
                    message=f"Valores não numéricos em Lat ({len(lat_issues)} linhas)",
                    column="Lat",
                    row_indices=lat_issues[:50]
                ))
        
        if 'Lon' in df.columns:
            lon_issues = self._check_numeric_column(df, 'Lon')
            if lon_issues:
                errors.append(self.create_error(
                    severity=Severity.MAJOR,
                    message=f"Valores não numéricos em Lon ({len(lon_issues)} linhas)",
                    column="Lon",
                    row_indices=lon_issues[:50]
                ))
        
        passed = len(errors) == 0
        
        return ValidationResult(
            category=self.name,
            passed=passed,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _check_whitespace(self, df: pd.DataFrame) -> list[str]:
        """Verifica colunas com whitespace extra."""
        issues = []
        
        for col in df.select_dtypes(include=['object']).columns:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            
            # Verifica se há diferença após strip
            has_whitespace = (series.astype(str) != series.astype(str).str.strip()).any()
            if has_whitespace:
                issues.append(col)
        
        return issues
    
    def _check_unicode(self, df: pd.DataFrame) -> list[dict]:
        """Verifica caracteres Unicode especiais (NBSP, etc)."""
        issues = []
        
        special_chars = {
            '\xa0': 'NBSP',
            '\u200b': 'Zero-width space',
            '\u2013': 'En-dash',
            '\u2014': 'Em-dash'
        }
        
        for col in df.select_dtypes(include=['object']).columns:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            
            col_issues = []
            for char, name in special_chars.items():
                if series.astype(str).str.contains(char, regex=False).any():
                    col_issues.append(name)
            
            if col_issues:
                issues.append({"column": col, "special_chars": col_issues})
        
        return issues
    
    def _check_numeric_column(self, df: pd.DataFrame, col: str) -> list[int]:
        """Verifica se coluna numérica tem valores não-numéricos."""
        if df[col].dtype in ['float64', 'float32', 'int64', 'int32']:
            # Já é numérico, verificar NaN inesperados
            return []
        
        # Tentar converter e encontrar falhas
        invalid_indices = []
        for idx, val in df[col].items():
            if pd.isna(val):
                continue
            try:
                float(str(val).replace(',', '.'))
            except (ValueError, TypeError):
                invalid_indices.append(idx)
        
        return invalid_indices


def normalize_dataframe(df: pd.DataFrame, config: ManifestConfig) -> pd.DataFrame:
    """Aplica normalizações ao DataFrame."""
    df = df.copy()
    
    # Trim whitespace em colunas string
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
    
    # Normalizar Unicode (NFC)
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].apply(
            lambda x: unicodedata.normalize('NFC', x) if isinstance(x, str) else x
        )
    
    return df


def convert_decimal_comma(series: pd.Series) -> pd.Series:
    """Converte vírgula decimal para ponto."""
    def convert(val):
        if pd.isna(val):
            return val
        if isinstance(val, str):
            return float(val.replace(',', '.'))
        return val
    
    return series.apply(convert)
