"""
Módulo de modelos e leitura de dados para o Leilão de Entregas.
Contém as estruturas de dados e funções de leitura compartilhadas entre as versões.
"""

import heapq
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------

@dataclass
class Entrega:
    """Representa uma entrega agendada."""
    tempo_inicio: int      # Horário programado de saída (em minutos)
    destino: str           # Nó de destino
    bonus: float           # Valor do bônus oferecido

    def __repr__(self):
        return f"Entrega(t={self.tempo_inicio}, destino={self.destino}, bônus={self.bonus})"


@dataclass(order=True)
class EstadoBusca:
    """Estado usado pelo algoritmo A* na busca determinística."""
    custo_f: float                              # f = g + h (para o heap)
    tempo_atual: float = field(compare=False)  # Tempo decorrido
    bonus_acumulado: float = field(compare=False)  # Bônus coletado até agora
    entregas_feitas: frozenset = field(compare=False)  # Índices das entregas já realizadas
    sequencia: list = field(compare=False)     # Sequência de entregas realizadas


class GrafoConexoes:
    """
    Representa o grafo de conexões entre destinos com os tempos de deslocamento.
    Inclui Dijkstra para calcular menor caminho entre dois nós.
    """

    def __init__(self):
        self.nos: List[str] = []
        self.adjacencia: Dict[str, Dict[str, float]] = {}

    def adicionar_no(self, no: str):
        """Adiciona um nó ao grafo."""
        if no not in self.adjacencia:
            self.nos.append(no)
            self.adjacencia[no] = {}

    def adicionar_aresta(self, origem: str, destino: str, tempo: float):
        """Adiciona uma aresta bidirecional entre dois nós."""
        self.adicionar_no(origem)
        self.adicionar_no(destino)
        if tempo > 0:
            self.adjacencia[origem][destino] = tempo
            self.adjacencia[destino][origem] = tempo

    def menor_tempo(self, origem: str, destino: str) -> Optional[float]:
        """
        Calcula o menor tempo entre dois nós usando o algoritmo de Dijkstra.
        Retorna None se não houver caminho.
        """
        if origem == destino:
            return 0.0

        distancias = {no: float('inf') for no in self.nos}
        distancias[origem] = 0.0
        heap = [(0.0, origem)]

        while heap:
            dist_atual, no_atual = heapq.heappop(heap)
            if dist_atual > distancias[no_atual]:
                continue
            for vizinho, peso in self.adjacencia[no_atual].items():
                nova_dist = dist_atual + peso
                if nova_dist < distancias[vizinho]:
                    distancias[vizinho] = nova_dist
                    heapq.heappush(heap, (nova_dist, vizinho))

        resultado = distancias.get(destino, float('inf'))
        return resultado if resultado < float('inf') else None

    def tempo_ida_volta(self, destino: str, ponto_base: str = 'A') -> Optional[float]:
        """
        Calcula o tempo total de ida e volta do ponto base até o destino.
        """
        ida = self.menor_tempo(ponto_base, destino)
        volta = self.menor_tempo(destino, ponto_base)
        if ida is None or volta is None:
            return None
        return ida + volta

    def __repr__(self):
        linhas = ["GrafoConexoes:"]
        for no, vizinhos in self.adjacencia.items():
            for v, t in vizinhos.items():
                linhas.append(f"  {no} --{t}--> {v}")
        return "\n".join(linhas)


# ---------------------------------------------------------------------------
# Leitura dos arquivos de entrada
# ---------------------------------------------------------------------------

def ler_conexoes(caminho_arquivo: str) -> GrafoConexoes:
    """
    Lê a matriz de adjacência do arquivo e retorna um GrafoConexoes.

    Formato esperado:
        A, B, C, D
        A 0, 5, 0, 2
        B 5, 0, 3, 0
        ...
    """
    grafo = GrafoConexoes()

    with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
        linhas = [l.strip() for l in arquivo if l.strip()]

    # Primeira linha: nomes dos nós
    cabecalho = [c.strip() for c in linhas[0].split(',')]
    for no in cabecalho:
        grafo.adicionar_no(no)

    # Linhas seguintes: matriz de adjacência
    for linha in linhas[1:]:
        partes = linha.split()
        if not partes:
            continue
        no_origem = partes[0]
        # Os valores podem estar separados por ", " ou ","
        valores_str = linha[len(no_origem):].strip()
        valores = [float(v.strip().rstrip(',')) for v in valores_str.split(',')]

        for i, tempo in enumerate(valores):
            no_destino = cabecalho[i]
            if tempo > 0:
                grafo.adicionar_aresta(no_origem, no_destino, tempo)

    return grafo


def ler_entregas(caminho_arquivo: str) -> List[Entrega]:
    """
    Lê a lista de entregas do arquivo.

    Formato esperado (uma por linha):
        tempo_inicio, destino, bonus
    Exemplo:
        0, B, 1
        5, C, 10
    """
    entregas = []

    with open(caminho_arquivo, 'r', encoding='utf-8') as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha:
                continue
            partes = [p.strip() for p in linha.split(',')]
            if len(partes) != 3:
                continue
            tempo = int(partes[0])
            destino = partes[1]
            bonus = float(partes[2])
            entregas.append(Entrega(tempo_inicio=tempo, destino=destino, bonus=bonus))

    # Ordena por tempo de início
    entregas.sort(key=lambda e: e.tempo_inicio)
    return entregas


# ---------------------------------------------------------------------------
# Funções utilitárias compartilhadas
# ---------------------------------------------------------------------------

def verificar_entrega_possivel(
    entrega: Entrega,
    tempo_atual: float,
    grafo: GrafoConexoes,
    ponto_base: str = 'A'
) -> Tuple[bool, float]:
    """
    Verifica se uma entrega ainda pode ser realizada dado o tempo atual.

    Regras:
    - Se tempo_atual <= entrega.tempo_inicio: pode esperar e partir no tempo certo.
    - Se tempo_atual > entrega.tempo_inicio: entrega PERDIDA (inválida).

    Retorna (pode_fazer, tempo_retorno_base).
    """
    if tempo_atual > entrega.tempo_inicio:
        return False, 0.0

    # Pode esperar até o horário programado
    tempo_partida = max(tempo_atual, float(entrega.tempo_inicio))
    tempo_ida = grafo.menor_tempo(ponto_base, entrega.destino)

    if tempo_ida is None:
        return False, 0.0

    tempo_volta = grafo.menor_tempo(entrega.destino, ponto_base)
    if tempo_volta is None:
        return False, 0.0

    tempo_retorno = tempo_partida + tempo_ida + tempo_volta
    return True, tempo_retorno


def exibir_resultado(sequencia: List[Entrega], lucro: float, algoritmo: str):
    """Exibe o resultado formatado no terminal."""
    print(f"\n{'='*50}")
    print(f"  RESULTADO — {algoritmo}")
    print(f"{'='*50}")
    if not sequencia:
        print("  Nenhuma entrega selecionada.")
    else:
        print("  Sequência de entregas selecionadas:")
        for e in sequencia:
            print(f"    → ({e.tempo_inicio}, {e.destino}, {e.bonus})")
    print(f"\n  Lucro total (bônus): {lucro}")
    print(f"{'='*50}\n")
