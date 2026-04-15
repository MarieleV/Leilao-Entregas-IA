"""
Simulação Visual Interativa — Leilão de Entregas (Pygame)
==========================================================
Interface gráfica interativa que permite:
    • Visualizar o grafo de conexões com nós e arestas
    • Ver as entregas disponíveis com seus horários e bônus
    • Escolher entre A* e Algoritmo Genético
    • Animar o entregador percorrendo o trajeto ótimo
    • Modificar parâmetros (arquivo de entrada) via teclado
    • Pausar/retomar a simulação

Controles:
    [ESPAÇO]  — Iniciar/Pausar animação
    [1]       — Rodar com A* (Versão 1)
    [2]       — Rodar com Algoritmo Genético (Versão 2)
    [R]       — Reiniciar simulação
    [+] / [-] — Ajustar velocidade de animação
    [ESC]     — Sair
"""

import sys
import math
import time
import pygame

from modelos import GrafoConexoes, Entrega, ler_conexoes, ler_entregas
from versao1_a_estrela import busca_a_estrela
from versao2_genetico import algoritmo_genetico


# ---------------------------------------------------------------------------
# Constantes visuais
# ---------------------------------------------------------------------------

LARGURA  = 1200
ALTURA   = 750
FPS      = 60

# Paleta de cores (tema escuro profissional)
FUNDO         = (13,  17,  23)
FUNDO_PAINEL  = (22,  27,  34)
BORDA_PAINEL  = (48,  54,  61)
TEXTO         = (230, 237, 243)
TEXTO_DIM     = (110, 118, 129)
AZUL          = (33,  150, 243)
AZUL_CLARO    = (100, 181, 246)
LARANJA       = (255,  87,  34)
VERDE         = ( 76, 175,  80)
AMARELO       = (240, 180,  41)
VERMELHO      = (244,  67,  54)
CINZA         = ( 97, 105, 114)
BRANCO        = (255, 255, 255)

# Layout
PAINEL_ESQUERDA_L = 280   # Largura do painel esquerdo
PAINEL_DIREITA_L  = 300   # Largura do painel direito
AREA_GRAFO_X      = PAINEL_ESQUERDA_L
AREA_GRAFO_L      = LARGURA - PAINEL_ESQUERDA_L - PAINEL_DIREITA_L
AREA_GRAFO_Y      = 0
AREA_GRAFO_H      = ALTURA - 120

RAIO_NO           = 28
VELOCIDADE_BASE   = 2.0   # pixels por frame no trajeto animado


# ---------------------------------------------------------------------------
# Classe principal da simulação
# ---------------------------------------------------------------------------

