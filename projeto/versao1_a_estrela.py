"""
Versão 1 — Leilão de Entregas com Busca Determinística (A*)
============================================================
Estratégia: minimizar a "perda de bônus", ou seja, maximizar o bônus coletado
modelando o problema como minimização do custo negativo de bônus perdido.

O estado do A* é:
    (tempo_atual, bonus_acumulado, conjunto_entregas_feitas, sequência)

A heurística h(estado) estima o bônus máximo ainda alcançável a partir
do estado atual, usando uma estimativa otimista (admissível): soma dos
bônus de todas as entregas ainda não feitas e que ainda podem ser
iniciadas no futuro (tempo_atual <= tempo_inicio da entrega).
"""

import heapq
import time
from typing import List, Tuple

from modelos import (
    GrafoConexoes,
    Entrega,
    EstadoBusca,
    ler_conexoes,
    ler_entregas,
    verificar_entrega_possivel,
    exibir_resultado,
)


# ---------------------------------------------------------------------------
# Heurística admissível para o A*
# ---------------------------------------------------------------------------

def heuristica(
    tempo_atual: float,
    entregas_feitas: frozenset,
    todas_entregas: List[Entrega],
    grafo: GrafoConexoes,
    ponto_base: str = 'A',
) -> float:
    """
    Estimativa otimista do bônus ainda alcançável (heurística admissível).

    Para cada entrega ainda não realizada, verifica se ela PODERIA ser
    alcançada a partir do tempo atual (sem considerar conflitos entre elas).
    Isso garante que h nunca superestima o bônus real → A* é ótimo.
    """
    bonus_potencial = 0.0
    for i, entrega in enumerate(todas_entregas):
        if i in entregas_feitas:
            continue
        # Estimativa otimista: ignora conflitos entre entregas pendentes
        pode, _ = verificar_entrega_possivel(entrega, tempo_atual, grafo, ponto_base)
        if pode:
            bonus_potencial += entrega.bonus
    return bonus_potencial


# ---------------------------------------------------------------------------
# Algoritmo A*
# ---------------------------------------------------------------------------

def busca_a_estrela(
    grafo: GrafoConexoes,
    entregas: List[Entrega],
    ponto_base: str = 'A',
) -> Tuple[List[Entrega], float]:
    """
    Resolve o Leilão de Entregas com o algoritmo A*.

    Como o A* minimiza custos, define-se:
        g(estado) = bônus_maximo_possivel - bônus_acumulado  (perda de bônus)
        h(estado) = estimativa otimista do bônus ainda alcançável (negativa da perda futura)

    Na prática, minimizamos: -bônus_acumulado - heurística
    que equivale a maximizar o bônus total esperado.

    Retorna a melhor sequência de entregas e o lucro total.
    """
    bonus_total_possivel = sum(e.bonus for e in entregas)

    # Estado inicial: tempo=0, bônus=0, nenhuma entrega feita
    estado_inicial = EstadoBusca(
        custo_f=0.0,
        tempo_atual=0.0,
        bonus_acumulado=0.0,
        entregas_feitas=frozenset(),
        sequencia=[],
    )

    # heap: (custo_f, id_unico, estado)
    # custo_f = -(bonus_acumulado + heuristica)  → minimizar = maximizar bônus
    h_inicial = heuristica(0.0, frozenset(), entregas, grafo, ponto_base)
    heap = [(-h_inicial, 0, estado_inicial)]
    contador = 1  # desempate no heap

    # Tabela de visitados: (entregas_feitas, tempo_discretizado) → melhor bônus visto
    visitados = {}

    melhor_bonus = 0.0
    melhor_sequencia: List[Entrega] = []

    while heap:
        custo_f_neg, _, estado = heapq.heappop(heap)

        # Chave de estado para evitar revisitar
        chave = (estado.entregas_feitas, round(estado.tempo_atual, 1))
        if chave in visitados and visitados[chave] >= estado.bonus_acumulado:
            continue
        visitados[chave] = estado.bonus_acumulado

        # Atualiza melhor solução encontrada
        if estado.bonus_acumulado > melhor_bonus:
            melhor_bonus = estado.bonus_acumulado
            melhor_sequencia = list(estado.sequencia)

        # Expande: tenta adicionar cada entrega ainda não feita
        expandiu = False
        for i, entrega in enumerate(entregas):
            if i in estado.entregas_feitas:
                continue

            pode, tempo_retorno = verificar_entrega_possivel(
                entrega, estado.tempo_atual, grafo, ponto_base
            )
            if not pode:
                continue

            expandiu = True
            novo_bonus = estado.bonus_acumulado + entrega.bonus
            novas_feitas = estado.entregas_feitas | {i}
            nova_sequencia = estado.sequencia + [entrega]

            h = heuristica(tempo_retorno, novas_feitas, entregas, grafo, ponto_base)
            novo_custo_f = -(novo_bonus + h)

            novo_estado = EstadoBusca(
                custo_f=novo_custo_f,
                tempo_atual=tempo_retorno,
                bonus_acumulado=novo_bonus,
                entregas_feitas=novas_feitas,
                sequencia=nova_sequencia,
            )
            heapq.heappush(heap, (novo_custo_f, contador, novo_estado))
            contador += 1

    return melhor_sequencia, melhor_bonus


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def executar_versao1(
    caminho_conexoes: str,
    caminho_entregas: str,
    verboso: bool = True,
) -> Tuple[List[Entrega], float, float]:
    """
    Executa a Versão 1 (A*) e retorna (sequência, lucro, tempo_execucao_ms).
    """
    grafo = ler_conexoes(caminho_conexoes)
    entregas = ler_entregas(caminho_entregas)

    inicio = time.perf_counter()
    sequencia, lucro = busca_a_estrela(grafo, entregas)
    fim = time.perf_counter()

    tempo_ms = (fim - inicio) * 1000

    if verboso:
        exibir_resultado(sequencia, lucro, "Versão 1 — Busca A*")
        print(f"  Tempo de execução: {tempo_ms:.4f} ms\n")

    return sequencia, lucro, tempo_ms


# ---------------------------------------------------------------------------
# Execução direta
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    executar_versao1('conexoes.txt', 'entregas.txt')
