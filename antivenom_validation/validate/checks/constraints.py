"""
Validação de restrições de campo (CNES, Telefone, etc).
"""

import re
import pandas as pd
from typing import Optional

from .base import BaseCheck
from ..models import ValidationResult, ValidationError, Severity
from ..manifest import ManifestConfig


class ConstraintsCheck(BaseCheck):
    """Valida restrições de formato em campos específicos."""
    
    @property
    def name(self) -> str:
        return "constraints"
    
    @property
    def description(self) -> str:
        return "Valida formato de CNES, Telefone e outros campos com padrões"
    
    def run(self, df: pd.DataFrame, config: ManifestConfig) -> ValidationResult:
        errors = []
        warnings = []
        info = []
        
        # Validar CNES
        if 'CNES' in df.columns:
            cnes_result = self._validate_cnes(df, config)
            if cnes_result:
                errors.extend(cnes_result.get('errors', []))
                warnings.extend(cnes_result.get('warnings', []))
                info.extend(cnes_result.get('info', []))
        
        # Validar Telefone
        if 'Telefone' in df.columns:
            tel_result = self._validate_telefone(df, config)
            if tel_result:
                warnings.extend(tel_result.get('warnings', []))
                info.extend(tel_result.get('info', []))
        
        # Validar outros campos com pattern no config
        if hasattr(config, 'constraints') and config.constraints:
            for col_name, constraint in config.constraints.items():
                if col_name in ['CNES', 'Telefone']:
                    continue  # Já validados acima
                
                if col_name in df.columns and hasattr(constraint, 'pattern') and constraint.pattern:
                    pattern_result = self._validate_pattern(df, col_name, constraint)
                    severity = getattr(constraint, 'severity', 'MINOR')
                    if severity == 'BLOCKER':
                        errors.extend(pattern_result)
                    elif severity == 'MAJOR':
                        errors.extend(pattern_result)
                    elif severity == 'MINOR':
                        warnings.extend(pattern_result)
                    else:
                        info.extend(pattern_result)
        
        # Validar missingness
        missingness_result = self._check_missingness(df, config)
        if missingness_result:
            errors.extend(missingness_result.get('errors', []))
            warnings.extend(missingness_result.get('warnings', []))
            info.extend(missingness_result.get('info', []))
        
        passed = len(errors) == 0
        
        return ValidationResult(
            category=self.name,
            passed=passed,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _validate_cnes(self, df: pd.DataFrame, config: ManifestConfig) -> dict:
        """Valida formato do CNES."""
        result = {'errors': [], 'warnings': [], 'info': []}
        
        # Usar configuração padrão se não houver config específico
        cnes_config = None
        if hasattr(config, 'constraints') and config.constraints:
            cnes_config = config.constraints.get('CNES')
        
        special_values = []
        if cnes_config and hasattr(cnes_config, 'special_values'):
            special_values = cnes_config.special_values
        else:
            # Valores padrão conhecidos do dataset
            special_values = ['Not informed', 'Not informed1-4']
        
        strip_chars = "\t \n"  # Valor padrão
        if cnes_config and hasattr(cnes_config, 'strip_chars') and cnes_config.strip_chars:
            strip_chars = cnes_config.strip_chars
            
        pattern = r'^\d{6,8}$'  # Valor padrão
        if cnes_config and hasattr(cnes_config, 'pattern') and cnes_config.pattern:
            pattern = cnes_config.pattern
        
        invalid_indices = []
        special_value_indices = []
        
        for idx, val in df['CNES'].items():
            if pd.isna(val):
                continue
            
            # Limpar valor
            cleaned = clean_cnes(str(val), strip_chars)
            
            # Verificar se é valor especial permitido
            if str(val) in special_values or cleaned in special_values:
                special_value_indices.append(idx)
                continue
            
            # Validar pattern
            if not re.match(pattern, cleaned):
                invalid_indices.append(idx)
        
        if invalid_indices:
            sev_str = cnes_config.severity if cnes_config and hasattr(cnes_config, 'severity') else 'MAJOR'
            try:
                severity = Severity[sev_str] if sev_str in Severity.__members__ else Severity.MAJOR
            except (KeyError, AttributeError):
                severity = Severity.MAJOR
            result['errors' if severity in [Severity.BLOCKER, Severity.MAJOR] else 'warnings'].append(
                self.create_error(
                    severity=severity,
                    message=f"CNES com formato inválido ({len(invalid_indices)} registros)",
                    column="CNES",
                    row_indices=invalid_indices[:50],
                    details={
                        "pattern": pattern,
                        "sample_invalid": [str(df.loc[i, 'CNES']) for i in invalid_indices[:5]]
                    }
                )
            )
        
        if special_value_indices:
            result['info'].append(
                self.create_error(
                    severity=Severity.INFO,
                    message=f"CNES com valores especiais permitidos ({len(special_value_indices)} registros)",
                    column="CNES",
                    row_indices=special_value_indices[:20]
                )
            )
        
        return result
    
    def _validate_telefone(self, df: pd.DataFrame, config: ManifestConfig) -> dict:
        """Valida formato de telefone."""
        result = {'warnings': [], 'info': []}
        
        tel_config = None
        if hasattr(config, 'constraints') and config.constraints:
            tel_config = config.constraints.get('Telefone')
        
        special_values = tel_config.allow_special_values if tel_config and hasattr(tel_config, 'allow_special_values') else ['Sem contato']
        pattern = tel_config.pattern if tel_config and hasattr(tel_config, 'pattern') else r'^[\d\s\-\(\)\/\+]+$'
        
        invalid_indices = []
        empty_indices = []
        
        for idx, val in df['Telefone'].items():
            if pd.isna(val) or str(val).strip() == '':
                empty_indices.append(idx)
                continue
            
            val_str = str(val).strip()
            
            # Verificar valores especiais
            if val_str in special_values:
                continue
            
            # Validar pattern
            if not re.match(pattern, val_str):
                invalid_indices.append(idx)
        
        if invalid_indices:
            result['warnings'].append(
                self.create_error(
                    severity=Severity.MINOR,
                    message=f"Telefones com formato inválido ({len(invalid_indices)} registros)",
                    column="Telefone",
                    row_indices=invalid_indices[:30],
                    details={
                        "sample_invalid": [str(df.loc[i, 'Telefone']) for i in invalid_indices[:5]]
                    }
                )
            )
        
        if empty_indices:
            result['info'].append(
                self.create_error(
                    severity=Severity.INFO,
                    message=f"Telefones vazios/nulos ({len(empty_indices)} registros)",
                    column="Telefone",
                    row_indices=empty_indices[:20]
                )
            )
        
        return result
    
    def _validate_pattern(self, df: pd.DataFrame, col_name: str, constraint) -> list[ValidationError]:
        """Valida coluna genérica contra pattern."""
        errors = []
        invalid_indices = []
        
        for idx, val in df[col_name].items():
            if pd.isna(val):
                if not constraint.allow_empty:
                    invalid_indices.append(idx)
                continue
            
            val_str = str(val)
            if constraint.strip_chars:
                val_str = val_str.strip(constraint.strip_chars)
            
            if not re.match(constraint.pattern, val_str):
                invalid_indices.append(idx)
        
        if invalid_indices:
            errors.append(
                self.create_error(
                    severity=Severity[constraint.severity],
                    message=f"'{col_name}' com formato inválido ({len(invalid_indices)} registros)",
                    column=col_name,
                    row_indices=invalid_indices[:50],
                    details={"pattern": constraint.pattern}
                )
            )
        
        return errors
    
    def _check_missingness(self, df: pd.DataFrame, config: ManifestConfig) -> dict:
        """Verifica taxa de valores nulos."""
        result = {'errors': [], 'warnings': [], 'info': []}
        
        # Usar configuração de missingness se disponível
        missingness_config = {}
        if hasattr(config, 'missingness') and config.missingness:
            missingness_config = config.missingness
        
        for col in df.columns:
            null_count = df[col].isna().sum()
            null_rate = null_count / len(df) if len(df) > 0 else 0
            
            miss_config = missingness_config.get(col, {})
            max_rate = miss_config.get('max_null_rate', 1.0)
            severity = miss_config.get('severity', 'INFO')
            
            if null_rate > max_rate:
                try:
                    sev_enum = Severity[severity] if severity in Severity.__members__ else Severity.INFO
                except (KeyError, AttributeError):
                    sev_enum = Severity.INFO
                    
                error = self.create_error(
                    severity=sev_enum,
                    message=f"'{col}' tem {null_rate:.1%} nulos (máximo: {max_rate:.1%})",
                    column=col,
                    details={"null_count": null_count, "null_rate": null_rate, "max_rate": max_rate}
                )
                
                if severity == 'BLOCKER':
                    result['errors'].append(error)
                elif severity == 'MAJOR':
                    result['errors'].append(error)
                elif severity == 'MINOR':
                    result['warnings'].append(error)
                else:
                    result['info'].append(error)
        
        return result


def clean_cnes(value: str, strip_chars: str = "\t \n") -> str:
    """Remove caracteres especiais do CNES."""
    result = value
    for char in strip_chars:
        result = result.replace(char, '')
    return result.strip()


def normalize_telefone(value: str) -> str:
    """Extrai apenas dígitos do telefone."""
    if pd.isna(value):
        return ''
    return re.sub(r'\D', '', str(value))
