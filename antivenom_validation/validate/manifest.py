"""
Parser e validador do manifest YAML.
"""

import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ColumnConfig:
    """Configuração de uma coluna."""
    name: str
    required: bool = True
    type: str = "string"
    aliases: list[str] = field(default_factory=list)


@dataclass
class ConstraintConfig:
    """Configuração de restrição de campo."""
    type: str = "string"
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    strip_chars: Optional[str] = None
    allow_empty: bool = False
    allow_special_values: list[str] = field(default_factory=list)
    severity: str = "MAJOR"


@dataclass
class VocabConfig:
    """Configuração de vocabulário controlado."""
    values: list[str] = field(default_factory=list)
    case_sensitive: bool = True
    allow_null: bool = False
    severity: str = "MAJOR"


@dataclass
class GeoConfig:
    """Configuração geoespacial."""
    lat_field: str = "Lat"
    lon_field: str = "Lon"
    lat_min: float = -90
    lat_max: float = 90
    lon_min: float = -180
    lon_max: float = 180
    brazil_lat_min: float = -55
    brazil_lat_max: float = 10
    brazil_lon_min: float = -80
    brazil_lon_max: float = -30
    check_duplicates: bool = True
    id_column: str = "CNES"


@dataclass
class CrossFieldConfig:
    """Configuração de validação entre campos."""
    description: str
    field_a: str
    field_b: str
    mapping_file: Optional[str] = None
    rule: Optional[str] = None
    tolerance: int = 0
    severity: str = "MAJOR"


@dataclass 
class ManifestConfig:
    """Configuração completa do manifest."""
    input_file: str
    source_type: str = "excel"
    sheet_name: Optional[str] = None
    columns: list[ColumnConfig] = field(default_factory=list)
    constraints: dict[str, ConstraintConfig] = field(default_factory=dict)
    controlled_vocab: dict[str, VocabConfig] = field(default_factory=dict)
    geospatial: Optional[GeoConfig] = None
    cross_field: dict[str, CrossFieldConfig] = field(default_factory=dict)
    uniqueness_columns: list[str] = field(default_factory=list)
    missingness: dict[str, dict] = field(default_factory=dict)
    reports_dir: str = "reports"
    
    # Mapeamentos carregados
    fu_to_state: dict[str, list[str]] = field(default_factory=dict)
    fu_to_region: dict[str, list[str]] = field(default_factory=dict)
    
    # Propriedades de compatibilidade
    @property
    def geo_config(self) -> Optional[GeoConfig]:
        return self.geospatial
    
    @property
    def primary_keys(self) -> list[str]:
        return self.uniqueness_columns
    
    @property
    def composite_keys(self) -> list:
        return []
    
    @property
    def expected_hash(self) -> Optional[str]:
        return None
    
    @property
    def expected_rows(self) -> Optional[int]:
        return None
    
    @property
    def expected_columns(self) -> Optional[list]:
        return [col.name for col in self.columns] if self.columns else None
    
    @property
    def perf_thresholds(self) -> Optional[dict]:
        return None
    
    @property
    def encoding(self) -> str:
        return 'utf-8'
    
    @property
    def delimiter(self) -> str:
        return ','


