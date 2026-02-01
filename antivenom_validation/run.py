#!/usr/bin/env python
"""
Script de execução rápida da validação.
Uso: python run.py [arquivo_xlsx]
"""

import sys
from pathlib import Path

# Adicionar diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

from validate.runner import run_validation, get_summary_stats
from reporting import generate_json_report, generate_markdown_reports


def main():
    # Arquivo padrão ou especificado
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "../antivenom_limpo4_corrigido.xlsx"
    
    # Verificar existência
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ Arquivo não encontrado: {input_file}")
        return 1
    
    print(f"[*] Arquivo: {input_path.absolute()}")
    print("[*] Executando validacoes...\n")
    
    # Executar validação
    report = run_validation(
        file_path=str(input_path),
        manifest_path="validation.manifest.yaml" if Path("validation.manifest.yaml").exists() else None
    )
    
    # Criar diretório de relatórios
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # Gerar relatórios
    json_path = generate_json_report(report, reports_dir)
    md_paths = generate_markdown_reports(report, reports_dir)
    
    # Mostrar resumo
    stats = get_summary_stats(report)
    
    status = "[PASSOU]" if report.passed else "[FALHOU]"
    print(f"{'='*50}")
    print(f"  RESULTADO: {status}")
    print(f"{'='*50}")
    
    print(f"\n[*] Resumo:")
    print(f"   * Linhas: {report.total_rows:,}")
    print(f"   * Colunas: {report.total_columns}")
    print(f"   * Checks executados: {stats['total_checks']}")
    print(f"   * Passou: {stats['passed_checks']}")
    print(f"   * Falhou: {stats['failed_checks']}")
    
    print(f"\n[*] Ocorrencias:")
    print(f"   * Erros: {stats['total_errors']}")
    print(f"   * Warnings: {stats['total_warnings']}")
    print(f"   * Info: {stats['total_info']}")
    
    print(f"\n[!] Por severidade:")
    print(f"   * BLOCKER: {stats['blocker_count']}")
    print(f"   * MAJOR: {stats['major_count']}")
    print(f"   * MINOR: {stats['minor_count']}")
    
    print(f"\n[*] Tempo: {stats['execution_time']:.3f}s")
    
    print(f"\n[*] Relatorios gerados:")
    print(f"   * JSON: {json_path}")
    print(f"   * Markdown: {len(md_paths)} arquivos em {reports_dir}/")
    
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
