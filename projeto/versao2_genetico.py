"""
Versão 2 — Leilão de Entregas com Busca Meta-Heurística (Algoritmo Genético)
=============================================================================
Estratégia: Algoritmo Genético (AG) que evolui populações de sequências de
entregas para maximizar o bônus total.

Representação do cromossomo:
    Uma permutação dos índices das entregas → define a ordem de tentativa.
    O decodificador simula a execução na ordem dada e descarta entregas
    inviáveis (cujo horário já passou quando o entregador retorna à base).

Operadores genéticos:
    - Seleção por torneio
    - Cruzamento por Order Crossover (OX)
    - Mutação por troca de posições (swap mutation)
    - Elitismo: os melhores indivíduos passam direto para a próxima geração
"""

import random
import time
from typing import List, Tuple

from modelos import (
    GrafoConexoes,
    Entrega,
    ler_conexoes,
    ler_entregas,
    verificar_entrega_possivel,
    exibir_resultado,
)


# ---------------------------------------------------------------------------
# Decodificador de cromossomo → solução viável
# ---------------------------------------------------------------------------

def decodificar_cromossomo(
    cromossomo: List[int],
    entregas: List[Entrega],
    grafo: GrafoConexoes,
    ponto_base: str = 'A',
) -> Tuple[List[Entrega], float]:
    """
    Simula a execução das entregas na ordem definida pelo cromossomo.
    Descarta automaticamente entregas inviáveis (tempo já passou).

    Retorna (sequência de entregas realizadas, bônus total).
    """
    tempo_atual = 0.0
    bonus_total = 0.0
    sequencia = []

    for indice in cromossomo:
        entrega = entregas[indice]
        pode, tempo_retorno = verificar_entrega_possivel(
            entrega, tempo_atual, grafo, ponto_base
        )
        if pode:
            sequencia.append(entrega)
            bonus_total += entrega.bonus
            tempo_atual = tempo_retorno

    return sequencia, bonus_total


def aptidao(
    cromossomo: List[int],
    entregas: List[Entrega],
    grafo: GrafoConexoes,
    ponto_base: str = 'A',
) -> float:
    """Função de aptidão: retorna o bônus total do cromossomo."""
    _, bonus = decodificar_cromossomo(cromossomo, entregas, grafo, ponto_base)
    return bonus


# ---------------------------------------------------------------------------
# Operadores genéticos
# ---------------------------------------------------------------------------

def criar_populacao_inicial(tamanho: int, num_entregas: int) -> List[List[int]]:
    """Cria uma população inicial com permutações aleatórias."""
    base = list(range(num_entregas))
    populacao = []
    for _ in range(tamanho):
        individuo = base.copy()
        random.shuffle(individuo)
        populacao.append(individuo)
    return populacao


def selecao_torneio(
    populacao: List[List[int]],
    aptidoes: List[float],
    tamanho_torneio: int = 3,
) -> List[int]:
    """Seleciona um indivíduo por torneio."""
    competidores = random.sample(range(len(populacao)), tamanho_torneio)
    vencedor = max(competidores, key=lambda i: aptidoes[i])
    return populacao[vencedor].copy()


def cruzamento_ox(pai1: List[int], pai2: List[int]) -> Tuple[List[int], List[int]]:
    """
    Order Crossover (OX): preserva segmentos de cada pai e preenche
    os genes restantes na ordem do outro pai.
    """
    n = len(pai1)
    p1, p2 = sorted(random.sample(range(n), 2))

    def ox(p_a, p_b):
        filho = [None] * n
        filho[p1:p2+1] = p_a[p1:p2+1]
        segmento = set(filho[p1:p2+1])
        posicao = (p2 + 1) % n
        for gene in p_b[p2+1:] + p_b[:p2+1]:
            if gene not in segmento:
                filho[posicao] = gene
                segmento.add(gene)
                posicao = (posicao + 1) % n
        return filho

    return ox(pai1, pai2), ox(pai2, pai1)


def mutacao_swap(cromossomo: List[int], taxa: float = 0.1) -> List[int]:
    """Mutação por troca de dois genes aleatórios."""
    mutante = cromossomo.copy()
    if random.random() < taxa:
        i, j = random.sample(range(len(mutante)), 2)
        mutante[i], mutante[j] = mutante[j], mutante[i]
    return mutante


