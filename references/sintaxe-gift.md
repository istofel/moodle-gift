# Sintaxe GIFT — referência corrigida

Consolidada a partir da documentação oficial do Moodle (MoodleDocs "GIFT format") e **conferida no código do importador** (`question/format/gift/format.php`). Onde a documentação e o código divergem, vale o código.

Leia este arquivo quando for escrever ou editar GIFT à mão, diagnosticar erro de importação ou lidar com casos especiais (LaTeX, código, imagens, pesos). Para gerar provas novas, prefira o `build_gift.py`, que já aplica tudo isto.

## Sumário
1. Estrutura do arquivo
2. Caracteres de controle e escape
3. Tipos de questão
4. Opções: título, formato, feedback, pesos, categorias, tags
5. Como o Moodle decide o tipo (e armadilhas silenciosas)
6. Pesos aceitos
7. Casos especiais: código, LaTeX, imagens, HTML
8. Importação no Moodle
9. Correções em relação aos arquivos de exemplo antigos

---

## 1. Estrutura do arquivo

- Codificação **UTF-8 sem BOM**. BOM quebra o título da 1ª questão; "Unicode" do Bloco de Notas é UTF-16 e não funciona; ANSI corrompe acentos.
- Questões separadas por **pelo menos uma linha em branco**. **Nenhuma linha em branco dentro** de uma questão (para quebra de linha use `\n`).
- Linhas que começam com `//` (ignorando espaços) são comentários e **somem na importação** — inclusive se estiverem no meio de uma questão. Nunca quebre um trecho de código em várias linhas físicas se alguma começar com `//`.
- Dentro de uma questão, as linhas físicas são aparadas (trim) e unidas; por isso é seguro indentar as alternativas em linhas separadas.
- Cada questão tem **no máximo um** bloco `{...}`.

```
// comentário (não importado)
::Título::[html]Enunciado da questão{
	=resposta correta#feedback
	~resposta errada#feedback
	####feedback geral
}
```

## 2. Caracteres de controle e escape

Controle: `~  =  #  {  }  :` — para usá-los como texto, prefixe com `\`.

| Escrever no .gift | Moodle grava |
|---|---|
| `\~` `\=` `\#` `\{` `\}` `\:` | `~ = # { } :` |
| `\n` | quebra de linha |
| `\\` | `\` (barra literal) |

Regras práticas:
- Escape **sempre**, em título, enunciado, alternativas e feedback. O escape é removido na importação, então escapar a mais nunca atrapalha; escapar a menos quebra.
- A ordem importa ao escapar por programa: primeiro `\` → `\\`, depois os demais, por último a quebra de linha → `\n`. (É exatamente o que o exportador do Moodle faz.)
- LaTeX e sequências com barra: `\neq`, `\nabla`, `\frac` — escreva `\\neq`, `\\frac\{a\}\{b\}`. Sem dobrar a barra, `\n` de `\neq` vira quebra de linha.
- `->` **não tem escape**. Só é problema em associação (separador) e em resposta curta (faria o Moodle achar que é associação). Use `→` quando for texto.
- `%` no início de uma alternativa é lido como peso. Evite começar alternativa com `%`.

## 3. Tipos de questão

### Múltipla escolha (uma correta)
```
::Q01 - Protocolo com conexão::Qual protocolo usa handshake de 3 vias?{
	~UDP#Não estabelece conexão.
	=TCP#Correto.
	~IP#É da camada de rede.
	~ICMP#Mensagens de controle.
}
```
Precisa de **ao menos um `~`**; só com `=` a questão vira resposta curta. Crédito parcial numa errada: `~%50%Galileia#Seja mais específico.`

### Múltiplas respostas (caixas de seleção)
Nenhum `=`. Pesos positivos das corretas **somam exatamente 100%**; use pesos negativos nas erradas para quem marcar tudo não levar nota máxima.
```
::Q02 - Tipos imutáveis::Quais são imutáveis em Python?{
	~%50%tuple
	~%50%str
	~%-50%list
	~%-50%dict
}
```
Três corretas: `%33.33333%` cada (não `%33%` nem `%33.33%`).

### Verdadeiro/Falso
`{TRUE}`, `{FALSE}`, `{T}` ou `{F}` — **em maiúsculas** (`{true}` vira resposta curta). Feedback: o **primeiro** `#` é mostrado a quem **errou**, o segundo a quem **acertou**.
```
::Q03 - Busca binária::A busca binária tem complexidade O(log n).{TRUE#Revise a divisão do intervalo.#Isso.}
```
Não coloque no título algo que entregue a resposta (ex.: título "A Terra é redonda" para "A Terra é achatada. {FALSE}").

