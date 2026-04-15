
<h1 align="center">Leilão de Entregas: Otimização de Rotas e Lucro</h1>

<p align="center">
  <strong>Inteligência Artificial — Católica SC</strong><br/>
  Projeto de Algoritmos de Busca e Otimização · Busca Heurística vs. Meta-heurística
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Pygame-Visualizacao-yellowgreen?logo=pygame" alt="Pygame"/>
  <img src="https://img.shields.io/badge/Algoritmo-A*-orange" alt="A* Search"/>
  <img src="https://img.shields.io/badge/Algoritmo-Meta--heurística-red" alt="Meta-heuristic"/>
  <img src="https://img.shields.io/badge/Matplotlib-Analytics-blue" alt="Matplotlib"/>
</p>

---

## 1. Visão do Projeto

### 1.1 O Problema do Leilão de Entregas

No setor de logística de última milha (*last-mile delivery*), o desafio não consiste apenas em encontrar o caminho mais curto, mas em selecionar a combinação de entregas que maximize o lucro (bônus) dentro de restrições de tempo e conexões. 

O projeto aborda um cenário onde o sistema deve:
- Processar grafos de conexões entre pontos de entrega.
- Avaliar janelas de oportunidade e bônus associados a cada entrega.
- Resolver o conflito de escolha: "Qual sequência de entregas gera o maior retorno financeiro antes do fim do expediente?"

---

### 1.2 Abordagens de Resolução

O sistema implementa duas filosofias de busca distintas para resolver o mesmo problema de otimização:

| Versão | Algoritmo | Tipo de Busca | Estratégia Principal |
|---|---|---|---|
| **V1** | **A* (A-Estrela)** | Determinística / Heurística | Minimizar a "Perda de Bônus" para encontrar a solução ótima global através de uma função de custo $f(n) = g(n) + h(n)$. |
| **V2** | **Meta-heurística** | Estocástica / Combinatória | Exploração do espaço de estados (ex: Algoritmos Genéticos ou Simulated Annealing) para encontrar soluções excelentes em tempo reduzido. |

---

### 1.3 Funcionalidades Chave

- **Ingestão de Dados:** Leitura automatizada de listas de conexões e listas de entregas disponíveis.
- **Engine de Decisão:** Processamento paralelo das duas versões de busca para comparação em tempo real.
- **Simulador Gráfico (Pygame):** Interface interativa que permite visualizar os agentes percorrendo as rotas, além de permitir a modificação de parâmetros de simulação pelo usuário.
- **Analytics:** Geração de gráficos comparativos detalhando o *trade-off* entre **Tempo de Execução** e **Lucro Obtido (Bônus)**.

---
### 1.4 Exemplo de Saída
O sistema gera o escalonamento no formato: `(ID_ENTREGA, PONTO; LUCRO_ESPERADO)`
> Exemplo: `(5, C; 10)` -> Entrega 5, realizada no ponto C, com lucro de 10 unidades.

---

## 2. Resultados

### 2.1 Resultados do exemplo de saída

Ambos encontraram corretamente a solução ótima: `(5, C, 10)` → Lucro = R$ 10

| Algoritmo | Lucro | Tempo | Tipo de Busca |
| :--- | :---: | :---: | :--- |
| **A\*** | R$ 10 | ~0,1 ms | Determinística (Exata) |
| **Algoritmo Genético** | R$ 10 | ~450 ms | Estocástica (Heurística) |

Na análise de escalabilidade (n=15 entregas), o A* já começa a demorar mais e o AG pode ficar levemente voltado ao ótimo. Um comportamento esperado para meta-heurísticas.

---

### 2.2 Diferença de Performance

Para problemas de pequena escala, o **A\*** é consideravelmente superior em tempo de execução, pois explora o espaço de estados de maneira direta. O **Algoritmo Genético** possui um "overhead" inicial (criação da população, crossover e mutação), resultando em um tempo maior. No entanto, em cenários de alta complexidade com centenas de entregas, o A* sofreria com a explosão combinatória, enquanto o Genético se manteria viável entregando soluções muito próximas ao ótimo em tempo polinomial.

---

### 2.3 Gráficos Comparativos

---

## 3. Interface Visual (Pygame)

O usuário pode interagir com o ambiente para testar a resiliência dos algoritmos frente a mudanças súbitas na lista de entregas.

No Pygame: pressione `[1]` ou `[2]` para calcular a rota e `[ESPAÇO]` para animar o entregador.
```bash
    python simulacao_pygame.py --simulacao
```

---

## 4. Estrutura do Projeto

| Arquivo | Descrição |
| :--- | :--- |
| `modelos.py` | Estruturas de dados, leitura de arquivos, Dijkstra, utilitários compartilhados |
| `versao1_a_estrela.py` | Versão 1 — Busca determinística com A* |
| `versao2_genetico.py` | Versão 2 — Meta-heurística com Algoritmo Genético |
| `comparacao.py` | Geração dos gráficos comparativos (matplotlib) |
| `simulacao_pygame.py` | Simulação visual interativa (Pygame) |
| `main.py` | Ponto de entrada unificado com argumentos CLI |
| `conexoes.txt` / `entregas.txt` | Dados de exemplo do enunciado |



## 5. Como Executar

### Pré-requisitos
- Python v3.12 (É utlizado o `lib pygame`, ele ainda não tem um pacote pré-compilado compatível com a versão 3.14)
- Pip (Gerenciador de pacotes)

### Instalação e Uso
```bash
   git clone [https://github.com/usuario/leilao-entregas.git](https://github.com/usuario/leilao-entregas.git)
```
### Como rodar
```bash
  pip install matplotlib pygame

  python main.py                                  # tudo em sequência
  python versao1_a_estrela.py --versao 1          # só A*
  python versao2_genetico.py --versao 2           # só AG
  python comparacao.py --comparar                 # gráficos
  python simulacao_pygame.py --simulacao          # Pygame interativo
```