class SimulacaoLeilao:

    def __init__(self, caminho_conexoes: str, caminho_entregas: str):
        pygame.init()
        pygame.display.set_caption("🚚 Leilão de Entregas — Simulação Visual")
        self.tela = pygame.display.set_mode((LARGURA, ALTURA))
        self.relogio = pygame.time.Clock()

        # Fontes
        self.fonte_titulo  = pygame.font.SysFont('monospace', 20, bold=True)
        self.fonte_normal  = pygame.font.SysFont('monospace', 14)
        self.fonte_pequena = pygame.font.SysFont('monospace', 12)
        self.fonte_no      = pygame.font.SysFont('monospace', 18, bold=True)
        self.fonte_grande  = pygame.font.SysFont('monospace', 28, bold=True)

        # Dados
        self.caminho_conexoes = caminho_conexoes
        self.caminho_entregas = caminho_entregas
        self.grafo    = ler_conexoes(caminho_conexoes)
        self.entregas = ler_entregas(caminho_entregas)

        # Estado da simulação
        self.algoritmo_ativo = None   # '1' ou '2'
        self.sequencia       = []
        self.lucro           = 0.0
        self.tempo_exec_ms   = 0.0
        self.historico_ag    = []

        # Animação
        self.animando        = False
        self.passo_animacao  = 0      # índice da entrega atual sendo animada
        self.progresso       = 0.0    # 0.0 a 1.0 no segmento atual
        self.fase_animacao   = 'ida'  # 'ida' ou 'volta'
        self.velocidade      = 1.5
        self.pos_entregador  = None   # (x, y) pixel atual
        self.entrega_atual_idx = 0
        self.tempo_simulado  = 0.0   # relógio interno
        self.log_eventos     = []     # mensagens de log
        self.animacao_concluida = False

        # Posições dos nós no canvas
        self.posicoes_nos = self._calcular_posicoes_nos()

        # Trajeto a animar (lista de segmentos: (no_origem, no_destino, fase))
        self.trajeto_segmentos = []
        self.seg_atual = 0

        self.executar()

    # -----------------------------------------------------------------------
    # Layout dos nós
    # -----------------------------------------------------------------------

    def _calcular_posicoes_nos(self):
        """Distribui os nós em círculo na área de grafo."""
        nos = self.grafo.nos
        n   = len(nos)
        cx  = AREA_GRAFO_X + AREA_GRAFO_L // 2
        cy  = AREA_GRAFO_H // 2
        raio_layout = min(AREA_GRAFO_L, AREA_GRAFO_H) // 2 - 70

        posicoes = {}
        for i, no in enumerate(nos):
            angulo = math.radians(-90 + 360 * i / n)
            x = int(cx + raio_layout * math.cos(angulo))
            y = int(cy + raio_layout * math.sin(angulo))
            posicoes[no] = (x, y)
        return posicoes

    # -----------------------------------------------------------------------
    # Construção do trajeto de animação
    # -----------------------------------------------------------------------

    def _construir_trajeto(self):
        """
        Monta a lista de segmentos de animação a partir da sequência de entregas.
        Cada segmento é: (no_A, no_B, entrega_associada_ou_None)
        Usamos o caminho mais curto calculado por Dijkstra.
        """
        segmentos = []
        for entrega in self.sequencia:
            # Caminho A → destino
            caminho_ida  = self._caminho_dijkstra('A', entrega.destino)
            caminho_volta = self._caminho_dijkstra(entrega.destino, 'A')
            for k in range(len(caminho_ida) - 1):
                segmentos.append((caminho_ida[k], caminho_ida[k+1], entrega, 'ida'))
            for k in range(len(caminho_volta) - 1):
                segmentos.append((caminho_volta[k], caminho_volta[k+1], entrega, 'volta'))
        return segmentos

    def _caminho_dijkstra(self, origem, destino):
        """Retorna o caminho (lista de nós) entre origem e destino."""
        import heapq
        dist = {n: float('inf') for n in self.grafo.nos}
        prev = {n: None for n in self.grafo.nos}
        dist[origem] = 0
        heap = [(0, origem)]
        while heap:
            d, u = heapq.heappop(heap)
            if d > dist[u]:
                continue
            for v, w in self.grafo.adjacencia[u].items():
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(heap, (nd, v))
        # Reconstrói caminho
        caminho = []
        atual = destino
        while atual is not None:
            caminho.append(atual)
            atual = prev[atual]
        caminho.reverse()
        return caminho if caminho[0] == origem else [origem, destino]

    # -----------------------------------------------------------------------
    # Execução dos algoritmos
    # -----------------------------------------------------------------------

    def rodar_algoritmo(self, versao: str):
        """Executa o algoritmo escolhido e prepara a animação."""
        self.algoritmo_ativo = versao
        self.animando        = False
        self.animacao_concluida = False
        self.seg_atual       = 0
        self.progresso       = 0.0
        self.log_eventos     = []
        self.historico_ag    = []

        t0 = time.perf_counter()
        if versao == '1':
            self.sequencia, self.lucro = busca_a_estrela(self.grafo, self.entregas)
        else:
            self.sequencia, self.lucro, self.historico_ag = algoritmo_genetico(
                self.grafo, self.entregas
            )
        t1 = time.perf_counter()
        self.tempo_exec_ms = (t1 - t0) * 1000

        self.trajeto_segmentos = self._construir_trajeto()
        if self.trajeto_segmentos:
            o, d, _, _ = self.trajeto_segmentos[0]
            self.pos_entregador = list(self.posicoes_nos[o])

        nome = "A*" if versao == '1' else "Alg. Genético"
        self.log_eventos.append(f"[{nome}] Lucro: R$ {self.lucro:.1f} | {self.tempo_exec_ms:.2f}ms")
        self.log_eventos.append(f"Entregas: {len(self.sequencia)}/{len(self.entregas)}")

    # -----------------------------------------------------------------------
    # Desenho
    # -----------------------------------------------------------------------

    def _desenhar_fundo(self):
        self.tela.fill(FUNDO)
        # Área do grafo — borda sutil
        pygame.draw.rect(self.tela, BORDA_PAINEL,
                         (AREA_GRAFO_X, AREA_GRAFO_Y, AREA_GRAFO_L, AREA_GRAFO_H), 1)

    def _desenhar_arestas(self):
        for no_a, vizinhos in self.grafo.adjacencia.items():
            for no_b, tempo in vizinhos.items():
                if no_a >= no_b:
                    continue
                x1, y1 = self.posicoes_nos[no_a]
                x2, y2 = self.posicoes_nos[no_b]
                pygame.draw.line(self.tela, CINZA, (x1, y1), (x2, y2), 2)
                # Rótulo do tempo no meio da aresta
                mx, my = (x1 + x2) // 2, (y1 + y2) // 2
                rot = self.fonte_pequena.render(f'{int(tempo)}min', True, TEXTO_DIM)
                self.tela.blit(rot, (mx - rot.get_width()//2, my - rot.get_height()//2))

    def _desenhar_arestas_ativas(self):
        """Destaca as arestas que fazem parte da solução encontrada."""
        if not self.sequencia:
            return
        arestas_sol = set()
        for entrega in self.sequencia:
            cam_ida   = self._caminho_dijkstra('A', entrega.destino)
            cam_volta = self._caminho_dijkstra(entrega.destino, 'A')
            for path in [cam_ida, cam_volta]:
                for k in range(len(path) - 1):
                    arestas_sol.add((min(path[k], path[k+1]), max(path[k], path[k+1])))

        for (a, b) in arestas_sol:
            x1, y1 = self.posicoes_nos[a]
            x2, y2 = self.posicoes_nos[b]
            pygame.draw.line(self.tela, AZUL_CLARO, (x1, y1), (x2, y2), 3)

    def _desenhar_nos(self):
        for no, (x, y) in self.posicoes_nos.items():
            # Verifica se é destino de alguma entrega selecionada
            na_solucao = any(e.destino == no for e in self.sequencia)
            cor = AZUL if na_solucao else CINZA
            cor_borda = AZUL_CLARO if na_solucao else BORDA_PAINEL

            pygame.draw.circle(self.tela, FUNDO_PAINEL, (x, y), RAIO_NO)
            pygame.draw.circle(self.tela, cor,          (x, y), RAIO_NO, 3)

            label = self.fonte_no.render(no, True, cor_borda)
            self.tela.blit(label, (x - label.get_width()//2,
                                   y - label.get_height()//2))

            # Exibe bônus abaixo do nó
            for e in self.entregas:
                if e.destino == no:
                    txt_bonus = self.fonte_pequena.render(
                        f'R${e.bonus:.0f}', True, AMARELO
                    )
                    self.tela.blit(txt_bonus, (x - txt_bonus.get_width()//2,
                                               y + RAIO_NO + 4))

    def _desenhar_entregador(self):
        if self.pos_entregador and (self.animando or self.seg_atual > 0):
            px, py = int(self.pos_entregador[0]), int(self.pos_entregador[1])
            # Sombra
            pygame.draw.circle(self.tela, (0, 0, 0, 120), (px + 3, py + 3), 16)
            # Corpo
            pygame.draw.circle(self.tela, LARANJA, (px, py), 16)
            pygame.draw.circle(self.tela, BRANCO,  (px, py), 16, 2)
            # Ícone de caminhão (simplificado)
            cam = self.fonte_pequena.render('🚚', True, BRANCO)
            self.tela.blit(cam, (px - cam.get_width()//2,
                                  py - cam.get_height()//2))

    # -----------------------------------------------------------------------
    # Painéis laterais
    # -----------------------------------------------------------------------

    def _desenhar_painel_esquerdo(self):
        pygame.draw.rect(self.tela, FUNDO_PAINEL, (0, 0, PAINEL_ESQUERDA_L, ALTURA))
        pygame.draw.line(self.tela, BORDA_PAINEL,
                         (PAINEL_ESQUERDA_L, 0), (PAINEL_ESQUERDA_L, ALTURA), 1)

        y = 18
        titulo = self.fonte_titulo.render('ENTREGAS DO DIA', True, AZUL)
        self.tela.blit(titulo, (12, y))
        y += 32
        pygame.draw.line(self.tela, BORDA_PAINEL, (12, y), (PAINEL_ESQUERDA_L - 12, y), 1)
        y += 12

        for i, e in enumerate(self.entregas):
            selecionada = e in self.sequencia
            cor_bg  = (20, 40, 70) if selecionada else FUNDO
            cor_txt = VERDE       if selecionada else TEXTO_DIM
            cor_bor = AZUL        if selecionada else BORDA_PAINEL

            pygame.draw.rect(self.tela, cor_bg,  (10, y, PAINEL_ESQUERDA_L - 20, 58), border_radius=6)
            pygame.draw.rect(self.tela, cor_bor, (10, y, PAINEL_ESQUERDA_L - 20, 58), 1, border_radius=6)

            t1 = self.fonte_normal.render(f'#{i+1}  ⏱ t={e.tempo_inicio}min', True, cor_txt)
            t2 = self.fonte_normal.render(f'   Destino: {e.destino}', True, TEXTO)
            t3 = self.fonte_normal.render(f'   Bônus:  R$ {e.bonus:.1f}', True, AMARELO)
            self.tela.blit(t1, (16, y + 6))
            self.tela.blit(t2, (16, y + 22))
            self.tela.blit(t3, (16, y + 38))

            if selecionada:
                check = self.fonte_normal.render('✓', True, VERDE)
                self.tela.blit(check, (PAINEL_ESQUERDA_L - 28, y + 20))

            y += 68

    def _desenhar_painel_direito(self):
        x0 = AREA_GRAFO_X + AREA_GRAFO_L
        pygame.draw.rect(self.tela, FUNDO_PAINEL, (x0, 0, PAINEL_DIREITA_L, ALTURA))
        pygame.draw.line(self.tela, BORDA_PAINEL, (x0, 0), (x0, ALTURA), 1)

        y = 18
        titulo = self.fonte_titulo.render('CONTROLES', True, LARANJA)
        self.tela.blit(titulo, (x0 + 12, y))
        y += 32
        pygame.draw.line(self.tela, BORDA_PAINEL,
                         (x0 + 12, y), (x0 + PAINEL_DIREITA_L - 12, y), 1)
        y += 14

        controles = [
            ('[1]', 'Rodar A*'),
            ('[2]', 'Rodar Alg. Genético'),
            ('[ESPAÇO]', 'Iniciar/Pausar'),
            ('[R]', 'Reiniciar'),
            ('[+]', 'Aumentar velocidade'),
            ('[-]', 'Diminuir velocidade'),
            ('[ESC]', 'Sair'),
        ]
        for tecla, desc in controles:
            t_tec  = self.fonte_normal.render(tecla, True, AZUL_CLARO)
            t_desc = self.fonte_pequena.render(desc,  True, TEXTO_DIM)
            self.tela.blit(t_tec,  (x0 + 14, y))
            self.tela.blit(t_desc, (x0 + 14, y + 18))
            y += 38

        y += 10
        pygame.draw.line(self.tela, BORDA_PAINEL,
                         (x0 + 12, y), (x0 + PAINEL_DIREITA_L - 12, y), 1)
        y += 14

        # Status algoritmo
        alg_nome = {'1': 'A* (Determinístico)',
                     '2': 'Alg. Genético'}.get(self.algoritmo_ativo, '—')
        t_alg = self.fonte_normal.render('Algoritmo:', True, TEXTO_DIM)
        t_nom = self.fonte_normal.render(alg_nome, True, TEXTO)
        self.tela.blit(t_alg, (x0 + 14, y)); y += 20
        self.tela.blit(t_nom, (x0 + 14, y)); y += 28

        # Lucro
        t_luc_label = self.fonte_normal.render('Lucro Total:', True, TEXTO_DIM)
        t_luc_val   = self.fonte_grande.render(f'R$ {self.lucro:.1f}', True, AMARELO)
        self.tela.blit(t_luc_label, (x0 + 14, y)); y += 20
        self.tela.blit(t_luc_val,   (x0 + 14, y)); y += 44

        # Tempo de execução
        t_te_l = self.fonte_normal.render('Exec. algoritmo:', True, TEXTO_DIM)
        t_te_v = self.fonte_normal.render(f'{self.tempo_exec_ms:.3f} ms', True, VERDE)
        self.tela.blit(t_te_l, (x0 + 14, y)); y += 20
        self.tela.blit(t_te_v, (x0 + 14, y)); y += 32

        # Velocidade
        t_vel_l = self.fonte_normal.render('Vel. animação:', True, TEXTO_DIM)
        t_vel_v = self.fonte_normal.render(f'{self.velocidade:.1f}x', True, TEXTO)
        self.tela.blit(t_vel_l, (x0 + 14, y)); y += 20
        self.tela.blit(t_vel_v, (x0 + 14, y)); y += 32

        # Progresso da animação
        if self.trajeto_segmentos:
            pct = self.seg_atual / len(self.trajeto_segmentos)
            pygame.draw.line(self.tela, BORDA_PAINEL,
                             (x0 + 12, y), (x0 + PAINEL_DIREITA_L - 12, y), 1)
            y += 14
            t_prog = self.fonte_normal.render('Progresso da rota:', True, TEXTO_DIM)
            self.tela.blit(t_prog, (x0 + 14, y)); y += 20
            barra_l = PAINEL_DIREITA_L - 28
            pygame.draw.rect(self.tela, CINZA, (x0 + 14, y, barra_l, 12), border_radius=4)
            pygame.draw.rect(self.tela, AZUL,
                             (x0 + 14, y, int(barra_l * pct), 12), border_radius=4)
            y += 24

        # Log de eventos
        pygame.draw.line(self.tela, BORDA_PAINEL,
                         (x0 + 12, y), (x0 + PAINEL_DIREITA_L - 12, y), 1)
        y += 10
        t_log = self.fonte_normal.render('Log:', True, TEXTO_DIM)
        self.tela.blit(t_log, (x0 + 14, y)); y += 20

        for msg in self.log_eventos[-6:]:
            surf = self.fonte_pequena.render(msg[:36], True, TEXTO_DIM)
            self.tela.blit(surf, (x0 + 14, y))
            y += 18

    def _desenhar_barra_inferior(self):
        y0 = AREA_GRAFO_H
        pygame.draw.rect(self.tela, FUNDO_PAINEL,
                         (AREA_GRAFO_X, y0, AREA_GRAFO_L, ALTURA - y0))
        pygame.draw.line(self.tela, BORDA_PAINEL,
                         (AREA_GRAFO_X, y0), (AREA_GRAFO_X + AREA_GRAFO_L, y0), 1)

        if self.sequencia:
            partes = ['A']
            for e in self.sequencia:
                partes.append(f'→{e.destino}(+R${e.bonus:.0f})')
                partes.append('→A')
            rota_str = ' '.join(partes)
        else:
            rota_str = 'Nenhuma rota calculada. Pressione [1] ou [2].'

        t = self.fonte_normal.render(rota_str[:100], True, TEXTO)
        self.tela.blit(t, (AREA_GRAFO_X + 12, y0 + 14))

        status = 'ANIMANDO...' if self.animando else ('CONCLUÍDO' if self.animacao_concluida else 'PRONTO')
        cor_st = VERDE if self.animacao_concluida else (AMARELO if self.animando else TEXTO_DIM)
        t_st = self.fonte_normal.render(status, True, cor_st)
        self.tela.blit(t_st, (AREA_GRAFO_X + 12, y0 + 36))

    # -----------------------------------------------------------------------
    # Animação do entregador
    # -----------------------------------------------------------------------

    def _atualizar_animacao(self):
        if not self.animando or not self.trajeto_segmentos:
            return
        if self.seg_atual >= len(self.trajeto_segmentos):
            self.animando = False
            self.animacao_concluida = True
            return

        origem_no, destino_no, entrega, fase = self.trajeto_segmentos[self.seg_atual]
        x1, y1 = self.posicoes_nos[origem_no]
        x2, y2 = self.posicoes_nos[destino_no]

        dist = math.hypot(x2 - x1, y2 - y1)
        passo = (self.velocidade * VELOCIDADE_BASE) / max(dist, 1)
        self.progresso += passo

        if self.progresso >= 1.0:
            self.progresso = 0.0
            self.seg_atual += 1
            if self.seg_atual < len(self.trajeto_segmentos):
                no_prox = self.trajeto_segmentos[self.seg_atual][0]
                self.pos_entregador = list(self.posicoes_nos[no_prox])
                # Log de chegada
                _, dest_ant, e_ant, f_ant = self.trajeto_segmentos[self.seg_atual - 1]
                if f_ant == 'ida' and dest_ant == e_ant.destino:
                    self.log_eventos.append(f'✓ Entregue em {dest_ant}! +R${e_ant.bonus:.0f}')
            else:
                self.animando = False
                self.animacao_concluida = True
                self.log_eventos.append('🏁 Rota completa!')
        else:
            px = x1 + (x2 - x1) * self.progresso
            py = y1 + (y2 - y1) * self.progresso
            self.pos_entregador = [px, py]

    # -----------------------------------------------------------------------
    # Loop principal
    # -----------------------------------------------------------------------

    def executar(self):
        rodando = True
        while rodando:
            self.relogio.tick(FPS)

            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    rodando = False

                elif evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE:
                        rodando = False

                    elif evento.key == pygame.K_1:
                        self.rodar_algoritmo('1')

                    elif evento.key == pygame.K_2:
                        self.rodar_algoritmo('2')

                    elif evento.key == pygame.K_SPACE:
                        if self.sequencia and not self.animacao_concluida:
                            self.animando = not self.animando
                        elif self.animacao_concluida:
                            # Reinicia animação
                            self.seg_atual = 0
                            self.progresso = 0.0
                            self.animacao_concluida = False
                            self.animando = True
                            if self.trajeto_segmentos:
                                o = self.trajeto_segmentos[0][0]
                                self.pos_entregador = list(self.posicoes_nos[o])

                    elif evento.key == pygame.K_r:
                        self.sequencia = []
                        self.lucro = 0.0
                        self.animando = False
                        self.animacao_concluida = False
                        self.seg_atual = 0
                        self.progresso = 0.0
                        self.algoritmo_ativo = None
                        self.log_eventos = []
                        self.pos_entregador = None

                    elif evento.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                        self.velocidade = min(self.velocidade + 0.5, 8.0)

                    elif evento.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self.velocidade = max(self.velocidade - 0.5, 0.5)

            # Atualiza animação
            self._atualizar_animacao()

            # Desenha tudo
            self._desenhar_fundo()
            self._desenhar_arestas()
            self._desenhar_arestas_ativas()
            self._desenhar_nos()
            self._desenhar_entregador()
            self._desenhar_painel_esquerdo()
            self._desenhar_painel_direito()
            self._desenhar_barra_inferior()

            # Mensagem inicial se nenhum algoritmo rodou
            if self.algoritmo_ativo is None:
                msg1 = self.fonte_titulo.render(
                    'Pressione [1] para A*  ou  [2] para Algoritmo Genético',
                    True, AZUL_CLARO
                )
                cx = AREA_GRAFO_X + AREA_GRAFO_L // 2
                cy = AREA_GRAFO_H // 2 + 100
                self.tela.blit(msg1, (cx - msg1.get_width()//2, cy))

            pygame.display.flip()

        pygame.quit()
        sys.exit()


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------

def executar_simulacao(
    caminho_conexoes: str = 'conexoes.txt',
    caminho_entregas: str = 'entregas.txt',
):
    SimulacaoLeilao(caminho_conexoes, caminho_entregas)


if __name__ == '__main__':
    executar_simulacao()
