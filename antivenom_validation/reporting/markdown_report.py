"""
Geração de relatórios Markdown (um por check).
"""

from pathlib import Path
from typing import Union, List, Dict, Any
from datetime import datetime

from validate.models import ValidationReport, ValidationResult, ValidationError, Severity


def generate_markdown_reports(
    report: ValidationReport,
    output_dir: Union[str, Path]
) -> List[Path]:
    """
    Gera relatórios Markdown individuais para cada check.
    
    Args:
        report: Relatório de validação
        output_dir: Diretório de saída
        
    Returns:
        Lista de caminhos dos arquivos gerados
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generated_files = []
    
    # Gerar um arquivo para cada check
    for result in report.results:
        filename = f"check_{result.category}_{timestamp}.md"
        output_path = output_dir / filename
        
        content = _generate_check_markdown(result, report)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        generated_files.append(output_path)
    
    # Gerar sumário geral
    summary_path = generate_markdown_summary(report, output_dir, timestamp)
    generated_files.append(summary_path)
    
    return generated_files


def generate_markdown_summary(
    report: ValidationReport,
    output_dir: Union[str, Path],
    timestamp: str = None
) -> Path:
    """Gera relatório Markdown de sumário."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    filename = f"validation_summary_{timestamp}.md"
    output_path = output_dir / filename
    
    content = _generate_summary_markdown(report)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return output_path


def _generate_check_markdown(result: ValidationResult, report: ValidationReport) -> str:
    """Gera conteúdo Markdown para um check específico."""
    status = "✅ PASSOU" if result.passed else "❌ FALHOU"
    
    lines = [
        f"# Check: {result.category}",
        "",
        f"**Status:** {status}",
        f"**Executado em:** {report.timestamp}",
        f"**Arquivo:** `{report.file_path}`",
        "",
        "---",
        ""
    ]
    
    # Erros
    if result.errors:
        lines.append("## ❌ Erros")
        lines.append("")
        for i, error in enumerate(result.errors, 1):
            lines.extend(_format_error(error, i))
        lines.append("")
    
    # Warnings
    if result.warnings:
        lines.append("## ⚠️ Warnings")
        lines.append("")
        for i, warning in enumerate(result.warnings, 1):
            lines.extend(_format_error(warning, i))
        lines.append("")
    
    # Info
    if result.info:
        lines.append("## ℹ️ Informações")
        lines.append("")
        for i, info in enumerate(result.info, 1):
            lines.extend(_format_error(info, i))
        lines.append("")
    
    # Tempo de execução
    execution_time = getattr(result, 'execution_time', None) or getattr(result, 'duration_seconds', None)
    if execution_time:
        lines.extend([
            "---",
            "",
            f"**Tempo de execução:** {execution_time:.4f}s",
            ""
        ])
    
    return "\n".join(lines)


def _generate_summary_markdown(report: ValidationReport) -> str:
    """Gera conteúdo Markdown do sumário."""
    status = "✅ PASSOU" if report.passed else "❌ FALHOU"
    
    # Contar estatísticas
    total_errors = sum(len(r.errors) for r in report.results)
    total_warnings = sum(len(r.warnings) for r in report.results)
    total_info = sum(len(r.info) for r in report.results)
    passed_checks = sum(1 for r in report.results if r.passed)
    failed_checks = len(report.results) - passed_checks
    
    lines = [
        "# 📋 Relatório de Validação - Sumário",
        "",
        f"**Status Geral:** {status}",
        f"**Executado em:** {report.timestamp}",
        f"**Arquivo:** `{report.file_path}`",
        f"**Linhas:** {report.total_rows:,}",
        f"**Colunas:** {report.total_columns}",
        "",
        "---",
        "",
        "## 📊 Resumo",
        "",
        "| Métrica | Valor |",
        "|---------|-------|",
        f"| Checks executados | {len(report.results)} |",
        f"| Passou | {passed_checks} |",
        f"| Falhou | {failed_checks} |",
        f"| Total de erros | {total_errors} |",
        f"| Total de warnings | {total_warnings} |",
        f"| Total de info | {total_info} |",
        f"| Tempo total | {report.execution_time:.3f}s |",
        "",
        "---",
        "",
        "## 📝 Checks Executados",
        "",
        "| Check | Status | Erros | Warnings | Tempo |",
        "|-------|--------|-------|----------|-------|"
    ]
    
    for result in report.results:
        status_emoji = "✅" if result.passed else "❌"
        time_str = f"{getattr(result, 'execution_time', getattr(result, 'duration_seconds', 0)):.3f}s"
        lines.append(
            f"| {result.category} | {status_emoji} | {len(result.errors)} | {len(result.warnings)} | {time_str} |"
        )
    
    lines.extend([
        "",
        "---",
        "",
        "## 🔍 Detalhes por Check",
        ""
    ])
    
    for result in report.results:
        status_emoji = "✅" if result.passed else "❌"
        lines.append(f"### {status_emoji} {result.category}")
        lines.append("")
        
        if not result.passed:
            lines.append("**Principais problemas:**")
            lines.append("")
            for error in result.errors[:3]:  # Top 3 erros
                msg = error.message if hasattr(error, 'message') else error.get('message', '')
                lines.append(f"- {msg}")
            if len(result.errors) > 3:
                lines.append(f"- ... e mais {len(result.errors) - 3} erros")
            lines.append("")
        else:
            lines.append("Nenhum erro encontrado.")
            lines.append("")
    
    lines.extend([
        "---",
        "",
        f"**Relatório gerado em:** {datetime.now()}",
    ])
    
    return "\n".join(lines)


def _format_error(error: Union[ValidationError, dict], index: int) -> List[str]:
    """Formata um erro/warning/info para Markdown."""
    lines = []
    
    # Extrair campos (suporta dict ou ValidationError)
    if isinstance(error, dict):
        severity = error.get('severity', 'UNKNOWN')
        message = error.get('message', '')
        row_indices = error.get('row_indices', [])
        details = error.get('details', {})
    else:
        severity = error.severity.value if hasattr(error.severity, 'value') else str(error.severity)
        message = error.message
        row_indices = error.row_indices or []
        details = error.details or {}
    
    # Badge de severidade
    severity_badges = {
        'BLOCKER': '🔴 **BLOCKER**',
        'MAJOR': '🟠 **MAJOR**',
        'MINOR': '🟡 **MINOR**',
        'INFO': '🔵 **INFO**'
    }
    badge = severity_badges.get(str(severity), f'**{severity}**')
    
    lines.append(f"### {index}. {badge}")
    lines.append("")
    lines.append(f"**Mensagem:** {message}")
    lines.append("")
    
    if row_indices:
        rows_display = row_indices[:10]
        lines.append(f"**Linhas afetadas:** {rows_display}")
        if len(row_indices) > 10:
            lines.append(f"  *(... e mais {len(row_indices) - 10} linhas)*")
        lines.append("")
    
    if details:
        lines.append("<details>")
        lines.append("<summary>📋 Detalhes</summary>")
        lines.append("")
        lines.append("```json")
        import json
        lines.append(json.dumps(details, indent=2, ensure_ascii=False, default=str))
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    
    return lines
