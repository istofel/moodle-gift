---
name: moodle-gift
description: Gera provas, avaliações, simulados, listas de exercícios e bancos de questões no formato GIFT para importar no Moodle, entregando arquivo validado, gabarito comentado e, se pedido, versão impressa. Cobre múltipla escolha (uma ou várias corretas), verdadeiro/falso, resposta curta, numérica com tolerância, associação, lacuna, dissertativa e descrição, com feedback, pesos parciais, categorias e tags, e escape correto de código, fórmulas e caracteres especiais. Use SEMPRE que o usuário pedir para criar, gerar ou elaborar questões, prova, quiz, questionário, avaliação ou simulado para o Moodle, citar GIFT ou banco de questões, quiser transformar uma apostila, PDF, slides ou lista do Word em questões importáveis no Moodle, ou pedir para revisar, corrigir ou validar um arquivo .gift que dá erro na importação — mesmo sem dizer GIFT.
license: Apache-2.0
---

# Moodle GIFT

Gera questões no formato GIFT prontas para **Banco de questões → Importar** do Moodle.

A parte difícil do GIFT não é escrever a questão, é não quebrar a importação: um `=` sem escape num feedback cria uma alternativa fantasma, `{#3,14}` faz o Moodle aceitar qualquer resposta, pesos como 33% são rejeitados. Por isso o fluxo separa as duas coisas: você escreve o conteúdo em JSON com texto normal e o `scripts/build_gift.py` produz o GIFT com os escapes e as regras do importador, validando no fim.

## Entregáveis

1. **`<slug>.gift.txt`** — arquivo de importação, **com respostas e feedback**. É o que o Moodle precisa: sem respostas, toda questão vira dissertativa ou descrição. O aluno nunca vê este arquivo. A extensão `.gift.txt` é aceita por qualquer instalação (algumas rejeitam `.gift`).
2. **`gabarito_<slug>.md`** — para o professor: tabela-resumo, resposta, justificativa, distribuição por tipo/dificuldade/Bloom.
3. **`prova_<slug>.md`** — versão para impressão **sem respostas**. Só quando o usuário pedir prova impressa/PDF/Word (converta com a skill de docx/pdf se ele pedir esses formatos).

## Fluxo

### 1. Entender o pedido
Parâmetros: tema/disciplina, quantidade, tipos, dificuldade, público/nível, categoria no Moodle, material-base.

- Se faltar **tema** ou **quantidade**, pergunte em uma única pergunta curta. O resto tem padrão.
- Padrões: tipos variados com predominância de múltipla escolha; 4 alternativas (5 se estilo ENEM/vestibular); dificuldade ~30/50/20 (fácil/média/difícil); feedback em todas as alternativas; categoria = nome da disciplina (e unidade, se houver); `formato: "texto"`.
- Com material-base (PDF, slides, apostila, ementa), leia-o antes (skills de leitura de arquivo) e elabore as questões **somente** a partir dele, registrando `fonte` (página/slide).
- "N questões" significa N avaliativas: descrições (instruções/texto-base) não contam.

### 2. Ler as referências certas
- `references/esquema-json.md` — sempre: formato do spec.
- `references/elaboracao-de-itens.md` — sempre que for criar conteúdo: distratores, Bloom, feedback, títulos.
- `references/sintaxe-gift.md` — ao editar GIFT à mão, diagnosticar erro de importação ou tratar código, LaTeX, imagens e pesos.

### 3. Escrever o spec
Crie `/home/claude/<slug>/spec.json` (modelo: `assets/exemplo_spec.json`). Pontos que evitam retrabalho:
- Texto normal, **sem escapes GIFT** — o script escapa; escapar antes gera `\\=` visível para o aluno.
- Código vai em `codigo` (não no enunciado), fórmulas em `\( ... \)`.
- Respostas numéricas: **calcule com Python** e cole o resultado; defina tolerância coerente com o arredondamento pedido no enunciado.
- Preencha `quantidade_esperada`, `dificuldade`, `bloom` e `justificativa` — alimentam o gabarito e as checagens.

### 4. Gerar e validar
`<skill>` = pasta deste SKILL.md (ex.: `/mnt/skills/user/moodle-gift`).
```bash
python3 <skill>/scripts/build_gift.py /home/claude/<slug>/spec.json --saida /mnt/user-data/outputs [--impressa]
```
- Erro → nada é gravado. Corrija o **spec** (não o .gift gerado) e rode de novo, até `RESULTADO: OK`.
- `[AVISO PEDAGÓGICO]` não bloqueia, mas corrija quando fizer sentido (título que entrega a resposta, "todas as anteriores", correta sempre na mesma letra).

### 5. Revisar o conteúdo
O validador garante a sintaxe, não a qualidade. Releia o gabarito gerado com o checklist da seção 7 de `elaboracao-de-itens.md`: resposta certa e única, distratores plausíveis, sem pistas, português correto.

### 6. Entregar
Apresente os arquivos com `present_files` e responda com:
- 1–2 frases: quantas questões, distribuição por tipo e suposições feitas (padrões aplicados).
- Como importar em uma linha: *Banco de questões → Importar → GIFT → marcar "Obter categoria do arquivo" → enviar o `.gift.txt`*.

Não cole o conteúdo dos arquivos no chat: eles são o produto e o texto inline só duplica e alonga a resposta. Se o usuário pedir para ver alguma questão, mostre.

## Revisar ou corrigir um .gift existente

```bash
python3 <skill>/scripts/validate_gift.py arquivo.gift.txt [--esperado N]
```
O validador replica a lógica do importador do Moodle e aponta erros (chaves, pesos, tipos) e armadilhas silenciosas (vírgula decimal, `{true}` minúsculo, numérica sem `#`, `*` sozinho). Explique os problemas em linguagem simples, corrija seguindo `references/sintaxe-gift.md` (`assets/exemplo_todos_os_tipos.gift.txt` mostra a forma correta de cada tipo) e valide de novo. Para reestruturar um arquivo grande, pode ser mais seguro convertê-lo para spec JSON e regenerar.

## Regras GIFT que o script aplica (e que valem ao editar à mão)

- Linha em branco separa questões; nunca dentro de uma (use `\n`). UTF-8 sem BOM.
- Escape de `~ = # { } :` e `\` com barra invertida, em todo texto.
- Um bloco `{}` por questão → uma lacuna por questão; várias lacunas exigem Cloze, que não é GIFT.
- Múltipla escolha precisa de ao menos um `~`; múltiplas respostas não têm `=` e os pesos positivos somam 100%.
- Pesos só da lista do Moodle (100, 90, 83.33333, 80, 75, 70, 66.66667, 60, 50, 40, 33.33333, 30, 25, 20, 16.66667, 14.28571, 12.5, 11.11111, 10, 5, 0 e negativos).
- Numérica começa com `#` e usa ponto decimal.
- `TRUE`/`FALSE` em maiúsculas; o 1º feedback de V/F vai para quem errou.
- Formato depois do título: `::Título::[html]Texto`.
- Resposta curta: `*` é curinga; acentos não são ignorados.
- Associação: ≥3 pares, sem feedback por par.

## Limites do GIFT (avise o usuário quando o pedido esbarrar neles)

- Sem imagens embutidas: só URL pública em `imagem`; imagens locais precisam ser inseridas depois no Moodle (ou usar Moodle XML).
- Sem várias lacunas, arrastar-e-soltar, questões calculadas ou "Informações para avaliadores" da dissertativa.
- Diferenciar maiúsculas em resposta curta: ajustar na questão depois da importação.
