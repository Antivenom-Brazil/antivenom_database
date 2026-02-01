"""
Geração de relatório JSON.
"""

import json
from pathlib import Path
from typing import Union
from datetime import datetime

from validate.models import ValidationReport


def generate_json_report(
    report: ValidationReport,
    output_dir: Union[str, Path]
) -> Path:
    """
    Gera relatório JSON completo.
    
    Args:
        report: Relatório de validação
        output_dir: Diretório de saída
        
    Returns:
        Caminho do arquivo gerado
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Nome do arquivo com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"validation_report_{timestamp}.json"
    output_path = output_dir / filename
    
    # Converter para dict
    report_dict = report.to_dict()
    
    # Escrever arquivo
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report_dict, f, indent=2, ensure_ascii=False, default=str)
    
    return output_path


def load_json_report(file_path: Union[str, Path]) -> dict:
    """Carrega relatório JSON."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def merge_reports(reports: list) -> dict:
    """Combina múltiplos relatórios em um só."""
    if not reports:
        return {}
    
    merged = {
        "merged_at": datetime.now().isoformat(),
        "report_count": len(reports),
        "reports": reports,
        "summary": {
            "all_passed": all(r.get('passed', False) for r in reports),
            "total_errors": sum(
                sum(len(res.get('errors', [])) for res in r.get('results', []))
                for r in reports
            ),
            "total_warnings": sum(
                sum(len(res.get('warnings', [])) for res in r.get('results', []))
                for r in reports
            )
        }
    }
    
    return merged
