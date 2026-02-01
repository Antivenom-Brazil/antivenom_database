"""
Validação geoespacial (coordenadas).
"""

import pandas as pd
from typing import Optional, Tuple, List

from .base import BaseCheck
from ..models import ValidationResult, ValidationError, Severity
from ..manifest import ManifestConfig


class GeospatialCheck(BaseCheck):
    """Valida coordenadas geoespaciais."""
    
    # Limites do Brasil (bounding box aproximado)
    BRAZIL_BOUNDS = {
        'lat_min': -33.75,
        'lat_max': 5.27,
        'lon_min': -73.99,
        'lon_max': -32.39
    }
    
    @property
    def name(self) -> str:
        return "geospatial"
    
    @property
    def description(self) -> str:
        return "Valida coordenadas dentro do Brasil e detecta anomalias"
    
    def run(self, df: pd.DataFrame, config: ManifestConfig) -> ValidationResult:
        errors = []
        warnings = []
        info = []
        
        # Identificar colunas de lat/lon
        lat_col = self._find_column(df, ['Lat', 'lat', 'latitude', 'Latitude'])
        lon_col = self._find_column(df, ['Lon', 'lon', 'longitude', 'Longitude', 'Lng', 'lng'])
        
        if not lat_col or not lon_col:
            return ValidationResult(
                category=self.name,
                passed=True,
                errors=[],
                warnings=[],
                info=[self.create_error(
                    severity=Severity.INFO,
                    message="Colunas de coordenadas não encontradas"
                )]
            )
        
        # Extrair bounds do config se disponível
        bounds = self._get_bounds(config)
        
        # Validar bounds gerais
        out_of_bounds_result = self._validate_bounds(df, lat_col, lon_col, bounds)
        errors.extend(out_of_bounds_result['errors'])
        warnings.extend(out_of_bounds_result['warnings'])
        
        # Validar valores nulos
        null_result = self._validate_nulls(df, lat_col, lon_col)
        warnings.extend(null_result['warnings'])
        info.extend(null_result['info'])
        
        # Detectar coordenadas duplicadas
        duplicate_result = self._detect_duplicate_coordinates(df, lat_col, lon_col)
        warnings.extend(duplicate_result['warnings'])
        info.extend(duplicate_result['info'])
        
        # Detectar possíveis outliers
        outlier_result = self._detect_outliers(df, lat_col, lon_col)
        warnings.extend(outlier_result['warnings'])
        
        # Detectar coordenadas suspeitas (ex: (0, 0))
        suspicious_result = self._detect_suspicious(df, lat_col, lon_col)
        errors.extend(suspicious_result['errors'])
        
        passed = len(errors) == 0
        
        return ValidationResult(
            category=self.name,
            passed=passed,
            errors=errors,
            warnings=warnings,
            info=info
        )
    
    def _find_column(self, df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """Encontra coluna pelo nome."""
        for col in candidates:
            if col in df.columns:
                return col
        return None
    
    def _get_bounds(self, config: ManifestConfig) -> dict:
        """Retorna bounds do config ou padrão (Brasil)."""
        if config.geo_config and config.geo_config.bounds:
            return config.geo_config.bounds
        return self.BRAZIL_BOUNDS
    
    def _validate_bounds(self, df: pd.DataFrame, lat_col: str, lon_col: str, bounds: dict) -> dict:
        """Valida coordenadas dentro dos limites."""
        result = {'errors': [], 'warnings': []}
        
        out_of_bounds_indices = []
        details = {'lat_violations': [], 'lon_violations': []}
        
        lat_min = bounds.get('lat_min', -90)
        lat_max = bounds.get('lat_max', 90)
        lon_min = bounds.get('lon_min', -180)
        lon_max = bounds.get('lon_max', 180)
        
        for idx, row in df.iterrows():
            lat = row.get(lat_col)
            lon = row.get(lon_col)
            
            if pd.isna(lat) or pd.isna(lon):
                continue
            
            try:
                lat = float(lat)
                lon = float(lon)
            except (ValueError, TypeError):
                out_of_bounds_indices.append(idx)
                continue
            
            is_out = False
            
            if lat < lat_min or lat > lat_max:
                is_out = True
                details['lat_violations'].append({
                    'idx': idx,
                    'value': lat,
                    'expected': f"[{lat_min}, {lat_max}]"
                })
            
            if lon < lon_min or lon > lon_max:
                is_out = True
                details['lon_violations'].append({
                    'idx': idx,
                    'value': lon,
                    'expected': f"[{lon_min}, {lon_max}]"
                })
            
            if is_out:
                out_of_bounds_indices.append(idx)
        
        if out_of_bounds_indices:
            severity = Severity.MAJOR if len(out_of_bounds_indices) > 10 else Severity.MINOR
            result['errors'].append(
                self.create_error(
                    severity=severity,
                    message=f"Coordenadas fora dos limites ({len(out_of_bounds_indices)} registros)",
                    row_indices=out_of_bounds_indices[:50],
                    details={
                        "total": len(out_of_bounds_indices),
                        "bounds": bounds,
                        "lat_violations": len(details['lat_violations']),
                        "lon_violations": len(details['lon_violations']),
                        "sample_violations": details['lat_violations'][:5] + details['lon_violations'][:5]
                    }
                )
            )
        
        return result
    
    def _validate_nulls(self, df: pd.DataFrame, lat_col: str, lon_col: str) -> dict:
        """Valida coordenadas nulas."""
        result = {'warnings': [], 'info': []}
        
        null_lat = df[lat_col].isna().sum()
        null_lon = df[lon_col].isna().sum()
        
        if null_lat > 0 or null_lon > 0:
            null_indices = df[df[lat_col].isna() | df[lon_col].isna()].index.tolist()
            
            severity = Severity.MAJOR if len(null_indices) > len(df) * 0.05 else Severity.MINOR
            result['warnings'].append(
                self.create_error(
                    severity=severity,
                    message=f"Coordenadas nulas: {null_lat} Lat, {null_lon} Lon",
                    row_indices=null_indices[:50],
                    details={
                        "null_lat": null_lat,
                        "null_lon": null_lon,
                        "percent": round((null_lat + null_lon) / (len(df) * 2) * 100, 2)
                    }
                )
            )
        
        return result
    
    def _detect_duplicate_coordinates(self, df: pd.DataFrame, lat_col: str, lon_col: str) -> dict:
        """Detecta coordenadas duplicadas exatas."""
        result = {'warnings': [], 'info': []}
        
        coord_df = df[[lat_col, lon_col]].dropna()
        duplicates = coord_df[coord_df.duplicated(keep=False)]
        
        if len(duplicates) > 0:
            # Agrupar duplicatas
            dup_groups = duplicates.groupby([lat_col, lon_col]).size()
            dup_counts = dup_groups[dup_groups > 1]
            
            if len(dup_counts) > 0:
                result['info'].append(
                    self.create_error(
                        severity=Severity.INFO,
                        message=f"Coordenadas duplicadas: {len(duplicates)} registros em {len(dup_counts)} localizações únicas",
                        details={
                            "total_duplicates": len(duplicates),
                            "unique_locations": len(dup_counts),
                            "top_duplicates": [
                                {"coord": f"({lat}, {lon})", "count": count}
                                for (lat, lon), count in dup_counts.head(10).items()
                            ]
                        }
                    )
                )
        
        return result
    
    def _detect_outliers(self, df: pd.DataFrame, lat_col: str, lon_col: str) -> dict:
        """Detecta outliers usando IQR."""
        result = {'warnings': []}
        
        outlier_indices = []
        
        for col in [lat_col, lon_col]:
            values = pd.to_numeric(df[col], errors='coerce').dropna()
            
            if len(values) < 10:
                continue
            
            q1 = values.quantile(0.25)
            q3 = values.quantile(0.75)
            iqr = q3 - q1
            
            lower_bound = q1 - 3 * iqr
            upper_bound = q3 + 3 * iqr
            
            col_outliers = df[(pd.to_numeric(df[col], errors='coerce') < lower_bound) | 
                             (pd.to_numeric(df[col], errors='coerce') > upper_bound)].index.tolist()
            outlier_indices.extend(col_outliers)
        
        outlier_indices = list(set(outlier_indices))
        
        if outlier_indices:
            result['warnings'].append(
                self.create_error(
                    severity=Severity.MINOR,
                    message=f"Possíveis outliers detectados (IQR×3): {len(outlier_indices)} registros",
                    row_indices=outlier_indices[:30],
                    details={"total_outliers": len(outlier_indices)}
                )
            )
        
        return result
    
    def _detect_suspicious(self, df: pd.DataFrame, lat_col: str, lon_col: str) -> dict:
        """Detecta coordenadas suspeitas (0,0), valores redondos excessivos."""
        result = {'errors': []}
        
        suspicious_indices = []
        
        for idx, row in df.iterrows():
            lat = row.get(lat_col)
            lon = row.get(lon_col)
            
            if pd.isna(lat) or pd.isna(lon):
                continue
            
            try:
                lat = float(lat)
                lon = float(lon)
            except (ValueError, TypeError):
                continue
            
            # Coordenada (0, 0) é suspeita
            if lat == 0 and lon == 0:
                suspicious_indices.append(idx)
                continue
            
            # Coordenadas muito redondas (ex: -23.0, -46.0)
            if lat == int(lat) and lon == int(lon):
                suspicious_indices.append(idx)
        
        if suspicious_indices:
            result['errors'].append(
                self.create_error(
                    severity=Severity.MINOR,
                    message=f"Coordenadas suspeitas (0,0 ou valores inteiros): {len(suspicious_indices)} registros",
                    row_indices=suspicious_indices[:30],
                    details={"total_suspicious": len(suspicious_indices)}
                )
            )
        
        return result


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula distância haversine em km."""
    from math import radians, cos, sin, sqrt, atan2
    
    R = 6371  # Raio da Terra em km
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c