# ---------------------------------------------------------------------------
# Algoritmo Genético principal
# ---------------------------------------------------------------------------

def algoritmo_genetico(
    grafo: GrafoConexoes,
    entregas: List[Entrega],
    tamanho_populacao: int = 100,
    num_geracoes: int = 300,
    taxa_cruzamento: float = 0.85,
    taxa_mutacao: float = 0.15,
    tamanho_elite: int = 5,
    ponto_base: str = 'A',
    semente: int = 42,
) -> Tuple[List[Entrega], float, List[float]]:
    """
    Executa o Algoritmo Genético para o Leilão de Entregas.

    Retorna:
        - Melhor sequência de entregas encontrada
        - Melhor bônus total
        - Histórico do melhor bônus por geração (para gráfico de convergência)
    """
    random.seed(semente)
    n = len(entregas)

    if n == 0:
        return [], 0.0, []

    # Inicialização
    populacao = criar_populacao_inicial(tamanho_populacao, n)

    # Adiciona soluções gulosas à população inicial para diversidade direcionada
    # (ordem crescente de tempo de início, e ordem decrescente de bônus)
    populacao[0] = sorted(range(n), key=lambda i: entregas[i].tempo_inicio)
    populacao[1] = sorted(range(n), key=lambda i: -entregas[i].bonus)

    historico_melhor = []
    melhor_global_bonus = 0.0
    melhor_global_seq: List[Entrega] = []

    for geracao in range(num_geracoes):
        # Avalia aptidão
        aptidoes = [aptidao(ind, entregas, grafo, ponto_base) for ind in populacao]

        # Atualiza melhor global
        melhor_idx = max(range(len(populacao)), key=lambda i: aptidoes[i])
        if aptidoes[melhor_idx] > melhor_global_bonus:
            melhor_global_bonus = aptidoes[melhor_idx]
            seq, _ = decodificar_cromossomo(populacao[melhor_idx], entregas, grafo, ponto_base)
            melhor_global_seq = seq

        historico_melhor.append(melhor_global_bonus)

        # Elitismo: preserva os melhores
        indices_ordenados = sorted(range(len(populacao)), key=lambda i: aptidoes[i], reverse=True)
        elite = [populacao[i].copy() for i in indices_ordenados[:tamanho_elite]]

        # Nova geração
        nova_populacao = elite.copy()
        while len(nova_populacao) < tamanho_populacao:
            pai1 = selecao_torneio(populacao, aptidoes)
            pai2 = selecao_torneio(populacao, aptidoes)

            if random.random() < taxa_cruzamento:
                filho1, filho2 = cruzamento_ox(pai1, pai2)
            else:
                filho1, filho2 = pai1.copy(), pai2.copy()

            filho1 = mutacao_swap(filho1, taxa_mutacao)
            filho2 = mutacao_swap(filho2, taxa_mutacao)

            nova_populacao.append(filho1)
            if len(nova_populacao) < tamanho_populacao:
                nova_populacao.append(filho2)

        populacao = nova_populacao

    return melhor_global_seq, melhor_global_bonus, historico_melhor


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def executar_versao2(
    caminho_conexoes: str,
    caminho_entregas: str,
    verboso: bool = True,
) -> Tuple[List[Entrega], float, float, List[float]]:
    """
    Executa a Versão 2 (AG) e retorna (sequência, lucro, tempo_ms, histórico).
    """
    grafo = ler_conexoes(caminho_conexoes)
    entregas = ler_entregas(caminho_entregas)

    inicio = time.perf_counter()
    sequencia, lucro, historico = algoritmo_genetico(grafo, entregas)
    fim = time.perf_counter()

    tempo_ms = (fim - inicio) * 1000

    if verboso:
        exibir_resultado(sequencia, lucro, "Versão 2 — Algoritmo Genético")
        print(f"  Tempo de execução: {tempo_ms:.4f} ms\n")

    return sequencia, lucro, tempo_ms, historico


# ---------------------------------------------------------------------------
# Execução direta
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    executar_versao2('conexoes.txt', 'entregas.txt')
