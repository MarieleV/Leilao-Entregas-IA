"""
Leilão de Entregas — Ponto de Entrada Principal
================================================
Executa todas as partes do projeto:
    1. Versão 1 (A*)
    2. Versão 2 (Algoritmo Genético)
    3. Comparação com gráficos
    4. Simulação visual com Pygame

Uso:
    python main.py                    → executa tudo em sequência
    python main.py --versao 1         → somente A*
    python main.py --versao 2         → somente Algoritmo Genético
    python main.py --comparar         → A* + AG + gráficos
    python main.py --simulacao        → abre a simulação Pygame
    python main.py --conexoes arquivo.txt --entregas arquivo.txt
"""

import argparse
import os
import sys


ARQUIVO_CONEXOES_PADRAO = 'conexoes.txt'
ARQUIVO_ENTREGAS_PADRAO = 'entregas.txt'


def verificar_arquivos(conexoes, entregas):
    """Verifica se os arquivos de entrada existem."""
    for caminho in [conexoes, entregas]:
        if not os.path.exists(caminho):
            print(f"\n  ❌ Arquivo não encontrado: {caminho}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Leilão de Entregas — Otimização de Rotas'
    )
    parser.add_argument('--versao',    choices=['1', '2'],
                        help='Executar somente a versão 1 (A*) ou 2 (AG)')
    parser.add_argument('--comparar',  action='store_true',
                        help='Comparar as duas versões e gerar gráficos')
    parser.add_argument('--simulacao', action='store_true',
                        help='Abrir a simulação visual Pygame')
    parser.add_argument('--conexoes',  default=ARQUIVO_CONEXOES_PADRAO,
                        help='Arquivo de conexões (padrão: conexoes.txt)')
    parser.add_argument('--entregas',  default=ARQUIVO_ENTREGAS_PADRAO,
                        help='Arquivo de entregas (padrão: entregas.txt)')
    args = parser.parse_args()

    verificar_arquivos(args.conexoes, args.entregas)

    print("""
╔══════════════════════════════════════════════════════╗
║         🚚  LEILÃO DE ENTREGAS URBANAS  🚚            ║
║   Otimização de Rotas com IA — Busca e Meta-Heurística ║
╚══════════════════════════════════════════════════════╝
""")

    # Execução conforme argumentos
    if args.versao == '1':
        from versao1_a_estrela import executar_versao1
        executar_versao1(args.conexoes, args.entregas)

    elif args.versao == '2':
        from versao2_genetico import executar_versao2
        executar_versao2(args.conexoes, args.entregas)

    elif args.comparar:
        from comparacao import executar_comparacao
        executar_comparacao(args.conexoes, args.entregas)

    elif args.simulacao:
        from simulacao_pygame import executar_simulacao
        executar_simulacao(args.conexoes, args.entregas)

    else:
        # Modo padrão: roda tudo
        print("  Executando todas as etapas...\n")

        from versao1_a_estrela import executar_versao1
        from versao2_genetico  import executar_versao2
        from comparacao        import executar_comparacao

        executar_versao1(args.conexoes, args.entregas)
        executar_versao2(args.conexoes, args.entregas)

        print("\n  Gerando gráficos comparativos...")
        executar_comparacao(args.conexoes, args.entregas)

        print("\n  Para abrir a simulação visual, execute:")
        print("    python main.py --simulacao\n")


if __name__ == '__main__':
    main()