### Resposta curta
Todas as respostas com `=` (todas corretas), pesos parciais opcionais. Sem `~`.
```
::Q04 - Listar arquivos::Qual comando lista arquivos no Linux?{
	=ls
	=%50%dir#Funciona em algumas distros.
	=%0%*#Resposta esperada: ls.
}
```
- Comparação ignora maiúsculas/minúsculas por padrão. Para diferenciar, edite a questão no Moodle depois (não é possível via GIFT; a antiga dica de alterar `format.php` não deve ser usada).
- Acentos **não** são ignorados: liste variantes (`=São Paulo =Sao Paulo`).
- `*` é **curinga**: `=*Paris*` aceita qualquer texto contendo "Paris"; `=*` sozinho aceita qualquer coisa (útil só com `%0%` para feedback genérico). Asterisco literal: `\\*`.

### Numérica
Começa com `#`. **Ponto decimal** no arquivo (o aluno pode digitar vírgula, conforme o idioma do Moodle).
```
::Q05::Valor de π com 2 casas?{#3.14:0.005}
::Q06::Valor de π?{#3.141..3.142}
::Q07 - Velocidade::150 km em 2,5 h. Velocidade em km/h?{#
	=60:0#Exato.
	=%50%60:2#Quase.
	~#Velocidade = distância ÷ tempo.
}
```
`valor:tolerância`, `mínimo..máximo`, várias respostas com `=` e pesos, e `~#texto` como feedback para qualquer outro valor. Unidades não são tratadas: informe-as no enunciado.

### Associação
Pares `=item -> correspondente`. Mínimo recomendado de 3 pares. Distratores: `= -> opção extra`. Sem feedback por par e sem pesos.
```
::Q08 - Portas::Associe serviço e porta.{
	=HTTP -> 80
	=HTTPS -> 443
	=SSH -> 22
	= -> 8080
}
```
O lado direito é gravado como texto puro (sem HTML).

### Lacuna ("missing word")
O bloco de respostas no meio da frase; o Moodle insere `_____`. Funciona com múltipla escolha, resposta curta e numérica.
```
::Q09 - Repetição::Em Python, a estrutura {=while ~for ~if} repete enquanto a condição for verdadeira.
```
Qualquer texto depois de `}` (até um ponto final) ativa o formato lacuna. **Só uma lacuna por questão**; várias lacunas exigem o tipo Cloze (Respostas embutidas), que não é GIFT.

### Dissertativa
Chaves vazias: `{}`. Aceita apenas feedback geral: `{####Critérios: ...}` (visível ao aluno na revisão).

### Descrição
Texto sem chaves. Não é pontuada; serve para instruções ou texto-base.

## 4. Opções

- **Título**: `::Título::` no início. Sem título, o Moodle usa o começo do enunciado. Títulos únicos e informativos (`Q03 - Complexidade busca binária`), sem revelar a resposta.
- **Formato do texto**: `[html]`, `[moodle]` (padrão), `[markdown]` ou `[plain]`, **depois do título e antes do enunciado**: `::Título::[html]Texto`. Alternativas e feedbacks herdam o formato. Colchete com conteúdo que não é formato (ex.: `[Enem 2020]`) fica como texto.
- **Feedback por resposta**: `#texto` após a resposta.
- **Feedback geral**: `####texto`, último item antes de `}`.
- **Categoria**: linha isolada, com linha em branco antes e depois. Na importação, marque **"Obter categoria do arquivo"**.
  ```
  $CATEGORY: Redes de Computadores/Unidade 2
  ```
  Subcategorias com `/`; categorias inexistentes são criadas. Barra literal no nome: `//`.
- **Tags e ID** (Moodle recentes): numa linha de comentário imediatamente antes da questão — `// [tag:redes] [tag:dificuldade-media] [id:RED-U2-001]`. Versões antigas ignoram o comentário. Evite `[id:]` se a questão puder ser reimportada na mesma categoria (o ID precisa ser único).

## 5. Como o Moodle decide o tipo

Ordem aplicada ao conteúdo das chaves (após remover o feedback geral):

1. Sem `{}` → **descrição**
2. `{}` vazio → **dissertativa**
3. Começa com `#` → **numérica**
4. Contém `~` → **múltipla escolha** (sem nenhum `=` → múltiplas respostas)
5. Contém `=` e `->` → **associação**
6. É `T`, `TRUE`, `F` ou `FALSE` (maiúsculas) → **verdadeiro/falso**
7. Qualquer outra coisa → **resposta curta**

