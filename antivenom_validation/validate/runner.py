"""
Runner principal - orquestra execução dos checks.
"""

import pandas as pd
from pathlib import Path
from typing import List, Optional, Type, Dict, Any
from datetime import datetime
import time

from .models import ValidationReport, ValidationResult, Severity
from .manifest import ManifestConfig, load_manifest
from .checks import ALL_CHECKS, BaseCheck


class ValidationRunner:
    """Orquestra execução de validações."""
    
    def __init__(
        self,
        config: Optional[ManifestConfig] = None,
        checks: Optional[List[Type[BaseCheck]]] = None,
        skip_checks: Optional[List[str]] = None
    ):
        self.config = config or ManifestConfig()
        self.checks = checks or ALL_CHECKS
        self.skip_checks = skip_checks or []
    
    def run(self, df: pd.DataFrame) -> ValidationReport:
        """Executa todas as validações."""
        start_time = time.perf_counter()
        results = []
        
        for check_class in self.checks:
            check = check_class()
            
            if check.name in self.skip_checks:
                continue
            
            try:
                result = check.timed_run(df, self.config)
                results.append(result)
            except Exception as e:
                # Captura erro e cria resultado de falha
                import traceback
                tb_str = traceback.format_exc()
                results.append(
                    ValidationResult(
                        category=check.name,
                        passed=False,
                        errors=[{
                            "severity": Severity.BLOCKER.value,
                            "message": f"Erro na execução do check: {str(e)}",
                            "details": {
                                "exception": str(type(e).__name__),
                                "traceback": tb_str
                            }
                        }],
                        warnings=[],
                        info=[]
                    )
                )
        
        total_time = time.perf_counter() - start_time
        
        # Determinar status geral
        passed = all(r.passed for r in results)
        
        return ValidationReport(
            timestamp=datetime.now(),
            data_file=self.config.input_file or "unknown",
            row_count=len(df),
            column_count=len(df.columns),
            results=results,
            duration_seconds=round(total_time, 3)
        )
    
    @classmethod
    def from_manifest(cls, manifest_path: str) -> 'ValidationRunner':
        """Cria runner a partir de arquivo manifest."""
        config = load_manifest(manifest_path)
        return cls(config=config)


def run_validation(
    file_path: str,
    manifest_path: Optional[str] = None,
    skip_checks: Optional[List[str]] = None,
    output_dir: Optional[str] = None
) -> ValidationReport:
    """Função de conveniência para executar validação."""
    
    # Carregar config
    if manifest_path:
        config = load_manifest(manifest_path)
    else:
        config = ManifestConfig()
    
    config.input_file = file_path
    
    # Carregar dados
    df = load_dataframe(file_path, config)
    
    # Criar runner e executar
    runner = ValidationRunner(config=config, skip_checks=skip_checks)
    report = runner.run(df)
    
    return report


def load_dataframe(file_path: str, config: ManifestConfig) -> pd.DataFrame:
    """Carrega DataFrame a partir de arquivo."""
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    
    # Determinar formato
    suffix = path.suffix.lower()
    
    if suffix in ['.xlsx', '.xls']:
        df = pd.read_excel(
            file_path,
            sheet_name=config.sheet_name or 0,
            engine='openpyxl' if suffix == '.xlsx' else None
        )
    elif suffix == '.csv':
        df = pd.read_csv(
            file_path,
            encoding=config.encoding or 'utf-8',
            sep=config.delimiter or ','
        )
    elif suffix == '.parquet':
        df = pd.read_parquet(file_path)
    else:
        raise ValueError(f"Formato não suportado: {suffix}")
    
    return df


def get_summary_stats(report: ValidationReport) -> Dict[str, Any]:
    """Extrai estatísticas resumidas do relatório."""
    total_errors = 0
    total_warnings = 0
    total_info = 0
    blocker_count = 0
    major_count = 0
    minor_count = 0
    
    for result in report.results:
        total_errors += len(result.errors)
        total_warnings += len(result.warnings)
        total_info += len(result.info)
        
        for error in result.errors:
            severity = error.severity if hasattr(error, 'severity') else error.get('severity', '')
            if severity == Severity.BLOCKER or severity == 'BLOCKER':
                blocker_count += 1
            elif severity == Severity.MAJOR or severity == 'MAJOR':
                major_count += 1
            elif severity == Severity.MINOR or severity == 'MINOR':
                minor_count += 1
    
    passed_checks = sum(1 for r in report.results if r.passed)
    failed_checks = len(report.results) - passed_checks
    
    return {
        "passed": report.passed,
        "total_checks": len(report.results),
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "total_info": total_info,
        "blocker_count": blocker_count,
        "major_count": major_count,
        "minor_count": minor_count,
        "execution_time": report.execution_time
    }
