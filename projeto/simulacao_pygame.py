"""
Simulação Visual Interativa — Leilão de Entregas (Pygame)
==========================================================
Interface gráfica interativa que permite:
    • Visualizar o grafo de conexões com nós e arestas
    • Ver as entregas disponíveis com seus horários e bônus
    • Escolher entre A* e Algoritmo Genético
    • Animar o entregador percorrendo o trajeto ótimo
    • Modificar parâmetros interativamente via painel lateral:
        - Adicionar/remover conexões entre nós
        - Adicionar/remover entregas
        - Ajustar bônus e horários
        - Recarregar a partir dos arquivos originais
    • Pausar/retomar a simulação

Controles:
    [ESPAÇO]  — Iniciar/Pausar animação
    [1]       — Rodar com A* (Versão 1)
    [2]       — Rodar com Algoritmo Genético (Versão 2)
    [R]       — Reiniciar simulação
    [P]       — Abrir/fechar painel de parâmetros
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

LARGURA  = 1280
ALTURA   = 800
FPS      = 60

# Paleta de cores (tema claro / clean profissional)
FUNDO          = (248, 250, 252)
FUNDO_PAINEL   = (255, 255, 255)
BORDA_PAINEL   = (226, 232, 240)
TEXTO          = ( 15,  23,  42)
TEXTO_DIM      = (100, 116, 139)
AZUL           = ( 59, 130, 246)
AZUL_CLARO     = (147, 197, 253)
AZUL_FUNDO     = (239, 246, 255)
LARANJA        = (249, 115,  22)
VERDE          = ( 16, 185, 129)
VERDE_FUNDO    = (209, 250, 229)
AMARELO        = (217, 119,   6)
VERMELHO       = (239,  68,  68)
VERMELHO_FUNDO = (254, 226, 226)
CINZA          = (148, 163, 184)
CINZA_CLARO    = (241, 245, 249)
BRANCO         = (255, 255, 255)

# Layout
PAINEL_ESQUERDA_L = 280
PAINEL_DIREITA_L  = 300
AREA_GRAFO_X      = PAINEL_ESQUERDA_L
AREA_GRAFO_L      = LARGURA - PAINEL_ESQUERDA_L - PAINEL_DIREITA_L
AREA_GRAFO_Y      = 0
AREA_GRAFO_H      = ALTURA - 120

RAIO_NO         = 28
VELOCIDADE_BASE = 2.0


# ---------------------------------------------------------------------------
# Componentes de UI reutilizáveis
# ---------------------------------------------------------------------------

class Botao:
    """Botão clicável com efeito de hover."""

    def __init__(self, x, y, largura, altura, texto,
                 cor=None, cor_texto=BRANCO, raio_borda=6, fonte=None):
        self.rect      = pygame.Rect(x, y, largura, altura)
        self.texto     = texto
        self.cor       = cor if cor else AZUL
        self.cor_hover = tuple(max(0, c - 30) for c in self.cor)
        self.cor_texto = cor_texto
        self.raio      = raio_borda
        self.fonte     = fonte
        self.hover     = False

    def desenhar(self, tela):
        cor_atual = self.cor_hover if self.hover else self.cor
        pygame.draw.rect(tela, cor_atual, self.rect, border_radius=self.raio)
        if self.fonte:
            surf = self.fonte.render(self.texto, True, self.cor_texto)
            tela.blit(surf, (
                self.rect.centerx - surf.get_width() // 2,
                self.rect.centery - surf.get_height() // 2,
            ))

    def atualizar_hover(self, pos_mouse):
        self.hover = self.rect.collidepoint(pos_mouse)

    def foi_clicado(self, evento):
        return (evento.type == pygame.MOUSEBUTTONDOWN
                and evento.button == 1
                and self.rect.collidepoint(evento.pos))


class CampoTexto:
    """Campo de entrada de texto simples."""

    def __init__(self, x, y, largura, altura, placeholder='', fonte=None):
        self.rect        = pygame.Rect(x, y, largura, altura)
        self.placeholder = placeholder
        self.fonte       = fonte
        self.texto       = ''
        self.ativo       = False

    def desenhar(self, tela):
        cor_borda = AZUL if self.ativo else BORDA_PAINEL
        pygame.draw.rect(tela, BRANCO,    self.rect, border_radius=4)
        pygame.draw.rect(tela, cor_borda, self.rect, 1, border_radius=4)

        exibir = self.texto if self.texto else self.placeholder
        cor    = TEXTO if self.texto else CINZA
        if self.fonte:
            surf = self.fonte.render(exibir[:20], True, cor)
            tela.blit(surf, (self.rect.x + 6,
                              self.rect.centery - surf.get_height() // 2))

        # Cursor piscante quando ativo
        if self.ativo and int(time.time() * 2) % 2 == 0 and self.texto:
            surf_txt = self.fonte.render(self.texto[:20], True, TEXTO)
            cx = self.rect.x + 6 + surf_txt.get_width() + 1
            pygame.draw.line(tela, TEXTO,
                             (cx, self.rect.y + 4),
                             (cx, self.rect.bottom - 4), 1)

    def processar_evento(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN:
            self.ativo = self.rect.collidepoint(evento.pos)
        if evento.type == pygame.KEYDOWN and self.ativo:
            if evento.key == pygame.K_BACKSPACE:
                self.texto = self.texto[:-1]
            elif evento.key not in (pygame.K_RETURN, pygame.K_ESCAPE,
                                    pygame.K_TAB):
                if len(self.texto) < 30:
                    self.texto += evento.unicode
        return self.ativo


# ---------------------------------------------------------------------------
# Painel de parâmetros interativos
# ---------------------------------------------------------------------------

class PainelParametros:
    """
    Painel flutuante para edição de entregas e conexões em tempo real,
    sem precisar editar arquivos externos.
    """

    LARGURA_PAINEL = 430
    ALTURA_PAINEL  = 570

    def __init__(self, largura_tela, altura_tela,
                 fonte_normal, fonte_pequena, fonte_titulo):
        self.visivel       = False
        self.fonte_normal  = fonte_normal
        self.fonte_pequena = fonte_pequena
        self.fonte_titulo  = fonte_titulo

        px = (largura_tela - self.LARGURA_PAINEL) // 2
        py = (altura_tela  - self.ALTURA_PAINEL)  // 2
        self.rect     = pygame.Rect(px, py, self.LARGURA_PAINEL, self.ALTURA_PAINEL)
        self.aba_ativa = 'entregas'

        self._construir_widgets(px, py)

    def _construir_widgets(self, px, py):
        fn = self.fonte_normal
        fp = self.fonte_pequena

        # Abas
        self.btn_aba_entregas = Botao(px + 10,  py + 42, 195, 32,
                                       'Entregas', fonte=fn)
        self.btn_aba_conexoes = Botao(px + 215, py + 42, 195, 32,
                                       'Conexões', cor=CINZA_CLARO,
                                       cor_texto=TEXTO, fonte=fn)

        # Campos — Entregas
        self.campo_entrega_tempo   = CampoTexto(px + 10,  py + 148,  92, 30,
                                                 'Tempo', fonte=fp)
        self.campo_entrega_destino = CampoTexto(px + 112, py + 148,  92, 30,
                                                 'Destino', fonte=fp)
        self.campo_entrega_bonus   = CampoTexto(px + 214, py + 148,  92, 30,
                                                 'Bônus', fonte=fp)
        self.btn_add_entrega = Botao(px + 316, py + 148, 100, 30,
                                      '+ Adicionar', cor=VERDE, fonte=fp)

        # Campos — Conexões
        self.campo_conn_origem  = CampoTexto(px + 10,  py + 148,  92, 30,
                                              'Origem', fonte=fp)
        self.campo_conn_destino = CampoTexto(px + 112, py + 148,  92, 30,
                                              'Destino', fonte=fp)
        self.campo_conn_tempo   = CampoTexto(px + 214, py + 148,  92, 30,
                                              'Tempo', fonte=fp)
        self.btn_add_conn = Botao(px + 316, py + 148, 100, 30,
                                   '+ Adicionar', cor=VERDE, fonte=fp)

        # Fechar
        self.btn_fechar = Botao(px + self.LARGURA_PAINEL - 36, py + 8,
                                 28, 28, '✕', cor=VERMELHO, fonte=fn)

        # Inferiores
        self.btn_recarregar = Botao(px + 10,
                                     py + self.ALTURA_PAINEL - 46,
                                     200, 32,
                                     '↺ Recarregar Arquivos',
                                     cor=CINZA_CLARO, cor_texto=TEXTO, fonte=fp)
        self.btn_limpar = Botao(px + 220,
                                 py + self.ALTURA_PAINEL - 46,
                                 200, 32,
                                 '🗑 Limpar Tudo',
                                 cor=VERMELHO_FUNDO, cor_texto=VERMELHO, fonte=fp)

        self.mensagem_feedback = ''
        self.cor_feedback      = VERDE
        self.tempo_feedback    = 0.0
        self.scroll_entregas   = 0
        self.scroll_conexoes   = 0

    # -----------------------------------------------------------------------
    # Controle de visibilidade e feedback
    # -----------------------------------------------------------------------

    def alternar_visibilidade(self):
        self.visivel = not self.visivel

    def exibir_feedback(self, msg, cor=VERDE):
        self.mensagem_feedback = msg
        self.cor_feedback      = cor
        self.tempo_feedback    = time.time()

    # -----------------------------------------------------------------------
    # Desenho
    # -----------------------------------------------------------------------

    def desenhar(self, tela, grafo, entregas):
        if not self.visivel:
            return

        # Overlay translúcido
        overlay = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        overlay.fill((15, 23, 42, 140))
        tela.blit(overlay, (0, 0))

        px, py = self.rect.x, self.rect.y
        lp, ap = self.LARGURA_PAINEL, self.ALTURA_PAINEL

        # Sombra e fundo
        pygame.draw.rect(tela, (200, 210, 220),
                         (px + 4, py + 4, lp, ap), border_radius=10)
        pygame.draw.rect(tela, BRANCO, self.rect, border_radius=10)
        pygame.draw.rect(tela, BORDA_PAINEL, self.rect, 1, border_radius=10)

        # Título
        t = self.fonte_titulo.render('⚙  Parâmetros Interativos', True, TEXTO)
        tela.blit(t, (px + 12, py + 10))
        self.btn_fechar.desenhar(tela)

        # Abas
        self._estilizar_aba(self.btn_aba_entregas, self.aba_ativa == 'entregas')
        self._estilizar_aba(self.btn_aba_conexoes, self.aba_ativa == 'conexoes')
        self.btn_aba_entregas.desenhar(tela)
        self.btn_aba_conexoes.desenhar(tela)

        pygame.draw.line(tela, BORDA_PAINEL,
                         (px + 10, py + 84), (px + lp - 10, py + 84), 1)

        if self.aba_ativa == 'entregas':
            self._desenhar_aba_entregas(tela, entregas, px, py, lp)
        else:
            self._desenhar_aba_conexoes(tela, grafo, px, py, lp)

        self.btn_recarregar.desenhar(tela)
        self.btn_limpar.desenhar(tela)

        # Feedback temporário
        if self.mensagem_feedback and time.time() - self.tempo_feedback < 2.5:
            fb = self.fonte_pequena.render(self.mensagem_feedback, True,
                                           self.cor_feedback)
            tela.blit(fb, (px + 10, py + ap - 68))

    def _estilizar_aba(self, btn, ativa):
        if ativa:
            btn.cor       = AZUL
            btn.cor_hover = (30, 100, 210)
            btn.cor_texto = BRANCO
        else:
            btn.cor       = CINZA_CLARO
            btn.cor_hover = BORDA_PAINEL
            btn.cor_texto = TEXTO_DIM

    def _desenhar_aba_entregas(self, tela, entregas, px, py, lp):
        tela.blit(self.fonte_pequena.render('Nova entrega:', True, TEXTO_DIM),
                  (px + 10, py + 92))
        for rotulo, ox in [('Tempo(min)', 10), ('Destino', 112), ('Bônus(R$)', 214)]:
            tela.blit(self.fonte_pequena.render(rotulo, True, CINZA),
                      (px + ox, py + 124))

        self.campo_entrega_tempo.desenhar(tela)
        self.campo_entrega_destino.desenhar(tela)
        self.campo_entrega_bonus.desenhar(tela)
        self.btn_add_entrega.desenhar(tela)

        pygame.draw.line(tela, BORDA_PAINEL,
                         (px + 10, py + 188), (px + lp - 10, py + 188), 1)
        tela.blit(
            self.fonte_pequena.render(
                f'Entregas agendadas ({len(entregas)}):', True, TEXTO_DIM),
            (px + 10, py + 194))

        self._desenhar_lista_rolavel(
            tela, entregas, px, py + 214, lp,
            self.ALTURA_PAINEL - 214 - 82,
            altura_item=46,
            scroll_ref='entregas',
            renderizar_item=self._item_entrega,
            largura_btn_rem=32,
        )

    def _desenhar_aba_conexoes(self, tela, grafo, px, py, lp):
        tela.blit(self.fonte_pequena.render(
                      'Nova conexão (bidirecional):', True, TEXTO_DIM),
                  (px + 10, py + 92))
        for rotulo, ox in [('Origem', 10), ('Destino', 112), ('Tempo(min)', 214)]:
            tela.blit(self.fonte_pequena.render(rotulo, True, CINZA),
                      (px + ox, py + 124))

        self.campo_conn_origem.desenhar(tela)
        self.campo_conn_destino.desenhar(tela)
        self.campo_conn_tempo.desenhar(tela)
        self.btn_add_conn.desenhar(tela)

        arestas = [(a, b, t)
                   for a, viz in grafo.adjacencia.items()
                   for b, t in viz.items() if a < b]

        pygame.draw.line(tela, BORDA_PAINEL,
                         (px + 10, py + 188), (px + lp - 10, py + 188), 1)
        tela.blit(
            self.fonte_pequena.render(
                f'Conexões existentes ({len(arestas)}):', True, TEXTO_DIM),
            (px + 10, py + 194))

        self._desenhar_lista_rolavel(
            tela, arestas, px, py + 214, lp,
            self.ALTURA_PAINEL - 214 - 82,
            altura_item=38,
            scroll_ref='conexoes',
            renderizar_item=self._item_conexao,
            largura_btn_rem=32,
        )

    def _desenhar_lista_rolavel(self, tela, itens, px, area_y, lp,
                                 area_h, altura_item, scroll_ref,
                                 renderizar_item, largura_btn_rem):
        scroll     = getattr(self, f'scroll_{scroll_ref}')
        max_scroll = max(0, len(itens) * altura_item - area_h)
        scroll     = max(0, min(scroll, max_scroll))
        setattr(self, f'scroll_{scroll_ref}', scroll)

        regiao = pygame.Rect(px + 8, area_y, lp - 16, area_h)
        pygame.draw.rect(tela, CINZA_CLARO, regiao, border_radius=4)

        clip_ant = tela.get_clip()
        tela.set_clip(regiao)

        for i, item in enumerate(itens):
            iy = area_y + i * altura_item - scroll
            if iy + altura_item < area_y or iy > area_y + area_h:
                continue

            cor_fundo = AZUL_FUNDO if i % 2 == 0 else BRANCO
            pygame.draw.rect(tela, cor_fundo,
                             (px + 10, iy + 2, lp - 20, altura_item - 4),
                             border_radius=4)

            renderizar_item(tela, item, px, iy, lp, largura_btn_rem)

        tela.set_clip(clip_ant)

        # Barra de rolagem
        if len(itens) * altura_item > area_h and max_scroll > 0:
            prop    = area_h / (len(itens) * altura_item)
            sb_h    = max(20, int(area_h * prop))
            sb_y    = int((scroll / max_scroll) * (area_h - sb_h))
            pygame.draw.rect(tela, CINZA,
                             (px + lp - 14, area_y + sb_y, 6, sb_h),
                             border_radius=3)

    def _item_entrega(self, tela, entrega, px, iy, lp, lb):
        info = (f't={entrega.tempo_inicio}min  '
                f'→{entrega.destino}  R${entrega.bonus:.1f}')
        surf = self.fonte_pequena.render(info, True, TEXTO)
        tela.blit(surf, (px + 14, iy + 14))

        btn = pygame.Rect(px + lp - lb - 12, iy + 10, lb, 22)
        pygame.draw.rect(tela, VERMELHO_FUNDO, btn, border_radius=4)
        t_rem = self.fonte_pequena.render('✕', True, VERMELHO)
        tela.blit(t_rem, (btn.centerx - t_rem.get_width() // 2,
                           btn.centery - t_rem.get_height() // 2))

    def _item_conexao(self, tela, aresta, px, iy, lp, lb):
        a, b, tv = aresta
        info = f'{a}  ↔  {b}     {int(tv)} min'
        surf = self.fonte_pequena.render(info, True, TEXTO)
        tela.blit(surf, (px + 14, iy + 10))

        btn = pygame.Rect(px + lp - lb - 12, iy + 7, lb, 22)
        pygame.draw.rect(tela, VERMELHO_FUNDO, btn, border_radius=4)
        t_rem = self.fonte_pequena.render('✕', True, VERMELHO)
        tela.blit(t_rem, (btn.centerx - t_rem.get_width() // 2,
                           btn.centery - t_rem.get_height() // 2))

    # -----------------------------------------------------------------------
    # Processamento de eventos
    # -----------------------------------------------------------------------

    def processar_eventos(self, evento, grafo, entregas,
                          caminho_conexoes, caminho_entregas):
        """
        Processa eventos do painel.
        Retorna True se o evento foi consumido (não deve ser repassado).
        """
        if not self.visivel:
            return False

        pos_mouse = pygame.mouse.get_pos()

        # Atualiza hover
        for btn in [self.btn_fechar, self.btn_aba_entregas, self.btn_aba_conexoes,
                    self.btn_add_entrega, self.btn_add_conn,
                    self.btn_recarregar, self.btn_limpar]:
            btn.atualizar_hover(pos_mouse)

        # Campos da aba ativa
        campos_ativos = (
            [self.campo_entrega_tempo,
             self.campo_entrega_destino,
             self.campo_entrega_bonus]
            if self.aba_ativa == 'entregas'
            else [self.campo_conn_origem,
                  self.campo_conn_destino,
                  self.campo_conn_tempo]
        )
        for campo in campos_ativos:
            campo.processar_evento(evento)

        # Scroll com roda do mouse
        if evento.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pos_mouse):
            attr = f'scroll_{self.aba_ativa}'
            setattr(self, attr, getattr(self, attr) - evento.y * 22)
            return True

        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            # Fechar
            if self.btn_fechar.foi_clicado(evento):
                self.visivel = False
                return True
            # Troca de aba
            if self.btn_aba_entregas.foi_clicado(evento):
                self.aba_ativa = 'entregas'
                return True
            if self.btn_aba_conexoes.foi_clicado(evento):
                self.aba_ativa = 'conexoes'
                return True
            # Recarregar
            if self.btn_recarregar.foi_clicado(evento):
                return self._acao_recarregar(grafo, entregas,
                                              caminho_conexoes, caminho_entregas)
            # Limpar
            if self.btn_limpar.foi_clicado(evento):
                return self._acao_limpar(grafo, entregas)

            if self.aba_ativa == 'entregas':
                if self.btn_add_entrega.foi_clicado(evento):
                    return self._acao_adicionar_entrega(entregas, grafo)
                return self._verificar_remover_entrega(evento, entregas)

            if self.aba_ativa == 'conexoes':
                if self.btn_add_conn.foi_clicado(evento):
                    return self._acao_adicionar_conexao(grafo)
                return self._verificar_remover_conexao(evento, grafo)

        # Bloqueia cliques fora do painel enquanto ele está aberto
        return self.rect.collidepoint(pos_mouse)

    # -----------------------------------------------------------------------
    # Ações
    # -----------------------------------------------------------------------

    def _acao_adicionar_entrega(self, entregas, grafo):
        try:
            tempo   = int(self.campo_entrega_tempo.texto.strip())
            destino = self.campo_entrega_destino.texto.strip().upper()
            bonus   = float(self.campo_entrega_bonus.texto.strip())
        except ValueError:
            self.exibir_feedback('⚠ Preencha todos os campos corretamente.', VERMELHO)
            return True

        if destino not in grafo.nos:
            self.exibir_feedback(f'⚠ Nó "{destino}" não existe no grafo.', VERMELHO)
            return True
        if destino == 'A':
            self.exibir_feedback('⚠ Destino não pode ser o ponto base A.', VERMELHO)
            return True
        if bonus <= 0:
            self.exibir_feedback('⚠ Bônus deve ser maior que zero.', VERMELHO)
            return True

        entregas.append(Entrega(tempo_inicio=tempo, destino=destino, bonus=bonus))
        entregas.sort(key=lambda e: e.tempo_inicio)

        for campo in [self.campo_entrega_tempo,
                      self.campo_entrega_destino,
                      self.campo_entrega_bonus]:
            campo.texto = ''

        self.exibir_feedback(f'✓ Entrega em {destino} (R${bonus:.1f}) adicionada!', VERDE)
        return True

    def _verificar_remover_entrega(self, evento, entregas):
        px, py  = self.rect.x, self.rect.y
        lp      = self.LARGURA_PAINEL
        area_y  = py + 214
        alt_item = 46

        for i in range(len(entregas)):
            iy  = area_y + i * alt_item - self.scroll_entregas
            btn = pygame.Rect(px + lp - 44, iy + 10, 32, 22)
            if btn.collidepoint(evento.pos):
                removida = entregas.pop(i)
                self.exibir_feedback(
                    f'✓ Entrega em {removida.destino} removida.', AMARELO)
                return True
        return False

    def _acao_adicionar_conexao(self, grafo):
        try:
            origem  = self.campo_conn_origem.texto.strip().upper()
            destino = self.campo_conn_destino.texto.strip().upper()
            tempo   = float(self.campo_conn_tempo.texto.strip())
        except ValueError:
            self.exibir_feedback('⚠ Preencha todos os campos corretamente.', VERMELHO)
            return True

        if not origem or not destino:
            self.exibir_feedback('⚠ Origem e destino são obrigatórios.', VERMELHO)
            return True
        if origem == destino:
            self.exibir_feedback('⚠ Origem e destino não podem ser iguais.', VERMELHO)
            return True
        if tempo <= 0:
            self.exibir_feedback('⚠ Tempo deve ser maior que zero.', VERMELHO)
            return True

        grafo.adicionar_aresta(origem, destino, tempo)

        for campo in [self.campo_conn_origem,
                      self.campo_conn_destino,
                      self.campo_conn_tempo]:
            campo.texto = ''

        self.exibir_feedback(
            f'✓ Conexão {origem}↔{destino} ({int(tempo)}min) adicionada!', VERDE)
        return True

    def _verificar_remover_conexao(self, evento, grafo):
        px, py  = self.rect.x, self.rect.y
        lp      = self.LARGURA_PAINEL
        area_y  = py + 214
        alt_item = 38

        arestas = [(a, b, t)
                   for a, viz in grafo.adjacencia.items()
                   for b, t in viz.items() if a < b]

        for i, (a, b, _) in enumerate(arestas):
            iy  = area_y + i * alt_item - self.scroll_conexoes
            btn = pygame.Rect(px + lp - 44, iy + 7, 32, 22)
            if btn.collidepoint(evento.pos):
                grafo.adjacencia[a].pop(b, None)
                grafo.adjacencia[b].pop(a, None)
                self.exibir_feedback(f'✓ Conexão {a}↔{b} removida.', AMARELO)
                return True
        return False

    def _acao_recarregar(self, grafo, entregas, caminho_conexoes, caminho_entregas):
        try:
            novo_grafo     = ler_conexoes(caminho_conexoes)
            novas_entregas = ler_entregas(caminho_entregas)
        except Exception as erro:
            self.exibir_feedback(f'⚠ Erro ao ler arquivos: {erro}', VERMELHO)
            return True

        # Atualiza in-place para preservar a referência na simulação
        grafo.nos        = novo_grafo.nos
        grafo.adjacencia = novo_grafo.adjacencia
        entregas.clear()
        entregas.extend(novas_entregas)
        self.exibir_feedback('✓ Dados recarregados dos arquivos!', VERDE)
        return True

    def _acao_limpar(self, grafo, entregas):
        entregas.clear()
        grafo.nos        = ['A']
        grafo.adjacencia = {'A': {}}
        self.exibir_feedback('✓ Tudo limpo. Adicione conexões e entregas.', AMARELO)
        return True


# ---------------------------------------------------------------------------
# Classe principal da simulação
# ---------------------------------------------------------------------------

class SimulacaoLeilao:

    def __init__(self, caminho_conexoes: str, caminho_entregas: str):
        pygame.init()
        pygame.display.set_caption('🚚 Leilão de Entregas — Simulação Visual')
        self.tela    = pygame.display.set_mode((LARGURA, ALTURA))
        self.relogio = pygame.time.Clock()

        # Fontes
        self.fonte_titulo  = pygame.font.SysFont('monospace', 20, bold=True)
        self.fonte_normal  = pygame.font.SysFont('monospace', 14)
        self.fonte_pequena = pygame.font.SysFont('monospace', 12)
        self.fonte_no      = pygame.font.SysFont('monospace', 18, bold=True)
        self.fonte_grande  = pygame.font.SysFont('monospace', 28, bold=True)

        # Caminhos dos arquivos (para recarregar pelo painel)
        self.caminho_conexoes = caminho_conexoes
        self.caminho_entregas = caminho_entregas

        # Dados mutáveis (o painel edita diretamente)
        self.grafo    = ler_conexoes(caminho_conexoes)
        self.entregas = ler_entregas(caminho_entregas)

        # Estado
        self.algoritmo_ativo    = None
        self.sequencia          = []
        self.lucro              = 0.0
        self.tempo_exec_ms      = 0.0
        self.historico_ag       = []
        self.animando           = False
        self.animacao_concluida = False
        self.progresso          = 0.0
        self.velocidade         = 1.5
        self.pos_entregador     = None
        self.log_eventos        = []
        self.trajeto_segmentos  = []
        self.seg_atual          = 0

        self.posicoes_nos = self._calcular_posicoes_nos()

        # Painel de parâmetros
        self.painel = PainelParametros(
            LARGURA, ALTURA,
            self.fonte_normal, self.fonte_pequena, self.fonte_titulo,
        )

        self.executar()

    # -----------------------------------------------------------------------
    # Posicionamento dos nós
    # -----------------------------------------------------------------------

    def _calcular_posicoes_nos(self):
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
    # Trajeto de animação
    # -----------------------------------------------------------------------

    def _construir_trajeto(self):
        segmentos = []
        for entrega in self.sequencia:
            for caminho, fase in [
                (self._caminho_dijkstra('A', entrega.destino), 'ida'),
                (self._caminho_dijkstra(entrega.destino, 'A'), 'volta'),
            ]:
                for k in range(len(caminho) - 1):
                    segmentos.append((caminho[k], caminho[k+1], entrega, fase))
        return segmentos

    def _caminho_dijkstra(self, origem, destino):
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
        caminho = []
        atual = destino
        while atual is not None:
            caminho.append(atual)
            atual = prev[atual]
        caminho.reverse()
        return caminho if caminho and caminho[0] == origem else [origem, destino]

    # -----------------------------------------------------------------------
    # Execução dos algoritmos
    # -----------------------------------------------------------------------

    def rodar_algoritmo(self, versao: str):
        if not self.entregas:
            self.log_eventos.append('⚠ Nenhuma entrega cadastrada!')
            return

        self.algoritmo_ativo    = versao
        self.animando           = False
        self.animacao_concluida = False
        self.seg_atual          = 0
        self.progresso          = 0.0
        self.log_eventos        = []
        self.historico_ag       = []

        # Recalcula posições caso novos nós tenham sido adicionados pelo painel
        self.posicoes_nos = self._calcular_posicoes_nos()

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
            no_inicial = self.trajeto_segmentos[0][0]
            self.pos_entregador = list(
                self.posicoes_nos.get(no_inicial, (0, 0)))

        nome = 'A*' if versao == '1' else 'Alg. Genético'
        self.log_eventos.append(
            f'[{nome}] R${self.lucro:.1f} | {self.tempo_exec_ms:.2f}ms')
        self.log_eventos.append(
            f'Entregas: {len(self.sequencia)}/{len(self.entregas)}')

    # -----------------------------------------------------------------------
    # Desenho
    # -----------------------------------------------------------------------

    def _desenhar_fundo(self):
        self.tela.fill(FUNDO)
        pygame.draw.rect(self.tela, BORDA_PAINEL,
                         (AREA_GRAFO_X, AREA_GRAFO_Y,
                          AREA_GRAFO_L, AREA_GRAFO_H), 1)

    def _desenhar_arestas(self):
        for no_a, vizinhos in self.grafo.adjacencia.items():
            for no_b, tempo in vizinhos.items():
                if no_a >= no_b:
                    continue
                if (no_a not in self.posicoes_nos
                        or no_b not in self.posicoes_nos):
                    continue
                x1, y1 = self.posicoes_nos[no_a]
                x2, y2 = self.posicoes_nos[no_b]
                pygame.draw.line(self.tela, CINZA, (x1, y1), (x2, y2), 2)
                mx, my = (x1 + x2) // 2, (y1 + y2) // 2
                rot = self.fonte_pequena.render(f'{int(tempo)}min', True, TEXTO_DIM)
                self.tela.blit(rot, (mx - rot.get_width() // 2,
                                     my - rot.get_height() // 2))

    def _desenhar_arestas_ativas(self):
        if not self.sequencia:
            return
        arestas_sol = set()
        for entrega in self.sequencia:
            for caminho in [self._caminho_dijkstra('A', entrega.destino),
                            self._caminho_dijkstra(entrega.destino, 'A')]:
                for k in range(len(caminho) - 1):
                    arestas_sol.add((min(caminho[k], caminho[k+1]),
                                     max(caminho[k], caminho[k+1])))
        for (a, b) in arestas_sol:
            if a not in self.posicoes_nos or b not in self.posicoes_nos:
                continue
            x1, y1 = self.posicoes_nos[a]
            x2, y2 = self.posicoes_nos[b]
            pygame.draw.line(self.tela, AZUL_CLARO, (x1, y1), (x2, y2), 3)

    def _desenhar_nos(self):
        for no, (x, y) in self.posicoes_nos.items():
            na_solucao = any(e.destino == no for e in self.sequencia)
            cor       = AZUL  if na_solucao else CINZA
            cor_label = AZUL  if na_solucao else TEXTO_DIM

            pygame.draw.circle(self.tela, FUNDO_PAINEL, (x, y), RAIO_NO)
            pygame.draw.circle(self.tela, cor,           (x, y), RAIO_NO, 3)

            label = self.fonte_no.render(no, True, cor_label)
            self.tela.blit(label, (x - label.get_width() // 2,
                                   y - label.get_height() // 2))

            for e in self.entregas:
                if e.destino == no:
                    txt = self.fonte_pequena.render(
                        f'R${e.bonus:.0f}', True, AMARELO)
                    self.tela.blit(txt, (x - txt.get_width() // 2,
                                         y + RAIO_NO + 4))

    def _desenhar_entregador(self):
        if self.pos_entregador and (self.animando or self.seg_atual > 0):
            px = int(self.pos_entregador[0])
            py = int(self.pos_entregador[1])
            pygame.draw.circle(self.tela, (203, 213, 225), (px + 3, py + 3), 16)
            pygame.draw.circle(self.tela, LARANJA, (px, py), 16)
            pygame.draw.circle(self.tela, BRANCO,  (px, py), 16, 2)
            cam = self.fonte_pequena.render('🚚', True, BRANCO)
            self.tela.blit(cam, (px - cam.get_width() // 2,
                                  py - cam.get_height() // 2))

    def _desenhar_painel_esquerdo(self):
        pygame.draw.rect(self.tela, FUNDO_PAINEL,
                         (0, 0, PAINEL_ESQUERDA_L, ALTURA))
        pygame.draw.line(self.tela, BORDA_PAINEL,
                         (PAINEL_ESQUERDA_L, 0),
                         (PAINEL_ESQUERDA_L, ALTURA), 1)

        y = 18
        self.tela.blit(
            self.fonte_titulo.render('ENTREGAS DO DIA', True, AZUL),
            (12, y))
        y += 32
        pygame.draw.line(self.tela, BORDA_PAINEL,
                         (12, y), (PAINEL_ESQUERDA_L - 12, y), 1)
        y += 12

        for i, e in enumerate(self.entregas):
            if y + 58 > ALTURA - 60:
                self.tela.blit(
                    self.fonte_pequena.render(
                        f'+ {len(self.entregas) - i} mais...', True, TEXTO_DIM),
                    (16, y + 4))
                break

            selecionada = e in self.sequencia
            cor_bg  = AZUL_FUNDO if selecionada else FUNDO
            cor_txt = VERDE      if selecionada else TEXTO_DIM
            cor_bor = AZUL       if selecionada else BORDA_PAINEL

            pygame.draw.rect(self.tela, cor_bg,
                             (10, y, PAINEL_ESQUERDA_L - 20, 58),
                             border_radius=6)
            pygame.draw.rect(self.tela, cor_bor,
                             (10, y, PAINEL_ESQUERDA_L - 20, 58), 1,
                             border_radius=6)

            self.tela.blit(
                self.fonte_normal.render(
                    f'#{i+1}  ⏱ t={e.tempo_inicio}min', True, cor_txt),
                (16, y + 6))
            self.tela.blit(
                self.fonte_normal.render(f'   Destino: {e.destino}', True, TEXTO),
                (16, y + 22))
            self.tela.blit(
                self.fonte_normal.render(f'   Bônus:  R$ {e.bonus:.1f}', True, AMARELO),
                (16, y + 38))

            if selecionada:
                self.tela.blit(
                    self.fonte_normal.render('✓', True, VERDE),
                    (PAINEL_ESQUERDA_L - 28, y + 20))

            y += 68

        # Botão para abrir painel de parâmetros
        btn_rect = pygame.Rect(10, ALTURA - 52, PAINEL_ESQUERDA_L - 20, 36)
        hover    = btn_rect.collidepoint(pygame.mouse.get_pos())
        cor_btn  = (30, 100, 210) if hover else AZUL
        pygame.draw.rect(self.tela, cor_btn, btn_rect, border_radius=6)
        t_btn = self.fonte_normal.render('[P]  ⚙ Editar Parâmetros', True, BRANCO)
        self.tela.blit(t_btn, (btn_rect.centerx - t_btn.get_width() // 2,
                                btn_rect.centery - t_btn.get_height() // 2))

    def _desenhar_painel_direito(self):
        x0 = AREA_GRAFO_X + AREA_GRAFO_L
        pygame.draw.rect(self.tela, FUNDO_PAINEL,
                         (x0, 0, PAINEL_DIREITA_L, ALTURA))
        pygame.draw.line(self.tela, BORDA_PAINEL,
                         (x0, 0), (x0, ALTURA), 1)

        y = 18
        self.tela.blit(
            self.fonte_titulo.render('CONTROLES', True, LARANJA),
            (x0 + 12, y))
        y += 32
        pygame.draw.line(self.tela, BORDA_PAINEL,
                         (x0 + 12, y), (x0 + PAINEL_DIREITA_L - 12, y), 1)
        y += 14

        controles = [
            ('[1]',      'Rodar A*'),
            ('[2]',      'Rodar Alg. Genético'),
            ('[ESPAÇO]', 'Iniciar/Pausar'),
            ('[R]',      'Reiniciar'),
            ('[P]',      'Editar parâmetros'),
            ('[+]',      'Aumentar velocidade'),
            ('[-]',      'Diminuir velocidade'),
            ('[ESC]',    'Sair'),
        ]
        for tecla, desc in controles:
            self.tela.blit(
                self.fonte_normal.render(tecla, True, AZUL), (x0 + 14, y))
            self.tela.blit(
                self.fonte_pequena.render(desc, True, TEXTO_DIM),
                (x0 + 14, y + 18))
            y += 38

        y += 10
        pygame.draw.line(self.tela, BORDA_PAINEL,
                         (x0 + 12, y), (x0 + PAINEL_DIREITA_L - 12, y), 1)
        y += 14

        alg_nome = {'1': 'A* (Determinístico)',
                    '2': 'Alg. Genético'}.get(self.algoritmo_ativo, '—')
        self.tela.blit(
            self.fonte_normal.render('Algoritmo:', True, TEXTO_DIM),
            (x0 + 14, y)); y += 20
        self.tela.blit(
            self.fonte_normal.render(alg_nome, True, TEXTO),
            (x0 + 14, y)); y += 28

        self.tela.blit(
            self.fonte_normal.render('Lucro Total:', True, TEXTO_DIM),
            (x0 + 14, y)); y += 20
        self.tela.blit(
            self.fonte_grande.render(f'R$ {self.lucro:.1f}', True, AMARELO),
            (x0 + 14, y)); y += 44

        self.tela.blit(
            self.fonte_normal.render('Exec. algoritmo:', True, TEXTO_DIM),
            (x0 + 14, y)); y += 20
        self.tela.blit(
            self.fonte_normal.render(f'{self.tempo_exec_ms:.3f} ms', True, VERDE),
            (x0 + 14, y)); y += 32

        self.tela.blit(
            self.fonte_normal.render('Vel. animação:', True, TEXTO_DIM),
            (x0 + 14, y)); y += 20
        self.tela.blit(
            self.fonte_normal.render(f'{self.velocidade:.1f}x', True, TEXTO),
            (x0 + 14, y)); y += 32

        if self.trajeto_segmentos:
            pct = self.seg_atual / len(self.trajeto_segmentos)
            pygame.draw.line(self.tela, BORDA_PAINEL,
                             (x0 + 12, y),
                             (x0 + PAINEL_DIREITA_L - 12, y), 1); y += 14
            self.tela.blit(
                self.fonte_normal.render('Progresso da rota:', True, TEXTO_DIM),
                (x0 + 14, y)); y += 20
            barra_l = PAINEL_DIREITA_L - 28
            pygame.draw.rect(self.tela, CINZA,
                             (x0 + 14, y, barra_l, 12), border_radius=4)
            pygame.draw.rect(self.tela, AZUL,
                             (x0 + 14, y, int(barra_l * pct), 12),
                             border_radius=4)
            y += 24

        pygame.draw.line(self.tela, BORDA_PAINEL,
                         (x0 + 12, y), (x0 + PAINEL_DIREITA_L - 12, y), 1)
        y += 10
        self.tela.blit(
            self.fonte_normal.render('Log:', True, TEXTO_DIM),
            (x0 + 14, y)); y += 20
        for msg in self.log_eventos[-6:]:
            self.tela.blit(
                self.fonte_pequena.render(msg[:36], True, TEXTO_DIM),
                (x0 + 14, y)); y += 18

    def _desenhar_barra_inferior(self):
        y0 = AREA_GRAFO_H
        pygame.draw.rect(self.tela, FUNDO_PAINEL,
                         (AREA_GRAFO_X, y0, AREA_GRAFO_L, ALTURA - y0))
        pygame.draw.line(self.tela, BORDA_PAINEL,
                         (AREA_GRAFO_X, y0),
                         (AREA_GRAFO_X + AREA_GRAFO_L, y0), 1)

        if self.sequencia:
            partes = ['A']
            for e in self.sequencia:
                partes += [f'→{e.destino}(+R${e.bonus:.0f})', '→A']
            rota_str = ' '.join(partes)
        else:
            rota_str = 'Nenhuma rota calculada. Pressione [1] ou [2].'

        self.tela.blit(
            self.fonte_normal.render(rota_str[:100], True, TEXTO),
            (AREA_GRAFO_X + 12, y0 + 14))

        status = ('ANIMANDO...' if self.animando
                  else ('CONCLUÍDO' if self.animacao_concluida else 'PRONTO'))
        cor_st = (VERDE  if self.animacao_concluida
                  else (AMARELO if self.animando else TEXTO_DIM))
        self.tela.blit(
            self.fonte_normal.render(status, True, cor_st),
            (AREA_GRAFO_X + 12, y0 + 36))

    # -----------------------------------------------------------------------
    # Animação
    # -----------------------------------------------------------------------

    def _atualizar_animacao(self):
        if not self.animando or not self.trajeto_segmentos:
            return
        if self.seg_atual >= len(self.trajeto_segmentos):
            self.animando           = False
            self.animacao_concluida = True
            return

        origem_no, destino_no, entrega, fase = self.trajeto_segmentos[self.seg_atual]
        if (origem_no not in self.posicoes_nos
                or destino_no not in self.posicoes_nos):
            self.seg_atual += 1
            return

        x1, y1 = self.posicoes_nos[origem_no]
        x2, y2 = self.posicoes_nos[destino_no]
        dist   = math.hypot(x2 - x1, y2 - y1)
        self.progresso += (self.velocidade * VELOCIDADE_BASE) / max(dist, 1)

        if self.progresso >= 1.0:
            self.progresso = 0.0
            self.seg_atual += 1
            if self.seg_atual < len(self.trajeto_segmentos):
                no_prox = self.trajeto_segmentos[self.seg_atual][0]
                self.pos_entregador = list(
                    self.posicoes_nos.get(no_prox, self.pos_entregador))
                _, dest_ant, e_ant, f_ant = (
                    self.trajeto_segmentos[self.seg_atual - 1])
                if f_ant == 'ida' and dest_ant == e_ant.destino:
                    self.log_eventos.append(
                        f'✓ Entregue em {dest_ant}! +R${e_ant.bonus:.0f}')
            else:
                self.animando           = False
                self.animacao_concluida = True
                self.log_eventos.append('🏁 Rota completa!')
        else:
            self.pos_entregador = [
                x1 + (x2 - x1) * self.progresso,
                y1 + (y2 - y1) * self.progresso,
            ]

    # -----------------------------------------------------------------------
    # Loop principal
    # -----------------------------------------------------------------------

    def _reiniciar_simulacao(self):
        self.sequencia          = []
        self.lucro              = 0.0
        self.animando           = False
        self.animacao_concluida = False
        self.seg_atual          = 0
        self.progresso          = 0.0
        self.algoritmo_ativo    = None
        self.log_eventos        = []
        self.pos_entregador     = None
        self.trajeto_segmentos  = []

    def executar(self):
        rodando = True
        while rodando:
            self.relogio.tick(FPS)

            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    rodando = False
                    continue

                # Painel consome o evento se estiver aberto e for relevante
                if self.painel.processar_eventos(
                        evento, self.grafo, self.entregas,
                        self.caminho_conexoes, self.caminho_entregas):
                    continue

                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_ESCAPE:
                        rodando = False

                    elif evento.key == pygame.K_1:
                        self.rodar_algoritmo('1')

                    elif evento.key == pygame.K_2:
                        self.rodar_algoritmo('2')

                    elif evento.key == pygame.K_p:
                        self.painel.alternar_visibilidade()

                    elif evento.key == pygame.K_SPACE:
                        if self.sequencia and not self.animacao_concluida:
                            self.animando = not self.animando
                        elif self.animacao_concluida:
                            self.seg_atual          = 0
                            self.progresso          = 0.0
                            self.animacao_concluida = False
                            self.animando           = True
                            if self.trajeto_segmentos:
                                no_ini = self.trajeto_segmentos[0][0]
                                self.pos_entregador = list(
                                    self.posicoes_nos.get(no_ini, [0, 0]))

                    elif evento.key == pygame.K_r:
                        self._reiniciar_simulacao()

                    elif evento.key in (pygame.K_PLUS, pygame.K_EQUALS,
                                        pygame.K_KP_PLUS):
                        self.velocidade = min(self.velocidade + 0.5, 8.0)

                    elif evento.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                        self.velocidade = max(self.velocidade - 0.5, 0.5)

                # Clique no botão "Editar Parâmetros" do painel esquerdo
                elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    btn_rect = pygame.Rect(10, ALTURA - 52,
                                           PAINEL_ESQUERDA_L - 20, 36)
                    if btn_rect.collidepoint(evento.pos):
                        self.painel.alternar_visibilidade()

            self._atualizar_animacao()

            # Desenha cena principal
            self._desenhar_fundo()
            self._desenhar_arestas()
            self._desenhar_arestas_ativas()
            self._desenhar_nos()
            self._desenhar_entregador()
            self._desenhar_painel_esquerdo()
            self._desenhar_painel_direito()
            self._desenhar_barra_inferior()

            # Mensagem inicial
            if self.algoritmo_ativo is None and not self.painel.visivel:
                msg = self.fonte_titulo.render(
                    'Pressione [1] para A*  ou  [2] para Algoritmo Genético',
                    True, AZUL)
                cx = AREA_GRAFO_X + AREA_GRAFO_L // 2
                cy = AREA_GRAFO_H // 2 + 100
                self.tela.blit(msg, (cx - msg.get_width() // 2, cy))

            # Painel sempre por cima de tudo
            self.painel.desenhar(self.tela, self.grafo, self.entregas)

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