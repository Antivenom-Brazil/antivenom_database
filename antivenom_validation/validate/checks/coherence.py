"""
Validação de coerência entre campos.
"""

import pandas as pd
from typing import Optional

from .base import BaseCheck
from ..models import ValidationResult, ValidationError, Severity
from ..manifest import ManifestConfig


class CoherenceCheck(BaseCheck):
    """Valida coerência entre campos relacionados."""
    
    @property
    def name(self) -> str:
        return "coherence"
    
    @property
    def description(self) -> str:
        return "Valida FU↔Federal_Un, Region↔FU, Atendiment↔Atendime_1"
    
    def run(self, df: pd.DataFrame, config: ManifestConfig) -> ValidationResult:
        errors = []
        warnings = []
        info = []
        
        # Validar FU ↔ Federal_Un
        if 'FU' in df.columns and 'Federal_Un' in df.columns:
            fu_state_result = self._validate_fu_state(df, config)
            errors.extend(fu_state_result['errors'])
            warnings.extend(fu_state_result['warnings'])
        
        # Validar Region ↔ FU
        if 'Region' in df.columns and 'FU' in df.columns:
            region_fu_result = self._validate_region_fu(df, config)
            errors.extend(region_fu_result['errors'])
            warnings.extend(region_fu_result['warnings'])
        
        # Validar Atendiment ↔ Atendime_1 count
        if 'Atendiment' in df.columns and 'Atendime_1' in df.columns:
            atend_result = self._validate_atendimento_count(df, config)
            warnings.extend(atend_result['warnings'])
            info.extend(atend_result['info'])
        
        passed = len(errors) == 0
        
        return ValidationResult(
            category=self.name,
            passed=passed,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _validate_fu_state(self, df: pd.DataFrame, config: ManifestConfig) -> dict:
        """Valida mapeamento FU → Federal_Un."""
        result = {'errors': [], 'warnings': []}
        
        # Usar mapeamento do config ou padrão
        fu_to_state = config.fu_to_state if config.fu_to_state else self._get_default_fu_state_mapping()
        
        invalid_indices = []
        mismatches = {}
        
        for idx, row in df.iterrows():
            fu = row.get('FU')
            state = row.get('Federal_Un')
            
            if pd.isna(fu) or pd.isna(state):
                continue
            
            expected_states = fu_to_state.get(fu, [])
            if isinstance(expected_states, str):
                expected_states = [expected_states]
            
            if state not in expected_states:
                invalid_indices.append(idx)
                key = f"{fu} → {state}"
                mismatches[key] = mismatches.get(key, 0) + 1
        
        if invalid_indices:
            result['errors'].append(
                self.create_error(
                    severity=Severity.MAJOR,
                    message=f"FU não corresponde a Federal_Un ({len(invalid_indices)} registros)",
                    row_indices=invalid_indices[:50],
                    details={
                        "total_mismatches": len(invalid_indices),
                        "mismatch_types": dict(sorted(mismatches.items(), key=lambda x: -x[1])[:10])
                    }
                )
            )
        
        return result
    
    def _validate_region_fu(self, df: pd.DataFrame, config: ManifestConfig) -> dict:
        """Valida mapeamento Region → FU."""
        result = {'errors': [], 'warnings': []}
        
        # Usar mapeamento do config ou padrão
        fu_to_region = config.fu_to_region if config.fu_to_region else self._get_default_fu_region_mapping()
        
        # Inverter para FU → Region
        fu_region_map = {}
        for region, fus in fu_to_region.items():
            for fu in fus:
                fu_region_map[fu] = region
        
        invalid_indices = []
        mismatches = {}
        
        for idx, row in df.iterrows():
            fu = row.get('FU')
            region = row.get('Region')
            
            if pd.isna(fu) or pd.isna(region):
                continue
            
            expected_region = fu_region_map.get(fu)
            
            if expected_region and region != expected_region:
                invalid_indices.append(idx)
                key = f"{fu}:{region} (esperado: {expected_region})"
                mismatches[key] = mismatches.get(key, 0) + 1
        
        if invalid_indices:
            result['errors'].append(
                self.create_error(
                    severity=Severity.MAJOR,
                    message=f"Region inconsistente com FU ({len(invalid_indices)} registros)",
                    row_indices=invalid_indices[:50],
                    details={
                        "total_mismatches": len(invalid_indices),
                        "mismatch_types": dict(sorted(mismatches.items(), key=lambda x: -x[1])[:10])
                    }
                )
            )
        
        return result
    
    def _validate_atendimento_count(self, df: pd.DataFrame, config: ManifestConfig) -> dict:
        """Valida se contagem de itens em Atendiment == Atendime_1."""
        result = {'warnings': [], 'info': []}
        
        mismatch_indices = []
        
        for idx, row in df.iterrows():
            atend = row.get('Atendiment')
            atend_1 = row.get('Atendime_1')
            
            if pd.isna(atend) or pd.isna(atend_1):
                continue
            
            count_atend = count_comma_separated(str(atend))
            count_atend_1 = count_comma_separated(str(atend_1))
            
            if count_atend != count_atend_1:
                mismatch_indices.append(idx)
        
        if mismatch_indices:
            result['warnings'].append(
                self.create_error(
                    severity=Severity.MINOR,
                    message=f"Contagem de itens diferente entre Atendiment e Atendime_1 ({len(mismatch_indices)} registros)",
                    row_indices=mismatch_indices[:30],
                    details={"total_mismatches": len(mismatch_indices)}
                )
            )
        
        return result
    
    def _get_default_fu_state_mapping(self) -> dict:
        """Retorna mapeamento padrão FU → Estado."""
        return {
            'AC': ['Acre'],
            'AL': ['Alagoas'],
            'AM': ['Amazonas'],
            'AP': ['Amapá'],
            'BA': ['Bahia'],
            'CE': ['Ceará'],
            'DF': ['Distrito Federal'],
            'ES': ['Espírito Santo', 'Espiríto Santo'],
            'GO': ['Goiás'],
            'MA': ['Maranhão'],
            'MG': ['Minas Gerais'],
            'MS': ['Mato Grosso do Sul'],
            'MT': ['Mato Grosso'],
            'PA': ['Pará'],
            'PB': ['Paraíba'],
            'PE': ['Pernambuco'],
            'PI': ['Piauí'],
            'PR': ['Paraná'],
            'RJ': ['Rio de Janeiro'],
            'RN': ['Rio Grande do Norte', 'Rio grande do Norte'],
            'RO': ['Rondônia'],
            'RR': ['Roraima'],
            'RS': ['Rio Grande do Sul'],
            'SC': ['Santa Catarina'],
            'SE': ['Sergipe'],
            'SP': ['São Paulo'],
            'TO': ['Tocantins']
        }
    
    def _get_default_fu_region_mapping(self) -> dict:
        """Retorna mapeamento padrão Region → FUs."""
        return {
            'North': ['AC', 'AM', 'AP', 'PA', 'RO', 'RR', 'TO'],
            'Northeast': ['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'],
            'Midwest': ['DF', 'GO', 'MS', 'MT'],
            'Southeast': ['ES', 'MG', 'RJ', 'SP'],
            'South': ['PR', 'RS', 'SC']
        }


def count_comma_separated(value: str) -> int:
    """Conta itens separados por vírgula."""
    if not value or pd.isna(value):
        return 0
    
    items = [item.strip() for item in str(value).split(',') if item.strip()]
    return len(items)


def load_mapping(mapping_file: str) -> dict:
    """Carrega arquivo de mapeamento YAML."""
    import yaml
    from pathlib import Path
    
    path = Path(mapping_file)
    if not path.exists():
        return {}
    
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}
