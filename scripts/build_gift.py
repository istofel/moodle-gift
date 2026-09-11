#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_gift.py — Gera, a partir de uma especificação JSON:
  1. <slug>.gift.txt        arquivo GIFT para importar no banco de questões do Moodle
  2. gabarito_<slug>.md     gabarito comentado para o professor
  3. prova_<slug>.md        versão para impressão, sem respostas (opcional: --impressa)

O script cuida do que mais quebra importações: escape dos caracteres de
controle (~ = # { } : \\), quebras de linha, pesos percentuais aceitos pelo
Moodle, UTF-8 sem BOM e nomes de arquivo sanitizados. Ao final valida o
.gift com validate_gift.py e só grava os arquivos se não houver erros.

Uso:
    python3 build_gift.py spec.json [--saida DIR] [--impressa] [--ext gift.txt|gift|txt]

Formato da especificação: references/esquema-json.md
"""
import argparse
import html
import json
import random
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_gift as vg  # noqa: E402

MARCADOR = "[[LACUNA]]"
PESO_POR_DIVISOR = {1: 100, 2: 50, 3: 33.33333, 4: 25, 5: 20, 6: 16.66667,
                    7: 14.28571, 8: 12.5, 9: 11.11111, 10: 10}
FORMATOS = {"texto": "html", "html": "html", "markdown": "markdown",
            "moodle": "moodle", "plain": "plain"}
TIPOS = {
    "multipla_escolha": "Múltipla escolha",
    "multipla_resposta": "Múltiplas respostas",
    "verdadeiro_falso": "Verdadeiro/Falso",
    "resposta_curta": "Resposta curta",
    "numerica": "Numérica",
    "associacao": "Associação",
    "dissertativa": "Dissertativa",
    "descricao": "Descrição",
}
DIFICULDADES = {"facil": "Fácil", "media": "Média", "dificil": "Difícil"}
BLOOM = {"lembrar": "Lembrar", "compreender": "Compreender", "aplicar": "Aplicar",
         "analisar": "Analisar", "avaliar": "Avaliar", "criar": "Criar"}


class ErrosSpec(Exception):
    pass


# ---------------------------------------------------------------- utilidades
def sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def chave(s) -> str:
    return re.sub(r"[^a-z0-9]+", "_", sem_acento(str(s)).lower()).strip("_")


def slugify(s: str) -> str:
    return (re.sub(r"_+", "_", chave(s))[:60].strip("_")) or "questoes"


def esc(s: str) -> str:
    """Escape GIFT idêntico ao repchar() do exportador do Moodle."""
    s = s.replace("\\", "\\\\")
    for c in "~=#{}:":
        s = s.replace(c, "\\" + c)
    return s


def norm_nl(s: str) -> str:
    return str(s).replace("\r\n", "\n").replace("\r", "\n")


def render(texto: str, fmt: str) -> str:
    """Texto do spec -> trecho GIFT escapado, em uma única linha física."""
    t = norm_nl(texto)
    if fmt == "texto":
        t = html.escape(t, quote=False).replace("\n", "<br>")
    return esc(t).replace("\n", "\\n")


def render_simples(texto: str) -> str:
    """Para campos que o Moodle guarda como texto puro (resposta curta, lado
    direito da associação): só escape GIFT, sem HTML e sem quebra de linha."""
    return esc(" ".join(norm_nl(texto).split()))


def fmt_num(x, onde, erros):
    if isinstance(x, bool) or x is None:
        erros.append(f"{onde}: valor numérico ausente/inválido")
        return "0"
    if isinstance(x, str):
        if "," in x:
            erros.append(f"{onde}: use ponto decimal ('{x}' → '{x.replace(',', '.')}')")
            return "0"
        x = x.strip()
    try:
        d = Decimal(str(x) if not isinstance(x, float) else repr(x))
    except InvalidOperation:
        erros.append(f"{onde}: '{x}' não é número")
        return "0"
    s = format(d.normalize(), "f")
    return "0" if s in ("-0", "") else s


def fmt_peso(p: float) -> str:
    if abs(p - round(p)) < 1e-9:
        return str(int(round(p)))
    return f"{p:.5f}".rstrip("0").rstrip(".")


def peso_str(p) -> str:
    return "" if p is None else f"%{fmt_peso(p)}%"


def tag_segura(t: str) -> str:
    return re.sub(r"[\]\[<>`\x00-\x1f]", "", str(t)).strip()


def letra(i: int) -> str:
    return chr(ord("A") + i)


def md_cel(s: str, n: int = 70) -> str:
    s = " ".join(str(s).split()).replace("|", "\\|")
    return s if len(s) <= n else s[: n - 1] + "…"


# ------------------------------------------------------- blocos do enunciado
def bloco_codigo(q, fmt):
    code = norm_nl(q["codigo"]).replace("\t", "    ").strip("\n")
    lang = chave(q.get("linguagem", ""))
    if fmt in ("texto", "html"):
        cls = f' class="language-{lang}"' if lang else ""
        s = f"<pre><code{cls}>{html.escape(code, quote=False)}</code></pre>"
    elif fmt == "markdown":
        s = "\n\n" + "\n".join("    " + ln for ln in code.split("\n")) + "\n\n"
    else:
        s = "\n" + code + "\n"
    return esc(s).replace("\n", "\\n")


def bloco_imagem(q, fmt, onde, erros):
    img = q["imagem"]
    if isinstance(img, str):
        img = {"url": img}
    url, alt = str(img.get("url", "")), str(img.get("alt", ""))
    if not re.match(r"^https?://", url):
        erros.append(f"{onde}: imagem.url deve ser um endereço http(s) público "
                     "(GIFT não embute arquivos)")
    if fmt in ("texto", "html"):
        s = (f'<p><img src="{html.escape(url)}" alt="{html.escape(alt)}" '
             f'style="max-width:100%"></p>')
    elif fmt == "markdown":
        s = f"\n\n![{alt}]({url})\n\n"
    else:
        erros.append(f"{onde}: imagem exige formato texto, html ou markdown")
        return ""
    return esc(s).replace("\n", "\\n")


def montar_enunciado(q, fmt, onde, erros):
    en = str(q.get("enunciado", "")).strip()
    if not en:
        erros.append(f"{onde}: 'enunciado' vazio")
    partes = en.split(MARCADOR)
    if len(partes) > 2:
        erros.append(f"{onde}: GIFT aceita só UMA lacuna por questão "
                     "(para várias lacunas use o tipo Cloze no Moodle)")
        partes = [partes[0], " ".join(partes[1:])]
    extras = ""
    if q.get("codigo"):
        extras += bloco_codigo(q, fmt)
    if q.get("imagem"):
        extras += bloco_imagem(q, fmt, onde, erros)
    antes = render(partes[0], fmt)
    if len(partes) == 2:
        depois = render(partes[1], fmt) + extras
        if not depois.strip():
            depois = "."  # garante o formato lacuna mesmo com marcador no fim
        return antes, depois
    return antes + extras, None


# ------------------------------------------------------------- por tipo
def alt_texto(a):
    return a if isinstance(a, str) else a.get("texto", "")


def gerar_respostas(q, fmt, onde, erros):
    """Retorna (bloco_de_resposta_GIFT, resposta_para_gabarito, detalhe_md)."""
    tipo = q["tipo"]
    gf = q.get("feedback_geral")
    gf_linha = f"\t####{render(gf, fmt)}\n" if gf else ""
    gf_inline = f"####{render(gf, fmt)}" if gf else ""

    if tipo in ("multipla_escolha", "multipla_resposta"):
        alts = q.get("alternativas") or []
        if len(alts) < 2:
            erros.append(f"{onde}: precisa de ao menos 2 alternativas")
            return "{}", "", ""
        alts = [{"texto": a} if isinstance(a, str) else a for a in alts]
        corretas = [a for a in alts if a.get("correta")]
        erradas = [a for a in alts if not a.get("correta")]
        textos = [" ".join(str(a.get("texto", "")).lower().split()) for a in alts]
        if any(not t for t in textos):
            erros.append(f"{onde}: alternativa sem texto")
        if len(set(textos)) != len(textos):
            erros.append(f"{onde}: alternativas repetidas")
        linhas, det = [], []
        if tipo == "multipla_escolha":
            if len(corretas) != 1:
                erros.append(f"{onde}: múltipla escolha precisa de exatamente 1 alternativa "
                             f"com \"correta\": true (há {len(corretas)}); para várias corretas "
                             "use tipo multipla_resposta")
            for a in alts:
                p = a.get("peso")
                if not a.get("correta") and p not in (None, 0) and (not vg.peso_valido(p) or p >= 100):
                    erros.append(f"{onde}: peso {p} inválido para alternativa incorreta")
                a["_peso"] = 100 if a.get("correta") else (p or 0)
        else:
            if len(corretas) < 1 or not erradas:
                erros.append(f"{onde}: multipla_resposta precisa de corretas e incorretas")
            nc, ne = len(corretas), len(erradas)
            if nc > 10 or ne > 10:
                erros.append(f"{onde}: no máximo 10 alternativas corretas e 10 incorretas")
            for a in alts:
                if a.get("peso") is not None:
                    a["_peso"] = float(a["peso"])
                elif a.get("correta"):
                    a["_peso"] = PESO_POR_DIVISOR.get(nc, 0)
                else:
                    a["_peso"] = -PESO_POR_DIVISOR.get(ne, 0)
                if not vg.peso_valido(a["_peso"]):
                    erros.append(f"{onde}: peso {a['_peso']:g} não é aceito pelo Moodle "
                                 "(ex.: 3 corretas = 33.33333; omita 'peso' para cálculo automático)")
            soma = sum(a["_peso"] for a in alts if a["_peso"] > 0)
            if abs(soma - 100) > 0.01:
                erros.append(f"{onde}: pesos positivos somam {soma:g}% (precisa ser 100%)")
        for i, a in enumerate(alts):
            if tipo == "multipla_escolha":
                pref = "=" if a.get("correta") else ("~" + peso_str(a["_peso"]) if a["_peso"] else "~")
            else:
                pref = "~" + peso_str(a["_peso"])
            fb = a.get("feedback")
            linhas.append(f"\t{pref}{render(a['texto'], fmt)}" + (f"#{render(fb, fmt)}" if fb else ""))
            marca = " ✅" if a.get("correta") else ""
            peso = f" ({fmt_peso(a['_peso'])}%)" if (tipo == "multipla_resposta" or
                                                     (a["_peso"] and not a.get("correta"))) else ""
            det.append(f"- {'**' if a.get('correta') else ''}{letra(i)}) {a['texto']}{marca}"
                       f"{'**' if a.get('correta') else ''}{peso}" + (f" — _{fb}_" if fb else ""))
        bloco = "{\n" + "\n".join(linhas) + "\n" + gf_linha + "}"
        resp = ", ".join(f"{letra(i)}) {a['texto']}" for i, a in enumerate(alts) if a.get("correta"))
        return bloco, resp, "**Alternativas:**\n" + "\n".join(det)

    if tipo == "verdadeiro_falso":
        r = q.get("resposta")
        if not isinstance(r, bool):
            erros.append(f"{onde}: 'resposta' deve ser true ou false")
            r = True
        fe, fa = q.get("feedback_erro"), q.get("feedback_acerto")
        fbs = ""
        if fe or fa:
            fbs = f"#{render(fe, fmt) if fe else ''}"
            if fa:
                fbs += f"#{render(fa, fmt)}"
        bloco = "{" + ("TRUE" if r else "FALSE") + fbs + gf_inline + "}"
        det = []
        if fa:
            det.append(f"- Feedback (acerto): _{fa}_")
        if fe:
            det.append(f"- Feedback (erro): _{fe}_")
        return bloco, "Verdadeiro" if r else "Falso", "\n".join(det)

    if tipo == "resposta_curta":
        resps = q.get("respostas") or []
        if not resps:
            erros.append(f"{onde}: 'respostas' vazio")
            return "{}", "", ""
        resps = [{"texto": r} if isinstance(r, str) else r for r in resps]
        linhas, det = [], []
        for r in resps:
            t = str(r.get("texto", "")).strip()
            p = r.get("peso", 100)
            if not t:
                erros.append(f"{onde}: resposta vazia")
            if "->" in t:
                erros.append(f"{onde}: '->' em resposta curta faria o Moodle tratá-la como "
                             "associação; use '→'")
            if t == "*" and p:
                erros.append(f"{onde}: '*' sozinho aceita qualquer resposta")
            if not vg.peso_valido(p):
                erros.append(f"{onde}: peso {p} não é aceito pelo Moodle")
            fb = r.get("feedback")
            linhas.append(f"\t={'' if p == 100 else peso_str(p)}{render_simples(t)}"
                          + (f"#{render(fb, fmt)}" if fb else ""))
            det.append(f"- `{t}`" + (f" ({fmt_peso(p)}%)" if p != 100 else "")
                       + (f" — _{fb}_" if fb else ""))
        if not any(r.get("peso", 100) == 100 for r in resps):
            erros.append(f"{onde}: nenhuma resposta vale 100%")
        bloco = "{\n" + "\n".join(linhas) + "\n" + gf_linha + "}"
        principais = [str(r.get("texto")) for r in resps if r.get("peso", 100) == 100]
        return bloco, " / ".join(principais), "**Respostas aceitas:**\n" + "\n".join(det)

    if tipo == "numerica":
        resps = q.get("respostas") or []
        if isinstance(resps, dict):
            resps = [resps]
        if not resps:
            erros.append(f"{onde}: 'respostas' vazio")
            return "{}", "", ""
        linhas, det, resumo = [], [], []
        for r in resps:
            p = r.get("peso", 100)
            if not vg.peso_valido(p) or p < 0:
                erros.append(f"{onde}: peso {p} inválido")
            if "min" in r or "max" in r:
                mn, mx = fmt_num(r.get("min"), onde, erros), fmt_num(r.get("max"), onde, erros)
                if float(mn) > float(mx):
                    erros.append(f"{onde}: min maior que max")
                val, legivel = f"{mn}..{mx}", f"entre {mn} e {mx}"
            else:
                v = fmt_num(r.get("valor"), onde, erros)
                tol = r.get("tolerancia", 0)
                ts = fmt_num(tol, onde, erros)
                if float(ts) < 0:
                    erros.append(f"{onde}: tolerância negativa")
                val = f"{v}:{ts}"
                legivel = f"{v}" + (f" ± {ts}" if float(ts) else " (exato)")
            fb = r.get("feedback")
            linhas.append(f"\t={'' if p == 100 else peso_str(p)}{val}"
                          + (f"#{render(fb, fmt)}" if fb else ""))
            det.append(f"- {legivel}" + (f" ({fmt_peso(p)}%)" if p != 100 else "")
                       + (f" — _{fb}_" if fb else ""))
            if p == 100:
                resumo.append(legivel)
        if not resumo:
            erros.append(f"{onde}: nenhuma resposta vale 100%")
        fe = q.get("feedback_erro")
        if fe:
            linhas.append(f"\t~#{render(fe, fmt)}")
            det.append(f"- Qualquer outro valor — _{fe}_")
        if q.get("unidade"):
            det.append(f"- Unidade (informada no enunciado): {q['unidade']}")
        bloco = "{#\n" + "\n".join(linhas) + "\n" + gf_linha + "}"
        return bloco, " / ".join(resumo), "**Respostas aceitas:**\n" + "\n".join(det)

    if tipo == "associacao":
        pares = q.get("pares") or []
        distr = q.get("distratores") or []
        if len(pares) < 3:
            erros.append(f"{onde}: associação precisa de ao menos 3 pares")
        linhas, det = [], []
        for pr in pares:
            item, corr = str(pr.get("item", "")).strip(), str(pr.get("correspondente", "")).strip()
            if not item or not corr:
                erros.append(f"{onde}: par com 'item' ou 'correspondente' vazio")
            if fmt != "texto" and "->" in item:
                erros.append(f"{onde}: '->' no item da associação quebra o par")
            linhas.append(f"\t={render(item, fmt)} -> {render_simples(corr)}")
            det.append(f"- {item} → **{corr}**")
        for d in distr:
            linhas.append(f"\t= -> {render_simples(d)}")
        if distr:
            det.append("- Distratores: " + ", ".join(str(d) for d in distr))
        norm = lambda x: " ".join(str(x).lower().split())
        if len({norm(p.get('correspondente', '')) for p in pares} | {norm(d) for d in distr}) \
                != len(pares) + len(distr):
            erros.append(f"{onde}: correspondentes/distratores repetidos confundem o aluno")
        bloco = "{\n" + "\n".join(linhas) + "\n" + gf_linha + "}"
        return bloco, "; ".join(f"{p.get('item')} → {p.get('correspondente')}" for p in pares), \
            "**Pares corretos:**\n" + "\n".join(det)

    if tipo == "dissertativa":
        det = []
        if q.get("resposta_esperada"):
            det.append(f"**Resposta esperada:** {q['resposta_esperada']}")
        crit = q.get("criterios") or []
        if crit:
            det.append("**Critérios de correção:**\n" + "\n".join(
                f"- {c if isinstance(c, str) else c.get('descricao', '')}"
                + ("" if isinstance(c, str) or c.get("pontos") is None else f" ({c['pontos']} pt)")
                for c in crit))
        return "{" + gf_inline + "}", "Correção manual", "\n\n".join(det)

    return "", "—", ""


# ---------------------------------------------------- avisos pedagógicos
def avisos_pedagogicos(itens):
    """Checagens que não impedem a importação, mas indicam itens fracos."""
    av = []
    posicoes = []
    proibidas = ("todas as anteriores", "nenhuma das anteriores", "todas as alternativas",
                 "nenhuma das alternativas", "todas acima", "nenhuma acima")
    for it in itens:
        q, rot = it["q"], it["rotulo"]
        tit = chave(it["titulo"].split(" - ", 1)[-1])
        if it["tipo"] in ("multipla_escolha", "multipla_resposta"):
            alts = q.get("alternativas") or []
            if it["tipo"] == "multipla_escolha" and len(alts) < 4 and MARCADOR not in q.get("enunciado", ""):
                av.append(f"{rot}: só {len(alts)} alternativas (recomendado 4 ou 5)")
            for i, a in enumerate(alts):
                txt = chave(alt_texto(a)).replace("_", " ")
                if any(p in txt for p in proibidas):
                    av.append(f"{rot}: '{alt_texto(a)}' perde o sentido quando o Moodle embaralha")
                if isinstance(a, dict) and a.get("correta"):
                    if it["tipo"] == "multipla_escolha":
                        posicoes.append(i)
                    c = chave(alt_texto(a))
                    if len(c) >= 4 and c in tit and it["tipo"] == "multipla_escolha":
                        av.append(f"{rot}: o título contém a resposta ('{alt_texto(a)}')")
        if it["tipo"] == "resposta_curta":
            for r in q.get("respostas") or []:
                c = chave(alt_texto(r) if isinstance(r, (str, dict)) else r)
                if len(c) >= 4 and c in tit:
                    av.append(f"{rot}: o título contém a resposta ('{alt_texto(r)}')")
    if len(posicoes) >= 4:
        letra_top, qtd = Counter(posicoes).most_common(1)[0]
        if qtd / len(posicoes) > 0.5:
            av.append(f"{qtd} de {len(posicoes)} múltiplas escolhas têm a correta na letra "
                      f"{letra(letra_top)} — varie a posição (conta na versão impressa)")
    return av


# ------------------------------------------------------------- montagem
def carregar_spec(caminho):
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ErrosSpec([f"JSON inválido: {e}"])


def construir(spec):
    erros = []
    qs = spec.get("questoes")
    if not isinstance(qs, list) or not qs:
        raise ErrosSpec(["'questoes' deve ser uma lista não vazia"])
    fmt_padrao = spec.get("formato", "texto")
    numerar = spec.get("numerar_titulos", True)
    auto_tags = spec.get("tags_automaticas", True)
    titulo_prova = spec.get("titulo") or spec.get("disciplina") or "Questões"

    saida = [f"// {titulo_prova}",
             f"// Gerado pela skill moodle-gift em {date.today():%d/%m/%Y}. "
             "Importar em: Banco de questões > Importar > formato GIFT.",
             ""]
    cat_atual = None
    if spec.get("categoria"):
        cat_atual = str(spec["categoria"]).strip()
        saida += [f"$CATEGORY: {cat_atual}", ""]

    itens, n, titulos = [], 0, Counter()
    for idx, q in enumerate(qs, start=1):
        tipo = chave(q.get("tipo", ""))
        if tipo == "lacuna":
            tipo = ("multipla_escolha" if q.get("alternativas") else
                    "numerica" if q.get("respostas") and isinstance(q["respostas"], list)
                    and isinstance(q["respostas"][0], dict) and ("valor" in q["respostas"][0]
                                                                or "min" in q["respostas"][0])
                    else "resposta_curta")
            if MARCADOR not in str(q.get("enunciado", "")):
                erros.append(f"questão {idx}: tipo lacuna exige o marcador {MARCADOR} no enunciado")
        q["tipo"] = tipo
        if tipo not in TIPOS:
            erros.append(f"questão {idx}: tipo '{q.get('tipo')}' desconhecido "
                         f"(use: {', '.join(TIPOS)} ou lacuna)")
            continue
        fmt = q.get("formato", fmt_padrao)
        if fmt not in FORMATOS:
            erros.append(f"questão {idx}: formato '{fmt}' inválido (use {', '.join(FORMATOS)})")
            fmt = "texto"
        dif = chave(q.get("dificuldade", "")) or None
        blm = chave(q.get("bloom", "")) or None
        if dif and dif not in DIFICULDADES:
            erros.append(f"questão {idx}: dificuldade '{dif}' (use facil, media, dificil)")
        if blm and blm not in BLOOM:
            erros.append(f"questão {idx}: bloom '{blm}' (use {', '.join(BLOOM)})")

        avaliativa = tipo != "descricao"
        if avaliativa:
            n += 1
        rotulo = f"Q{n:02d}" if avaliativa else "Descrição"
        onde = f"{rotulo} (questão {idx}, {tipo})"
        base = str(q.get("titulo") or "").strip() or \
            " ".join(str(q.get("enunciado", "")).replace(MARCADOR, "___").split())[:50]
        titulo = f"{rotulo} - {base}" if (numerar and avaliativa) else base
        titulos[titulo] += 1

        if q.get("categoria") and str(q["categoria"]).strip() != cat_atual:
            cat_atual = str(q["categoria"]).strip()
            saida += [f"$CATEGORY: {cat_atual}", ""]

        comentario = f"// {rotulo} · {TIPOS[tipo]}"
        if dif:
            comentario += f" · {DIFICULDADES.get(dif, dif)}"
        if blm:
            comentario += f" · {BLOOM.get(blm, blm)}"
        tags = [tag_segura(t) for t in q.get("tags", []) if tag_segura(t)]
        if auto_tags:
            tags += [f"dificuldade-{dif}"] if dif else []
            tags += [f"bloom-{blm}"] if blm else []
        linhas_q = [comentario]
        if tags:
            linhas_q.append("// " + " ".join(f"[tag:{t}]" for t in dict.fromkeys(tags)))

        antes, depois = montar_enunciado(q, fmt, onde, erros)
        tag_fmt = f"[{FORMATOS[fmt]}]"
        cab = f"::{esc(titulo)}::{tag_fmt}{antes}"
        if tipo == "descricao":
            if depois is not None:
                erros.append(f"{onde}: descrição não pode ter lacuna")
            linhas_q.append(cab)
            resp, det = "—", ""
        else:
            if depois is not None and tipo in ("associacao", "dissertativa", "multipla_resposta"):
                erros.append(f"{onde}: lacuna não se aplica ao tipo {tipo}")
            bloco, resp, det = gerar_respostas(q, fmt, onde, erros)
            linhas_q.append(cab + bloco + (depois or ""))
        saida += linhas_q + [""]
        itens.append({"q": q, "rotulo": rotulo, "titulo": titulo, "tipo": tipo, "dif": dif,
                      "blm": blm, "resp": resp, "det": det, "fmt": fmt})

    for t, c in titulos.items():
        if c > 1:
            erros.append(f"título repetido: '{t}'")
    spec["_avisos"] = avisos_pedagogicos(itens)
    esp = spec.get("quantidade_esperada")
    if esp is not None and esp != n:
        erros.append(f"quantidade_esperada = {esp}, mas o spec tem {n} questões avaliativas")
    if erros:
        raise ErrosSpec(erros)
    return "\n".join(saida).rstrip("\n") + "\n", itens, n


def gerar_gabarito(spec, itens, n, nome_gift):
    titulo = spec.get("titulo") or spec.get("disciplina") or "Questões"
    L = [f"# Gabarito — {titulo}", ""]
    meta = []
    if spec.get("disciplina"):
        meta.append(f"**Disciplina:** {spec['disciplina']}")
    if spec.get("publico"):
        meta.append(f"**Público:** {spec['publico']}")
    meta += [f"**Questões:** {n}", f"**Arquivo de importação:** `{nome_gift}`",
             f"**Gerado em:** {date.today():%d/%m/%Y}"]
    L.append(" · ".join(meta))
    if spec.get("categoria"):
        L.append(f"\n**Categoria no Moodle:** `{spec['categoria']}`")
    L += ["", "> Documento do professor. O Moodle pode embaralhar as alternativas; "
          "as letras abaixo seguem a ordem do arquivo.", "", "## Resumo", "",
          "| Nº | Tipo | Dificuldade | Bloom | Resposta |", "|---|---|---|---|---|"]
    for it in itens:
        if it["tipo"] == "descricao":
            continue
        L.append(f"| {it['rotulo']} | {TIPOS[it['tipo']]} | {DIFICULDADES.get(it['dif'], '—')} | "
                 f"{BLOOM.get(it['blm'], '—')} | {md_cel(it['resp'])} |")
    av = [i for i in itens if i["tipo"] != "descricao"]
    dist = lambda k, nomes: " · ".join(f"{nomes.get(a, a)}: {b}" for a, b in
                                       Counter(i[k] for i in av if i[k]).items())
    L += ["", "**Distribuição** — Tipos: " + " · ".join(
        f"{TIPOS[a]}: {b}" for a, b in Counter(i["tipo"] for i in av).items())]
    if dist("dif", DIFICULDADES):
        L.append(f"· Dificuldade: {dist('dif', DIFICULDADES)}")
    if dist("blm", BLOOM):
        L.append(f"· Bloom: {dist('blm', BLOOM)}")
    L += ["", "## Questões comentadas", ""]
    for it in itens:
        q = it["q"]
        L.append(f"### {it['titulo']}")
        info = [TIPOS[it["tipo"]]] + ([DIFICULDADES[it["dif"]]] if it["dif"] in DIFICULDADES else []) \
            + ([BLOOM[it["blm"]]] if it["blm"] in BLOOM else [])
        linha = "_" + " · ".join(info) + "_"
        if q.get("fonte"):
            linha += f" · Fonte: {q['fonte']}"
        L += [linha, "", "**Enunciado:** " + str(q.get("enunciado", "")).replace(MARCADOR, "_____")]
        if q.get("codigo"):
            L += ["", f"```{q.get('linguagem', '')}", norm_nl(q["codigo"]).strip("\n"), "```"]
        if q.get("imagem"):
            url = q["imagem"] if isinstance(q["imagem"], str) else q["imagem"].get("url")
            L.append(f"\n_Imagem:_ {url}")
        if it["det"]:
            L += ["", it["det"]]
        if it["tipo"] != "descricao":
            L += ["", f"**Resposta:** {it['resp']}"]
        if q.get("justificativa"):
            L += ["", f"**Justificativa:** {q['justificativa']}"]
        if q.get("feedback_geral"):
            L += ["", f"**Feedback geral (visível no Moodle):** {q['feedback_geral']}"]
        L += ["", "---", ""]
    return "\n".join(L).rstrip("\n-") + "\n"


def gerar_impressa(spec, itens, seed):
    rnd = random.Random(seed)
    titulo = spec.get("titulo") or spec.get("disciplina") or "Avaliação"
    L = [f"# {titulo}", ""]
    if spec.get("disciplina"):
        L += [f"**Disciplina:** {spec['disciplina']}", ""]
    L += ["**Nome:** ______________________________________ **Turma:** ________ "
          "**Data:** ____/____/______", ""]
    if spec.get("instrucoes"):
        L += [f"> {spec['instrucoes']}", ""]
    L += ["---", ""]
    num = 0
    for it in itens:
        q, tipo = it["q"], it["tipo"]
        en = str(q.get("enunciado", "")).replace(MARCADOR, "_______________")
        if tipo == "descricao":
            L += [f"_{en}_", ""]
            continue
        num += 1
        extra = " _(marque todas as corretas)_" if tipo == "multipla_resposta" else ""
        L += [f"**{num}.** {en}{extra}", ""]
        if q.get("codigo"):
            L += [f"```{q.get('linguagem', '')}", norm_nl(q["codigo"]).strip("\n"), "```", ""]
        if q.get("imagem"):
            url = q["imagem"] if isinstance(q["imagem"], str) else q["imagem"].get("url")
            L += [f"![imagem]({url})", ""]
        if tipo in ("multipla_escolha", "multipla_resposta"):
            for i, a in enumerate(q["alternativas"]):
                L.append(f"{letra(i).lower()}) {alt_texto(a)}  ")
            L.append("")
        elif tipo == "verdadeiro_falso":
            L += ["( ) Verdadeiro   ( ) Falso", ""]
        elif tipo in ("resposta_curta", "numerica"):
            if MARCADOR not in str(q.get("enunciado", "")):
                un = f" {q['unidade']}" if q.get("unidade") else ""
                L += [f"Resposta: ______________________________{un}", ""]
        elif tipo == "associacao":
            direita = [p["correspondente"] for p in q["pares"]] + list(q.get("distratores") or [])
            rnd.shuffle(direita)
            L += ["| Coluna 1 | Coluna 2 |", "|---|---|"]
            for i in range(max(len(q["pares"]), len(direita))):
                esq = f"{i + 1}. {q['pares'][i]['item']}" if i < len(q["pares"]) else ""
                dir_ = f"( ) {direita[i]}" if i < len(direita) else ""
                L.append(f"| {md_cel(esq, 200)} | {md_cel(dir_, 200)} |")
            L.append("")
        elif tipo == "dissertativa":
            L += ["\n".join(["_" * 90] * int(q.get("linhas", 8))), ""]
    return "\n".join(L).rstrip("\n") + "\n"


def main():
    ap = argparse.ArgumentParser(description="Gera GIFT + gabarito a partir de spec JSON.")
    ap.add_argument("spec")
    ap.add_argument("--saida", default=".", help="pasta de saída (padrão: atual)")
    ap.add_argument("--impressa", action="store_true", help="gera também prova_<slug>.md")
    ap.add_argument("--ext", default="gift.txt", choices=["gift.txt", "gift", "txt"],
                    help="extensão do arquivo de importação (padrão: gift.txt)")
    args = ap.parse_args()

    try:
        spec = carregar_spec(args.spec)
        conteudo, itens, n = construir(spec)
    except ErrosSpec as e:
        print("Spec com problemas — nada foi gravado:")
        for m in e.args[0]:
            print(f"  [ERRO] {m}")
        sys.exit(1)

    rel = vg.validar_texto(conteudo)
    print(vg.formatar_relatorio(rel, spec.get("quantidade_esperada")))
    for a in spec.get("_avisos", []):
        print(f"[AVISO PEDAGÓGICO] {a}")
    if rel.erros:
        print("\nO .gift gerado não passou na validação — nada foi gravado.")
        sys.exit(1)

    slug = slugify(spec.get("slug") or spec.get("titulo") or spec.get("disciplina") or "questoes")
    pasta = Path(args.saida)
    pasta.mkdir(parents=True, exist_ok=True)
    nome_gift = f"{slug}.{args.ext}"
    arquivos = [pasta / nome_gift, pasta / f"gabarito_{slug}.md"]
    arquivos[0].write_bytes(conteudo.encode("utf-8"))  # UTF-8 sem BOM, LF
    arquivos[1].write_text(gerar_gabarito(spec, itens, n, nome_gift), encoding="utf-8")
    if args.impressa:
        arquivos.append(pasta / f"prova_{slug}.md")
        arquivos[2].write_text(gerar_impressa(spec, itens, slug), encoding="utf-8")
    print("\nArquivos gravados:")
    for a in arquivos:
        print(f"  {a}")


if __name__ == "__main__":
    main()
