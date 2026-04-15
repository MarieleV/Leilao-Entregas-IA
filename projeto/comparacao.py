"""
Comparação de Desempenho — Versão 1 (A*) vs Versão 2 (Algoritmo Genético)
==========================================================================
Gera gráficos comparativos de:
    1. Lucro (bônus) obtido por cada algoritmo
    2. Tempo de execução de cada algoritmo
    3. Curva de convergência do Algoritmo Genético por geração
    4. Análise de escalabilidade (múltiplos tamanhos de instância)
"""

import time
import random
import matplotlib
matplotlib.use('Agg')  # Renderização sem display
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from modelos import GrafoConexoes, Entrega, ler_conexoes, ler_entregas
from versao1_a_estrela import busca_a_estrela
from versao2_genetico import algoritmo_genetico


# ---------------------------------------------------------------------------
# Paleta de cores e estilo
# ---------------------------------------------------------------------------

COR_A_ESTRELA  = '#2196F3'   # Azul
COR_GENETICO   = '#FF5722'   # Laranja-vermelho
COR_FUNDO      = '#0D1117'   # Fundo escuro
COR_TEXTO      = '#E6EDF3'   # Texto claro
COR_GRADE      = '#21262D'   # Grade sutil
COR_DESTAQUE   = '#F0B429'   # Amarelo destaque

plt.rcParams.update({
    'figure.facecolor': COR_FUNDO,
    'axes.facecolor':   COR_FUNDO,
    'axes.edgecolor':   COR_GRADE,
    'axes.labelcolor':  COR_TEXTO,
    'xtick.color':      COR_TEXTO,
    'ytick.color':      COR_TEXTO,
    'text.color':       COR_TEXTO,
    'grid.color':       COR_GRADE,
    'grid.alpha':       0.5,
    'font.family':      'monospace',
    'axes.titlesize':   13,
    'axes.labelsize':   11,
})


# ---------------------------------------------------------------------------
# Gerador de instâncias sintéticas para análise de escalabilidade
# ---------------------------------------------------------------------------

def gerar_instancia(num_nos: int, num_entregas: int, semente: int = 0):
    """
    Gera uma instância aleatória com num_nos nós e num_entregas entregas.
    """
    random.seed(semente)
    nos = [chr(ord('A') + i) for i in range(min(num_nos, 26))]

    grafo = GrafoConexoes()
    for no in nos:
        grafo.adicionar_no(no)

    # Garante que o grafo seja conexo: árvore geradora + arestas extras
    for i in range(1, len(nos)):
        j = random.randint(0, i - 1)
        tempo = random.randint(1, 15)
        grafo.adicionar_aresta(nos[i], nos[j], tempo)

    # Arestas extras
    for _ in range(num_nos):
        u, v = random.sample(nos, 2)
        grafo.adicionar_aresta(u, v, random.randint(1, 15))

    # Entregas
    destinos_possiveis = nos[1:]  # Exclui 'A'
    entregas = []
    tempo_base = 0
    for _ in range(num_entregas):
        destino = random.choice(destinos_possiveis)
        bonus   = round(random.uniform(1, 20), 1)
        entregas.append(Entrega(tempo_inicio=tempo_base, destino=destino, bonus=bonus))
        tempo_base += random.randint(3, 12)

    return grafo, sorted(entregas, key=lambda e: e.tempo_inicio)


# ---------------------------------------------------------------------------
# Gráfico 1 — Comparação direta no exemplo base
# ---------------------------------------------------------------------------

def grafico_comparacao_basico(
    seq_a, lucro_a, tempo_a,
    seq_b, lucro_b, tempo_b,
    historico_ag,
):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle('Leilão de Entregas — Comparação A* vs Algoritmo Genético',
                 color=COR_TEXTO, fontsize=15, fontweight='bold', y=1.02)

    # --- Gráfico 1a: Bônus obtido ---
    ax = axes[0]
    algoritmos = ['A*\n(Determinístico)', 'Alg. Genético\n(Meta-Heurístico)']
    lucros = [lucro_a, lucro_b]
    cores = [COR_A_ESTRELA, COR_GENETICO]
    barras = ax.bar(algoritmos, lucros, color=cores, width=0.45,
                    edgecolor='white', linewidth=0.8)
    ax.set_title('Lucro Total (Bônus)')
    ax.set_ylabel('Bônus (R$)')
    ax.set_ylim(0, max(lucros) * 1.35)
    ax.grid(axis='y', linestyle='--')
    for barra, val in zip(barras, lucros):
        ax.text(barra.get_x() + barra.get_width() / 2,
                barra.get_height() + 0.3,
                f'R$ {val:.1f}',
                ha='center', va='bottom', fontweight='bold',
                color=COR_DESTAQUE, fontsize=13)

    # --- Gráfico 1b: Tempo de execução ---
    ax = axes[1]
    tempos = [tempo_a, tempo_b]
    barras = ax.bar(algoritmos, tempos, color=cores, width=0.45,
                    edgecolor='white', linewidth=0.8)
    ax.set_title('Tempo de Execução')
    ax.set_ylabel('Tempo (ms)')
    ax.set_ylim(0, max(tempos) * 1.35)
    ax.grid(axis='y', linestyle='--')
    for barra, val in zip(barras, tempos):
        ax.text(barra.get_x() + barra.get_width() / 2,
                barra.get_height() + max(tempos) * 0.01,
                f'{val:.2f} ms',
                ha='center', va='bottom', fontweight='bold',
                color=COR_DESTAQUE, fontsize=11)

    # --- Gráfico 1c: Convergência do AG ---
    ax = axes[2]
    geracoes = list(range(1, len(historico_ag) + 1))
    ax.plot(geracoes, historico_ag, color=COR_GENETICO, linewidth=2, label='AG')
    ax.axhline(y=lucro_a, color=COR_A_ESTRELA, linestyle='--',
               linewidth=1.5, label=f'A* (ótimo = {lucro_a})')
    ax.fill_between(geracoes, historico_ag, alpha=0.15, color=COR_GENETICO)
    ax.set_title('Convergência — Algoritmo Genético')
    ax.set_xlabel('Geração')
    ax.set_ylabel('Melhor Bônus')
    ax.legend(loc='lower right', framealpha=0.3)
    ax.grid(linestyle='--')

    plt.tight_layout()
    caminho = 'grafico_comparacao.png'
    plt.savefig(caminho, dpi=150, bbox_inches='tight',
                facecolor=COR_FUNDO)
    plt.close()
    print(f"  → Salvo: {caminho}")
    return caminho


