<p align="center">
    <img src="docs/banner/moodle_gift.png" width="900px">
</p>

<hr/>

# Moodle GIFT

Skill para o Claude gerar **provas e bancos de questões no formato GIFT** prontos para importar no Moodle, com gabarito comentado e versão impressa opcional.

O Claude elabora o conteúdo; um script em Python cuida da sintaxe (escapes, pesos, tipos) e valida o arquivo com as mesmas regras do importador oficial do Moodle antes da entrega.

## O que ela faz

- Cria questões a partir de um tema ou de um material-base (PDF, apostila, slides), citando a página de origem no gabarito.
- Tipos: múltipla escolha (uma ou várias corretas), verdadeiro/falso, resposta curta, numérica (com tolerância e crédito parcial), associação, lacuna, dissertativa e descrição.
- Feedback por alternativa e geral, categorias (`$CATEGORY`), tags de dificuldade e nível de Bloom.
- Trechos de código, fórmulas LaTeX e imagens por URL com escape correto.
- Valida e corrige arquivos `.gift` existentes que dão erro na importação.

## Arquivos gerados

| Arquivo | Para quê |
|---|---|
| `<slug>.gift.txt` | Importação no banco de questões (questões + respostas + feedback) |
| `gabarito_<slug>.md` | Gabarito comentado para o professor |
| `prova_<slug>.md` | Versão para impressão sem respostas (opcional) |

## Estrutura

```
moodle-gift/
├── SKILL.md                         instruções para o Claude
├── README.md
├── LICENSE                          Apache 2.0
├── scripts/
│   ├── build_gift.py                spec JSON → .gift.txt + gabarito + prova impressa
│   └── validate_gift.py             valida qualquer arquivo GIFT
├── references/
│   ├── sintaxe-gift.md              sintaxe completa, conferida no código do Moodle
│   ├── esquema-json.md              formato do spec usado pelo build_gift.py
│   └── elaboracao-de-itens.md       boas práticas de elaboração de questões
├── assets/
│   ├── exemplo_spec.json            spec de exemplo com todos os tipos
│   └── exemplo_todos_os_tipos.gift.txt   GIFT gerado a partir dele
└── evals/
    └── evals.json                   casos de teste da skill
```

## Instalação

### Claude.ai

1. Na seção [Releases](../../releases) deste repositório, clique em **moodle-gift.skill**
   para baixar o arquivo (ele será salvo na pasta de Downloads do seu computador).

2. Acesse [claude.ai](https://claude.ai) e clique no ícone do seu perfil
   (canto inferior esquerdo) → **Configurações**.

3. Na barra lateral, clique em **Habilidades** (ou *Skills*).

4. Clique no botão **Adicionar** → **Criar habilidade**.

5. Selecione a opção **Fazer upload de arquivo**, localize o arquivo
   `moodle-gift.skill` na sua pasta de Downloads e confirme.

6. Clique em **Salvar**. A habilidade aparecerá na sua lista de habilidades ativa.

Pronto. A partir daí, basta pedir ao Claude algo como *"cria uma prova de
[disciplina] com [N] questões para o Moodle"* — a skill é ativada automaticamente.
Você também pode invocá-la diretamente digitando `/moodle-gift` no chat.

> **Requisito de plano:** Pro, Max, Team ou Enterprise com execução de código
> habilitada.

Requisito dos scripts: Python 3.8+ (somente biblioteca padrão).

## Exemplos de pedido

```
Crie uma prova de Redes de Computadores com 15 questões sobre a camada de transporte,
nível técnico integrado, categoria "Redes/Unidade 3". Quero também a versão impressa.
```
```
Transforme a apostila em anexo em 20 questões de múltipla escolha para o Moodle,
citando a página de cada uma no gabarito.
```
```
Meu arquivo questoes.txt dá erro ao importar no Moodle. Pode verificar?
```

## Uso direto dos scripts

```bash
# gerar a partir de um spec
python3 scripts/build_gift.py assets/exemplo_spec.json --saida saida/ --impressa

# validar um arquivo GIFT qualquer
python3 scripts/validate_gift.py saida/exemplo_todos_os_tipos_de_questao_gift.gift.txt --esperado 10
```

`build_gift.py` só grava os arquivos se o spec e o GIFT gerado passarem na validação. `validate_gift.py` retorna 0 (ok), 1 (erros) ou 2 (arquivo ilegível).

## Importando no Moodle

1. Curso → **Banco de questões** → **Importar**.
2. Formato **GIFT**.
3. Marque **Obter categoria do arquivo** (o arquivo traz `$CATEGORY`).
4. Mantenha "Associar notas" em **Erro se a nota não estiver listada**.
5. Envie o `.gift.txt` e confira a pré-visualização.

Dica: importe primeiro numa categoria de teste e pré-visualize questões com código, fórmulas ou pesos parciais.

## Limitações do formato GIFT

- Não embute imagens (apenas URL pública).
- Uma lacuna por questão (várias lacunas exigem Cloze/Moodle XML).
- Não cria questões calculadas, arrastar-e-soltar nem "Informações para avaliadores".
- Diferenciação de maiúsculas em resposta curta é ajustada no Moodle após a importação.

## Licença

Copyright 2026 Vinícius Istofel Oliveira

Licenciado sob a Apache License, Version 2.0. Veja [LICENSE](LICENSE).