Armadilhas que **não geram erro** na importação, mas criam questão errada:

| Escrito | O que acontece |
|---|---|
| `{#3,14}` | valor não numérico vira `*`: **qualquer resposta é aceita** |
| `{=42:0 =%50%41:1}` (sem `#`) | vira resposta curta com respostas "42:0" e "41:1" |
| `{true}` / `{f}` | vira resposta curta |
| `{=A =B}` querendo múltipla escolha | vira resposta curta (falta `~`) |
| `{=*}` ou `{*}` | aceita qualquer texto |
| `~%33%a ~%33%b ~%34%c` | erro "invalidgrade" (pesos fora da lista) |
| `=%50%x` em múltipla escolha | vale 100% e "%50%" aparece no texto |
| `[html]::Título::texto` | sem título; "::Título::" aparece no enunciado |
| `=x = 2` em feedback/alternativa | o `=` sem escape cria uma alternativa nova |
| `{=A->B}` resposta curta | vira associação |
| `$CATEGORY:` sem linha em branco depois | a questão seguinte vira parte do nome da categoria |

## 6. Pesos aceitos

O importador rejeita (erro `invalidgrade`) pesos fora desta lista (positivos ou negativos), com tolerância de 0,001 ponto percentual:

`100, 90, 83.33333, 80, 75, 70, 66.66667, 60, 50, 40, 33.33333, 30, 25, 20, 16.66667, 14.28571, 12.5, 11.11111, 10, 5, 0`

Divisão por número de corretas: 2 → 50 · 3 → 33.33333 · 4 → 25 · 5 → 20 · 6 → 16.66667 · 7 → 14.28571 · 8 → 12.5 · 9 → 11.11111 · 10 → 10.

## 7. Casos especiais

**Código-fonte** — use `[html]` com `<pre><code>`, entidades HTML (`&lt;` `&gt;` `&amp;`), quebras como `\n` e escape GIFT de chaves, `=`, `#`, `:`:
```
::Q10 - Saída::[html]Qual a saída?<pre><code>d \= \{"a"\: 1\}\nprint(len(d))</code></pre>{=1 ~2 ~0 ~Erro}
```

**Fórmulas (filtro MathJax/TeX)** — `\\( ... \\)` inline ou `$$ ... $$` em bloco, com chaves e `=` escapados: `$$x \= \\frac\{-b \\pm \\sqrt\{\\Delta\}\}\{2a\}$$`.

**Imagens** — GIFT não embute arquivos. Use URL pública: `[html]... <img src\="https\://exemplo.org/fig.png" alt\="Gráfico">`. Para imagens privadas, importe e depois insira a imagem pelo editor do Moodle, ou use Moodle XML.

**HTML** — só com `[html]` no início do enunciado. Em `[html]`, `<` e `&` literais precisam virar `&lt;` e `&amp;`.

## 8. Importação no Moodle

1. Curso → **Banco de questões** → **Importar**.
2. Formato **GIFT**.
3. Em "Geral": escolha a categoria padrão e marque **Obter categoria do arquivo** se o arquivo tiver `$CATEGORY`.
4. "Associar notas": mantenha **Erro se a nota não estiver listada** (detecta pesos inválidos).
5. Envie o arquivo e confira a pré-visualização da importação.

Extensão: `.txt` é sempre aceita. Algumas instalações rejeitam `.gift` por não reconhecer o tipo do arquivo; por isso a skill gera `nome.gift.txt` (mesma convenção do arquivo de teste do próprio Moodle).

Importe primeiro numa categoria de teste e pré-visualize 2–3 questões (especialmente as com código, fórmulas ou pesos).

## 9. Correções em relação aos arquivos de exemplo antigos

- `gift_question_examples.json` não era JSON válido (`\=` não é escape JSON; o correto seria `\\=`).
- Numérica com vários pesos estava sem o `#` inicial (virava resposta curta).
- `[html]` e `[markdown]` estavam antes do título; o correto é `::Título::[html]Texto`.
- `{*}` aceitava qualquer resposta (curinga).
- V/F com título que entregava a resposta.
- `{=Paris =paris}` é redundante (já ignora maiúsculas por padrão).
- A dica de editar `format.php` para diferenciar maiúsculas foi removida (altera o núcleo do Moodle).
- Um arquivo GIFT "só com perguntas, sem respostas" não serve para o banco de questões: sem respostas, tudo é importado como dissertativa ou descrição. As respostas **precisam** estar no `.gift`; a versão sem respostas é o documento impresso.
