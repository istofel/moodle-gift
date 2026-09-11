# Especificação JSON para `build_gift.py`

Escreva o conteúdo em **texto normal**: sem escapes GIFT (`\=`, `\{`...) e sem HTML (a menos que use `"formato": "html"`). O script escapa tudo; escapar antes causa escape duplo. Exemplo completo com todos os tipos: `assets/exemplo_spec.json`.

## Campos gerais

| Campo | Obrig. | Descrição |
|---|---|---|
| `titulo` | sim | Título da prova. Base do nome dos arquivos (se não houver `slug`). |
| `disciplina` | não | Aparece no gabarito e na versão impressa. |
| `publico` | não | Ex.: "1º ano do ensino médio técnico". |
| `slug` | não | Nome base dos arquivos (é sanitizado: minúsculas, sem acento, `_`). |
| `categoria` | não | Caminho no banco de questões, ex.: `"Redes/Unidade 2"` → `$CATEGORY:`. |
| `formato` | não | Formato padrão do texto: `texto` (padrão), `html`, `markdown`, `moodle`, `plain`. |
| `quantidade_esperada` | recomendado | Nº de questões avaliativas (descrições não contam). O script confere. |
| `numerar_titulos` | não | `true` (padrão): títulos viram `Q01 - ...`. |
| `tags_automaticas` | não | `true` (padrão): gera tags `dificuldade-x` e `bloom-x`. |
| `instrucoes` | não | Texto no topo da versão impressa. |
| `questoes` | sim | Lista de questões (abaixo). |

### Formatos de texto
- `texto` (recomendado): você escreve texto puro; o script converte para HTML seguro (`<`, `&` viram entidades; quebras de linha viram `<br>`) e grava `[html]`.
- `html`: você escreve HTML válido; só o escape GIFT é aplicado.
- `markdown`: grava `[markdown]`; quebras de linha preservadas.
- `moodle` / `plain`: repassados como estão.

## Campos comuns a todas as questões

| Campo | Descrição |
|---|---|
| `tipo` | `multipla_escolha`, `multipla_resposta`, `verdadeiro_falso`, `resposta_curta`, `numerica`, `associacao`, `dissertativa`, `descricao` ou `lacuna` |
| `titulo` | Curto, único, **sem revelar a resposta**. Se omitido, usa o início do enunciado. |
| `enunciado` | Texto da questão. Para lacuna, inclua `[[LACUNA]]` onde fica o espaço. |
| `codigo` / `linguagem` | Trecho de código exibido após o enunciado em `<pre><code>`. Tabs viram 4 espaços. |
| `imagem` | `{"url": "https://...", "alt": "descrição"}` — só URL pública. |
| `feedback_geral` | Mostrado a todos após responder (`####`). |
| `dificuldade` | `facil`, `media`, `dificil` |
| `bloom` | `lembrar`, `compreender`, `aplicar`, `analisar`, `avaliar`, `criar` |
| `tags` | Lista de tags extras. |
| `justificativa` | Só no gabarito: por que a resposta é essa. |
| `fonte` | Só no gabarito: ex. "Apostila, p. 12". |
| `formato` | Sobrescreve o formato padrão nesta questão. |
| `categoria` | Muda a categoria a partir desta questão. |

## Por tipo

**multipla_escolha** — exatamente uma com `"correta": true`. `peso` opcional em erradas para crédito parcial (ex.: 50).
```json
{"tipo": "multipla_escolha", "titulo": "Camada do TCP", "enunciado": "Em qual camada do modelo TCP/IP atua o TCP?",
 "alternativas": [
   {"texto": "Transporte", "correta": true, "feedback": "Correto."},
   {"texto": "Rede", "feedback": "Nessa camada atua o IP."},
   {"texto": "Aplicação", "feedback": "Ali ficam HTTP, DNS etc."},
   {"texto": "Enlace", "feedback": "Trata de quadros e MAC."}]}
```

**multipla_resposta** — várias `"correta": true`. Sem `peso`, o script calcula: corretas dividem +100%, erradas dividem −100% (marcar tudo = 0). Pesos manuais precisam estar na lista do Moodle (ver `sintaxe-gift.md` §6).

**verdadeiro_falso**
```json
{"tipo": "verdadeiro_falso", "enunciado": "...", "resposta": false,
 "feedback_erro": "mostrado a quem errou", "feedback_acerto": "mostrado a quem acertou"}
```

**resposta_curta** — `respostas`: lista de strings ou objetos `{"texto", "peso", "feedback"}`. Liste variantes (com/sem acento, sinônimos). `*` é curinga.

**numerica** — `respostas`: lista de `{"valor", "tolerancia", "peso", "feedback"}` ou `{"min", "max", ...}`. Números JSON (ponto decimal). `feedback_erro` opcional para qualquer outro valor. `unidade` opcional (só exibida no gabarito e na impressa; coloque-a também no enunciado).
```json
{"tipo": "numerica", "enunciado": "Resistência equivalente (Ω) de 10 Ω e 15 Ω em paralelo?",
 "respostas": [{"valor": 6, "tolerancia": 0.05}], "unidade": "Ω"}
```

**associacao** — `pares`: ≥3 `{"item", "correspondente"}`; `distratores`: lista opcional de correspondentes extras.

**lacuna** — atalho: exige `[[LACUNA]]` no enunciado e vira múltipla escolha (se tiver `alternativas`), numérica (se `respostas` tiver `valor`/`min`) ou resposta curta. Uma lacuna por questão.

**dissertativa** — `resposta_esperada` e `criterios` (lista de strings ou `{"descricao", "pontos"}`) vão só para o gabarito. `linhas` define as linhas na versão impressa (padrão 8).

**descricao** — só `enunciado` (e `titulo`). Não conta em `quantidade_esperada`.

## Execução

```bash
python3 scripts/build_gift.py spec.json --saida /mnt/user-data/outputs [--impressa] [--ext gift.txt|gift|txt]
```
Se houver erro, nada é gravado e a lista de problemas é impressa. Corrija o **spec** e rode de novo. `[AVISO PEDAGÓGICO]` não bloqueia, mas deve ser avaliado (título que entrega resposta, "todas as anteriores", correta sempre na mesma letra...).