# ---------------------------------------------------------------------------
# Gráfico 2 — Análise de escalabilidade
# ---------------------------------------------------------------------------

def grafico_escalabilidade():
    """
    Compara tempo de execução e qualidade da solução para instâncias
    de tamanhos crescentes de entregas.
    """
    tamanhos = [3, 5, 8, 10, 12, 15]
    tempos_a   = []
    tempos_b   = []
    lucros_a   = []
    lucros_b   = []

    print("\n  Análise de escalabilidade em andamento...")
    for n in tamanhos:
        grafo, entregas = gerar_instancia(num_nos=6, num_entregas=n, semente=n*7)

        t0 = time.perf_counter()
        _, la = busca_a_estrela(grafo, entregas)
        t1 = time.perf_counter()
        tempos_a.append((t1 - t0) * 1000)
        lucros_a.append(la)

        t0 = time.perf_counter()
        _, lb, _ = algoritmo_genetico(grafo, entregas,
                                       tamanho_populacao=60,
                                       num_geracoes=150,
                                       semente=42)
        t1 = time.perf_counter()
        tempos_b.append((t1 - t0) * 1000)
        lucros_b.append(lb)
        print(f"    n={n}: A*={la:.1f} ({tempos_a[-1]:.1f}ms)  AG={lb:.1f} ({tempos_b[-1]:.1f}ms)")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Escalabilidade — Nº de Entregas',
                 color=COR_TEXTO, fontsize=14, fontweight='bold')

    ax = axes[0]
    ax.plot(tamanhos, tempos_a, 'o-', color=COR_A_ESTRELA,
            linewidth=2, markersize=7, label='A*')
    ax.plot(tamanhos, tempos_b, 's-', color=COR_GENETICO,
            linewidth=2, markersize=7, label='Alg. Genético')
    ax.set_title('Tempo de Execução vs Nº de Entregas')
    ax.set_xlabel('Nº de Entregas')
    ax.set_ylabel('Tempo (ms)')
    ax.legend(framealpha=0.3)
    ax.grid(linestyle='--')

    ax = axes[1]
    ax.plot(tamanhos, lucros_a, 'o-', color=COR_A_ESTRELA,
            linewidth=2, markersize=7, label='A*')
    ax.plot(tamanhos, lucros_b, 's-', color=COR_GENETICO,
            linewidth=2, markersize=7, label='Alg. Genético')
    ax.set_title('Bônus Obtido vs Nº de Entregas')
    ax.set_xlabel('Nº de Entregas')
    ax.set_ylabel('Bônus Total')
    ax.legend(framealpha=0.3)
    ax.grid(linestyle='--')

    plt.tight_layout()
    caminho = 'grafico_escalabilidade.png'
    plt.savefig(caminho, dpi=150, bbox_inches='tight',
                facecolor=COR_FUNDO)
    plt.close()
    print(f"  → Salvo: {caminho}")
    return caminho


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def executar_comparacao(
    caminho_conexoes: str = 'conexoes.txt',
    caminho_entregas: str = 'entregas.txt',
):
    from versao1_a_estrela import executar_versao1
    from versao2_genetico import executar_versao2

    print("\n" + "="*55)
    print("  COMPARAÇÃO DE DESEMPENHO")
    print("="*55)

    seq_a, lucro_a, tempo_a = executar_versao1(
        caminho_conexoes, caminho_entregas, verboso=True
    )
    seq_b, lucro_b, tempo_b, historico = executar_versao2(
        caminho_conexoes, caminho_entregas, verboso=True
    )

    print("\n  Gerando gráficos comparativos...")
    arq1 = grafico_comparacao_basico(
        seq_a, lucro_a, tempo_a,
        seq_b, lucro_b, tempo_b,
        historico,
    )
    arq2 = grafico_escalabilidade()

    print(f"\n  Gráficos salvos: {arq1}, {arq2}")
    return arq1, arq2


if __name__ == '__main__':
    executar_comparacao()
