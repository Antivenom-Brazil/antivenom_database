"""
CLI - Interface de linha de comando.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .runner import run_validation, get_summary_stats
from .manifest import load_manifest


def create_parser() -> argparse.ArgumentParser:
    """Cria parser de argumentos."""
    parser = argparse.ArgumentParser(
        prog='antivenom-validate',
        description='Suite de validação para dataset Antivenom'
    )
    
    parser.add_argument(
        'input_file',
        help='Arquivo de entrada (xlsx, csv, parquet)'
    )
    
    parser.add_argument(
        '-m', '--manifest',
        help='Arquivo de configuração YAML (manifest)',
        default=None
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Diretório de saída para relatórios',
        default='./reports'
    )
    
    parser.add_argument(
        '--skip',
        nargs='+',
        help='Checks a pular (ex: --skip perf reproducibility)',
        default=[]
    )
    
    parser.add_argument(
        '--format',
        choices=['json', 'markdown', 'both'],
        default='both',
        help='Formato de saída (padrão: both)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Modo verboso'
    )
    
    parser.add_argument(
        '--fail-on-warning',
        action='store_true',
        help='Retorna código de erro se houver warnings'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser


def main(args: Optional[List[str]] = None) -> int:
    """Função principal do CLI."""
    parser = create_parser()
    parsed = parser.parse_args(args)
    
    # Verificar arquivo de entrada
    input_path = Path(parsed.input_file)
    if not input_path.exists():
        print(f"Erro: Arquivo não encontrado: {parsed.input_file}", file=sys.stderr)
        return 1
    
    # Criar diretório de saída
    output_dir = Path(parsed.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if parsed.verbose:
        print(f"📂 Arquivo: {input_path}")
        print(f"📁 Saída: {output_dir}")
        if parsed.manifest:
            print(f"📋 Manifest: {parsed.manifest}")
        if parsed.skip:
            print(f"⏭️  Pulando: {', '.join(parsed.skip)}")
    
    # Executar validação
    try:
        if parsed.verbose:
            print("\n🔍 Executando validações...")
        
        report = run_validation(
            file_path=str(input_path),
            manifest_path=parsed.manifest,
            skip_checks=parsed.skip,
            output_dir=str(output_dir)
        )
        
        stats = get_summary_stats(report)
        
        # Gerar relatórios
        from reporting import generate_json_report, generate_markdown_reports
        
        if parsed.format in ['json', 'both']:
            json_path = generate_json_report(report, output_dir)
            if parsed.verbose:
                print(f"📄 JSON: {json_path}")
        
        if parsed.format in ['markdown', 'both']:
            md_paths = generate_markdown_reports(report, output_dir)
            if parsed.verbose:
                print(f"📝 Markdown: {len(md_paths)} arquivos gerados")
        
        # Exibir resumo
        print_summary(stats, parsed.verbose)
        
        # Determinar código de retorno
        if not report.passed:
            return 2
        if parsed.fail_on_warning and stats['total_warnings'] > 0:
            return 1
        return 0
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}", file=sys.stderr)
        if parsed.verbose:
            import traceback
            traceback.print_exc()
        return 1


def print_summary(stats: dict, verbose: bool = False):
    """Imprime resumo da validação."""
    status = "✅ PASSOU" if stats['passed'] else "❌ FALHOU"
    
    print(f"\n{'='*50}")
    print(f"  RESULTADO: {status}")
    print(f"{'='*50}")
    
    print(f"\n📊 Resumo:")
    print(f"   • Checks executados: {stats['total_checks']}")
    print(f"   • Passou: {stats['passed_checks']}")
    print(f"   • Falhou: {stats['failed_checks']}")
    
    print(f"\n📈 Ocorrências:")
    print(f"   • Erros: {stats['total_errors']}")
    print(f"   • Warnings: {stats['total_warnings']}")
    print(f"   • Info: {stats['total_info']}")
    
    if verbose:
        print(f"\n🔴 Por severidade:")
        print(f"   • BLOCKER: {stats['blocker_count']}")
        print(f"   • MAJOR: {stats['major_count']}")
        print(f"   • MINOR: {stats['minor_count']}")
    
    print(f"\n⏱️  Tempo: {stats['execution_time']:.3f}s")
    print()


if __name__ == '__main__':
    sys.exit(main())