def load_manifest(path: str) -> ManifestConfig:
    """Carrega e parseia o manifest YAML."""
    manifest_path = Path(path)
    
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest não encontrado: {path}")
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    config = ManifestConfig(
        input_file=data.get('input', {}).get('file_path', ''),
        source_type=data.get('input', {}).get('source_type', 'excel'),
        sheet_name=data.get('input', {}).get('sheet_name'),
        reports_dir=data.get('output', {}).get('reports_dir', 'reports')
    )
    
    # Parse columns
    for col_data in data.get('columns', {}).get('expected', []):
        config.columns.append(ColumnConfig(
            name=col_data.get('name', ''),
            required=col_data.get('required', True),
            type=col_data.get('type', 'string'),
            aliases=col_data.get('aliases', [])
        ))
    
    # Parse constraints
    for col_name, constraint_data in data.get('constraints', {}).items():
        config.constraints[col_name] = ConstraintConfig(
            type=constraint_data.get('type', 'string'),
            pattern=constraint_data.get('pattern'),
            min_length=constraint_data.get('min_length'),
            max_length=constraint_data.get('max_length'),
            strip_chars=constraint_data.get('strip_chars'),
            allow_empty=constraint_data.get('allow_empty', False),
            allow_special_values=constraint_data.get('allow_special_values', []),
            severity=constraint_data.get('severity', 'MAJOR')
        )
    
    # Parse controlled vocab
    for col_name, vocab_data in data.get('controlled_vocab', {}).items():
        config.controlled_vocab[col_name] = VocabConfig(
            values=vocab_data.get('values', []),
            case_sensitive=vocab_data.get('case_sensitive', True),
            allow_null=vocab_data.get('allow_null', False),
            severity=vocab_data.get('severity', 'MAJOR')
        )
    
    # Parse geospatial
    geo_data = data.get('geospatial', {})
    if geo_data:
        plausible = geo_data.get('plausible_bounds', {})
        config.geospatial = GeoConfig(
            lat_field=geo_data.get('lat_field', 'Lat'),
            lon_field=geo_data.get('lon_field', 'Lon'),
            brazil_lat_min=plausible.get('lat_min', -55),
            brazil_lat_max=plausible.get('lat_max', 10),
            brazil_lon_min=plausible.get('lon_min', -80),
            brazil_lon_max=plausible.get('lon_max', -30),
            check_duplicates=geo_data.get('duplicate_coords', {}).get('check', True),
            id_column=geo_data.get('duplicate_coords', {}).get('id_column', 'CNES')
        )
    
    # Parse cross-field rules
    for rule_name, rule_data in data.get('cross_field', {}).items():
        config.cross_field[rule_name] = CrossFieldConfig(
            description=rule_data.get('description', ''),
            field_a=rule_data.get('field_a', ''),
            field_b=rule_data.get('field_b', ''),
            mapping_file=rule_data.get('mapping_file'),
            rule=rule_data.get('rule'),
            tolerance=rule_data.get('tolerance', 0),
            severity=rule_data.get('severity', 'MAJOR')
        )
    
    # Parse uniqueness
    uniqueness_data = data.get('uniqueness', {}).get('primary_key', {})
    config.uniqueness_columns = uniqueness_data.get('columns', ['CNES'])
    
    # Parse missingness
    config.missingness = data.get('missingness', {}).get('per_field', {})
    
    # Load mappings
    manifest_dir = manifest_path.parent
    mappings_dir = manifest_dir / 'mappings'
    
    fu_state_path = mappings_dir / 'fu_to_state.yaml'
    if fu_state_path.exists():
        with open(fu_state_path, 'r', encoding='utf-8') as f:
            config.fu_to_state = yaml.safe_load(f) or {}
    
    fu_region_path = mappings_dir / 'fu_to_region.yaml'
    if fu_region_path.exists():
        with open(fu_region_path, 'r', encoding='utf-8') as f:
            config.fu_to_region = yaml.safe_load(f) or {}
    
    return config


def get_default_manifest() -> dict:
    """Retorna um manifest padrão."""
    return {
        'input': {
            'source_type': 'excel',
            'file_path': 'antivenom_limpo4_corrigido.xlsx'
        },
        'columns': {
            'expected': [
                {'name': 'Region', 'required': True},
                {'name': 'Federal_Un', 'required': True},
                {'name': 'FU', 'required': True},
                {'name': 'Municipio', 'required': True},
                {'name': 'CNES', 'required': True},
                {'name': 'Lat', 'required': True},
                {'name': 'Lon', 'required': True}
            ]
        }
    }
