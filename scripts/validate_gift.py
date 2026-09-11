#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_gift.py — Valida um arquivo GIFT antes da importação no Moodle.

Replica a lógica do importador oficial (question/format/gift/format.php):
separação de blocos por linha em branco, escapes, título, detecção do tipo
de questão e regras de pesos. Também aponta armadilhas que o Moodle aceita
em silêncio mas que geram questões erradas (ex.: {#3,14} aceita qualquer
resposta; {true} minúsculo vira resposta curta).

Uso:
    python3 validate_gift.py arquivo.gift.txt [--esperado N] [--quiet]

Saída: 0 = sem erros | 1 = há erros | 2 = arquivo ilegível
"""
import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# Pesos aceitos pelo Moodle (question_bank::fraction_options_full), em %.
PESOS_VALIDOS = [100, 90, 83.33333, 80, 75, 70, 66.66667, 60, 50, 40,
                 33.33333, 30, 25, 20, 16.66667, 14.28571, 12.5, 11.11111,
                 10, 5, 0]
# O Moodle compara frações com tolerância 0.00001 (= 0.001 em %).
TOLERANCIA_PESO = 0.001

NOMES_TIPO = {
    "multichoice": "Múltipla escolha",
    "multichoice_multi": "Múltiplas respostas",
    "truefalse": "Verdadeiro/Falso",
    "shortanswer": "Resposta curta",
    "numerical": "Numérica",
    "match": "Associação",
    "essay": "Dissertativa",
    "description": "Descrição",
}

# Placeholders em área de uso privado do Unicode (não colidem com texto real).
_PH = {":": "\ue001", "#": "\ue002", "=": "\ue003", "{": "\ue004",
       "}": "\ue005", "~": "\ue006", "n": "\ue007"}
_BS = "\ue000"
_WEIGHT_RE = re.compile(r"^%-*([0-9]{1,2})\.?([0-9]*)%")
_NUM_RE = re.compile(r"^\s*[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?\s*$")


def peso_valido(p: float) -> bool:
    return any(abs(abs(p) - v) < TOLERANCIA_PESO for v in PESOS_VALIDOS)


def escapar_pre(s: str) -> str:
    """Igual a escapedchar_pre(): troca escapes por placeholders."""
    s = s.replace("\\\\", _BS)
    for c, ph in _PH.items():
        s = s.replace("\\" + c, ph)
    return s.replace(_BS, "\\")


def escapar_pos(s: str) -> str:
    """Desfaz os placeholders (texto final como o Moodle gravaria)."""
    for c, ph in _PH.items():
        s = s.replace(ph, "\n" if c == "n" else c)
    return s


def is_numeric(s: str) -> bool:
    return bool(_NUM_RE.match(s))


@dataclass
class Questao:
    linha: int
    titulo: str
    tipo: str
    lacuna: bool = False


@dataclass
class Relatorio:
    erros: list = field(default_factory=list)
    avisos: list = field(default_factory=list)
    questoes: list = field(default_factory=list)
    categorias: list = field(default_factory=list)

    def erro(self, linha, titulo, msg):
        self.erros.append((linha, titulo, msg))

    def aviso(self, linha, titulo, msg):
        self.avisos.append((linha, titulo, msg))

    @property
    def avaliativas(self):
        return [q for q in self.questoes if q.tipo != "description"]


def _peso(resp: str):
    """Retorna (peso_em_%, resto) se a resposta começa com %n%, senão (None, resp)."""
    if _WEIGHT_RE.match(resp):
        corpo = resp[1:]
        fim = corpo.find("%")
        try:
            return float(corpo[:fim]), corpo[fim + 1:]
        except ValueError:
            return None, resp
    return None, resp


def _dividir_respostas(texto: str, sep: str):
    partes = texto.split(sep)
    if partes and partes[0].strip() == "":
        partes.pop(0)
    return [p.strip() for p in partes]


def _checar_bloco(linhas, inicio, rel: Relatorio, titulos: Counter):
    # 1. Comentários (// no início da linha) são descartados; tags ficam neles.
    conteudo = []
    for ln in linhas:
        if ln.strip().startswith("//"):
            conteudo.append(" ")
        else:
            conteudo.append(ln.strip())
    texto = "\n".join(conteudo).strip()
    if not texto:
        return

    texto = escapar_pre(texto)

    # 2. Categoria
    if texto.startswith("$CATEGORY:"):
        cat = texto[10:].strip()
        if "\n" in cat:
            rel.erro(inicio, "$CATEGORY", "a linha $CATEGORY precisa de uma linha em branco "
                     "antes e depois; o texto seguinte virou parte do nome da categoria")
        rel.categorias.append(cat.split("\n")[0])
        return

    # 3. Título
    titulo = None
    if texto.startswith("::"):
        resto = texto[2:]
        fim = resto.find("::")
        if fim == -1:
            rel.erro(inicio, "?", "título aberto com '::' e não fechado")
            return
        titulo = escapar_pos(resto[:fim]).strip()
        texto = resto[fim + 2:].strip()
    ident = titulo or escapar_pos(texto[:40]).replace("\n", " ") + "…"
    if titulo is None:
        rel.aviso(inicio, ident, "sem título (::Título::); o Moodle usará o início do enunciado")
        if "::" in texto:
            rel.aviso(inicio, ident, "'::' no meio do texto: o título deve vir ANTES do "
                      "formato, ex.: ::Título::[html]Enunciado")
    else:
        titulos[titulo] += 1
        if len(titulo) > 255:
            rel.aviso(inicio, ident, "título com mais de 255 caracteres")

    # 4. Bloco de respostas
    n_abre, n_fecha = texto.count("{"), texto.count("}")
    if n_abre == 0 and n_fecha == 0:
        rel.questoes.append(Questao(inicio, ident, "description"))
        return
    if n_abre != 1 or n_fecha != 1:
        rel.erro(inicio, ident, f"{n_abre} '{{' e {n_fecha} '}}' sem escape (esperado 1 de cada). "
                 "Causas comuns: linha em branco dentro da questão, chave em código/LaTeX "
                 "sem '\\', ou duas lacunas na mesma questão (GIFT só aceita uma)")
        return
    a, f = texto.find("{"), texto.find("}")
    if f < a:
        rel.erro(inicio, ident, "'}' aparece antes de '{'")
        return
    enunciado = texto[:a].strip()
    depois = texto[f + 1:].strip()
    resp = texto[a + 1:f].strip()
    lacuna = bool(depois)

    if not enunciado and not depois:
        rel.erro(inicio, ident, "enunciado vazio")

    gf = resp.rfind("####")
    if gf != -1:
        resp = resp[:gf].strip()

    # 5. Detecção de tipo (mesma ordem do Moodle)
    plano = resp.replace("\n", " ").strip()
    if plano == "":
        tipo = "essay"
        if lacuna:
            rel.aviso(inicio, ident, "texto após '{}' em dissertativa")
    elif plano[0] == "#":
        tipo = "numerical"
        _checar_numerica(plano[1:], inicio, ident, rel)
    elif "~" in plano:
        tipo = _checar_multipla(plano, inicio, ident, rel)
    elif "=" in plano and "->" in plano:
        tipo = "match"
        _checar_associacao(plano, inicio, ident, rel)
    else:
        tf = plano.split("#", 1)[0].strip() if plano.find("#") > 0 else plano
        if tf in ("T", "TRUE", "F", "FALSE"):
            tipo = "truefalse"
        else:
            tipo = "shortanswer"
            _checar_curta(plano, inicio, ident, rel)

    rel.questoes.append(Questao(inicio, ident, tipo, lacuna))


def _checar_multipla(plano, inicio, ident, rel):
    unica = "=" in plano
    respostas = _dividir_respostas(plano.replace("=", "~="), "~")
    if len(respostas) < 2:
        rel.erro(inicio, ident, "múltipla escolha precisa de ao menos 2 alternativas")
        return "multichoice"
    pesos, textos = [], []
    for r in respostas:
        if r == "":
            rel.erro(inicio, ident, "alternativa vazia (verifique '~' ou '=' duplicados)")
            continue
        if r[0] == "=":
            p, corpo = 100.0, r[1:].strip()
            if _WEIGHT_RE.match(corpo):
                rel.erro(inicio, ident, "'=%n%' em múltipla escolha vale 100% e o '%n%' vira "
                         "texto; use '~%n%' para crédito parcial")
        else:
            p, corpo = _peso(r)
            p = 0.0 if p is None else p
        txt = corpo.split("#", 1)[0].strip()
        if not txt:
            rel.erro(inicio, ident, "alternativa sem texto")
        if not peso_valido(p):
            rel.erro(inicio, ident, f"peso {p:g}% não é aceito pelo Moodle (use 100, 90, 83.33333, "
                     "80, 75, 70, 66.66667, 60, 50, 40, 33.33333, 30, 25, 20, 16.66667, 14.28571, "
                     "12.5, 11.11111, 10, 5 ou os negativos)")
        pesos.append(p)
        textos.append(escapar_pos(txt).lower())
    dup = [t for t, n in Counter(textos).items() if n > 1 and t]
    if dup:
        rel.aviso(inicio, ident, f"alternativas repetidas: {dup}")
    if unica:
        if max(pesos, default=0) != 100:
            rel.erro(inicio, ident, "nenhuma alternativa vale 100%")
        if sum(1 for p in pesos if p == 100) > 1:
            rel.aviso(inicio, ident, "mais de uma alternativa com '=' (todas valem 100%)")
        return "multichoice"
    soma = round(sum(p for p in pesos if p > 0), 2)
    if abs(soma - 100) > 0.01:
        rel.erro(inicio, ident, f"múltiplas respostas: pesos positivos somam {soma:g}% "
                 "(o Moodle exige exatamente 100%)")
    if not any(p < 0 for p in pesos):
        rel.aviso(inicio, ident, "múltiplas respostas sem peso negativo nas incorretas: "
                  "marcar todas as alternativas dá nota máxima")
    return "multichoice_multi"


def _checar_associacao(plano, inicio, ident, rel):
    pares = _dividir_respostas(plano, "=")
    com_item = 0
    for p in pares:
        if "->" not in p:
            rel.erro(inicio, ident, f"par sem '->': '{escapar_pos(p)[:40]}'")
            continue
        esq, dir_ = p.split("->", 1)
        if esq.strip():
            com_item += 1
        if not dir_.strip():
            rel.erro(inicio, ident, "par com lado direito vazio")
        if "#" in p:
            rel.aviso(inicio, ident, "associação não aceita feedback por par; '#' ficará no "
                      "texto (escape com \\#)")
    if com_item < 2 or len(pares) < 3:
        rel.erro(inicio, ident, "associação precisa de ≥2 pares e ≥3 opções no total "
                 "(recomendado: ≥3 pares)")
    elif com_item < 3:
        rel.aviso(inicio, ident, "a documentação do GIFT recomenda ao menos 3 pares")


def _checar_curta(plano, inicio, ident, rel):
    respostas = _dividir_respostas(plano, "=")
    if not respostas:
        rel.erro(inicio, ident, "resposta curta sem respostas")
        return
    pesos, textos = [], []
    for r in respostas:
        p, corpo = _peso(r)
        p = 100.0 if p is None else p
        txt = corpo.split("#", 1)[0].strip()
        if not txt:
            rel.erro(inicio, ident, "resposta vazia")
        if not peso_valido(p):
            rel.erro(inicio, ident, f"peso {p:g}% não é aceito pelo Moodle")
        if txt == "*" and p > 0:
            rel.erro(inicio, ident, "resposta '*' com crédito aceita QUALQUER texto "
                     "('*' é curinga; para asterisco literal use \\\\*)")
        pesos.append(p)
        textos.append(txt)
    if max(pesos, default=0) != 100:
        rel.erro(inicio, ident, "nenhuma resposta vale 100%")
    if all(re.fullmatch(r"-?[\d.]+\s*(:|\.\.)\s*-?[\d.]+", t) for t in textos if t):
        rel.erro(inicio, ident, "parece numérica sem '#' inicial — seria importada como "
                 "resposta curta; use {#valor:tolerância}")
    if len(textos) == 1 and textos[0].lower() in ("t", "f", "true", "false", "v", "verdadeiro", "falso"):
        rel.aviso(inicio, ident, "parece Verdadeiro/Falso: use {TRUE} ou {FALSE} em MAIÚSCULAS "
                  "(minúsculas viram resposta curta)")


def _checar_numerica(corpo, inicio, ident, rel):
    til = corpo.find("~")
    if til != -1:
        corpo = corpo[:til]
    respostas = _dividir_respostas(corpo, "=")
    if not respostas:
        rel.erro(inicio, ident, "numérica sem respostas")
        return
    pesos = []
    for r in respostas:
        p, resto = _peso(r)
        p = 100.0 if p is None else p
        if not peso_valido(p):
            rel.erro(inicio, ident, f"peso {p:g}% não é aceito pelo Moodle")
        pesos.append(p)
        val = resto.split("#", 1)[0].strip()
        if val.find("..") > 0:
            nums = [x.strip() for x in val.split("..", 1)]
        elif val.find(":") > 0:
            nums = [x.strip() for x in val.split(":", 1)]
        else:
            nums = [val]
        for n in nums:
            if not is_numeric(n):
                extra = (" — vírgula decimal: o Moodle NÃO acusa erro e passa a aceitar "
                         "QUALQUER resposta; use ponto (3.14)") if "," in n else ""
                rel.erro(inicio, ident, f"valor numérico inválido '{escapar_pos(n)}'{extra}")
        if len(nums) == 2 and all(is_numeric(n) for n in nums):
            if val.find("..") > 0 and float(nums[0]) > float(nums[1]):
                rel.erro(inicio, ident, f"intervalo invertido '{val}' (use mínimo..máximo)")
            if val.find(":") > 0 and float(nums[1]) < 0:
                rel.erro(inicio, ident, "tolerância negativa")
    if max(pesos, default=0) != 100:
        rel.erro(inicio, ident, "nenhuma resposta numérica vale 100%")


def validar_texto(conteudo: str) -> Relatorio:
    rel = Relatorio()
    titulos = Counter()
    linhas = conteudo.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    bloco, inicio = [], 1
    for i, ln in enumerate(linhas + [""], start=1):
        if ln.strip() == "":
            if bloco:
                _checar_bloco(bloco, inicio, rel, titulos)
                bloco = []
        else:
            if not bloco:
                inicio = i
            bloco.append(ln)
    for t, n in titulos.items():
        if n > 1:
            rel.aviso(0, t, f"título repetido {n} vezes (dificulta localizar no banco)")
    return rel


def validar_arquivo(caminho) -> Relatorio:
    dados = Path(caminho).read_bytes()
    rel_bom = None
    if dados.startswith(b"\xef\xbb\xbf"):
        rel_bom = "arquivo com BOM UTF-8: salve como 'UTF-8 sem BOM' (o BOM quebra a 1ª questão)"
        dados = dados[3:]
    if dados.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise ValueError("arquivo em UTF-16 ('Unicode' do Bloco de Notas): salve como UTF-8")
    try:
        conteudo = dados.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"arquivo não está em UTF-8 (byte inválido na posição {e.start}); "
                         "provavelmente ANSI/Windows-1252 — converta para UTF-8") from e
    rel = validar_texto(conteudo)
    if rel_bom:
        rel.erros.insert(0, (1, "arquivo", rel_bom))
    return rel


def formatar_relatorio(rel: Relatorio, esperado=None, quiet=False) -> str:
    out = []
    cont = Counter(NOMES_TIPO[q.tipo] for q in rel.avaliativas)
    n_desc = len(rel.questoes) - len(rel.avaliativas)
    out.append(f"Questões avaliativas: {len(rel.avaliativas)}"
               + (f" (+{n_desc} descrição)" if n_desc else ""))
    if cont:
        out.append("  " + " · ".join(f"{k}: {v}" for k, v in sorted(cont.items())))
    lac = sum(1 for q in rel.questoes if q.lacuna)
    if lac:
        out.append(f"  (das quais {lac} no formato lacuna)")
    if rel.categorias:
        out.append("Categorias: " + " | ".join(rel.categorias))
    if esperado is not None and len(rel.avaliativas) != esperado:
        rel.erros.append((0, "arquivo", f"esperadas {esperado} questões avaliativas, "
                          f"encontradas {len(rel.avaliativas)}"))
    for rotulo, itens in (("ERRO", rel.erros), ("AVISO", rel.avisos)):
        if rotulo == "AVISO" and quiet:
            continue
        for linha, tit, msg in itens:
            loc = f"linha {linha}" if linha else "geral"
            out.append(f"[{rotulo}] {loc} · {tit}: {msg}")
    out.append("RESULTADO: " + ("OK — pronto para importar" if not rel.erros
                                else f"{len(rel.erros)} erro(s) — corrija antes de importar"))
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Valida arquivo GIFT para o Moodle.")
    ap.add_argument("arquivo")
    ap.add_argument("--esperado", type=int, help="nº esperado de questões avaliativas")
    ap.add_argument("--quiet", action="store_true", help="oculta avisos")
    args = ap.parse_args()
    try:
        rel = validar_arquivo(args.arquivo)
    except (OSError, ValueError) as e:
        print(f"[ERRO] {e}")
        sys.exit(2)
    print(formatar_relatorio(rel, args.esperado, args.quiet))
    sys.exit(1 if rel.erros else 0)


if __name__ == "__main__":
    main()
