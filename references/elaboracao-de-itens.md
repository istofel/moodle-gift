# Elaboração de itens — guia de qualidade

Uma questão que importa sem erro ainda pode ser ruim: ambígua, com resposta entregue pelo formato ou medindo só memorização. Este guia resume boas práticas de elaboração de itens (psicometria e matrizes de avaliação como as do INEP) adaptadas ao Moodle.

## 1. Planejamento

- **Objetivo por questão**: cada item mede uma habilidade específica do conteúdo pedido. Se o usuário forneceu material (apostila, slides, ementa), use somente esse conteúdo e registre a origem em `fonte`.
- **Distribuição padrão** (quando o usuário não definir):
  - Dificuldade: ~30% fácil, 50% média, 20% difícil.
  - Bloom: cerca de 1/3 lembrar/compreender, 1/2 aplicar/analisar, o restante avaliar/criar (em geral via dissertativa ou análise de caso).
  - Tipos: maioria múltipla escolha, complementada por V/F, resposta curta/numérica e 1 dissertativa a cada ~10 itens. Se o usuário pedir só correção automática, não inclua dissertativa.
- **Público**: ajuste vocabulário e complexidade ao nível (fundamental, médio, técnico, superior).

| Nível de Bloom | Verbos típicos no comando |
|---|---|
| Lembrar | identifique, cite, defina, reconheça |
| Compreender | explique, classifique, interprete, compare |
| Aplicar | calcule, resolva, execute, utilize |
| Analisar | diferencie, organize, encontre o erro, relacione causa e efeito |
| Avaliar | julgue, justifique, escolha a melhor solução e defenda |
| Criar | proponha, projete, elabore |

## 2. Enunciado (comando)

- Autossuficiente: dá para responder sem ler as alternativas.
- Uma única ideia por item; sem pegadinhas de leitura.
- Prefira forma afirmativa. Se precisar de negação, destaque: "NÃO", "INCORRETA".
- Texto-base (situação-problema, dado, gráfico, código) antes do comando, quando houver.
- Evite "sempre", "nunca", "todos" que tornam a alternativa trivialmente falsa.

## 3. Alternativas (múltipla escolha)

- 4 alternativas por padrão (5 em estilo ENEM/vestibular). Exatamente uma correta e inquestionável.
- **Distratores plausíveis**: cada um corresponde a um erro real de raciocínio (conceito confundido, sinal trocado, unidade esquecida, etapa omitida). Em numérica/cálculo, gere distratores a partir desses erros.
- Homogêneas em tamanho, estrutura gramatical e nível técnico — a correta não pode ser a mais longa ou a mais detalhada.
- Nada de "todas as anteriores" / "nenhuma das anteriores": o Moodle embaralha as alternativas por padrão e essas opções perdem o sentido.
- Varie a posição da correta (conta na versão impressa).
- Sem sobreposição entre alternativas (uma não pode conter a outra).

## 4. Outros tipos

- **V/F**: afirmação inequivocamente verdadeira ou falsa, sem dupla negação. Equilibre verdadeiras e falsas.
- **Resposta curta**: resposta de 1–3 palavras e inequívoca. Liste variantes aceitáveis (acentos, abreviações, sinônimos). Evite pedir frases.
- **Numérica**: informe a unidade e o arredondamento esperado no enunciado ("em km/h, com uma casa decimal"). Defina tolerância coerente com o arredondamento. **Calcule a resposta com Python** em vez de fazer de cabeça.
- **Associação**: itens homogêneos (todos conceitos, ou todos exemplos), 3–6 pares, pelo menos 1 distrator.
- **Lacuna**: a lacuna deve estar num termo-chave, não em palavra trivial.
- **Dissertativa**: comando delimitado (o que abordar, extensão esperada) e critérios de correção objetivos no gabarito.

## 5. Feedback

- Nas erradas, explique o equívoco provável ("Você somou as resistências como se estivessem em série").
- Na correta, reforce o porquê em uma frase.
- `feedback_geral` é opcional; use para o raciocínio completo ou uma referência de estudo.
- O feedback é visível ao aluno na revisão: nada de ironia nem de dar a resposta de outras questões.

## 6. Títulos (nomes no banco de questões)

Curto, único, descritivo do conteúdo, **sem revelar a resposta**. Bom: `Q07 - Resistores em paralelo`. Ruim: `A Terra é redonda` (para uma V/F sobre a forma da Terra).

## 7. Revisão antes de entregar

Para cada item, confirme:
1. A resposta marcada está correta (confira fatos e cálculos).
2. Só existe uma resposta defensável.
3. O item não depende de outro item nem entrega a resposta de outro.
4. Linguagem clara, sem erro de português, adequada ao público.
5. Pelo menos um distrator por erro conceitual comum.
