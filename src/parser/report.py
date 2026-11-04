"""Tabela síntese e relatório de erros da análise sintática."""
import glob
import io
import os
import re
import json
from contextlib import redirect_stdout

from parser.parser import parse

LEX_ERR = re.compile(r"Erro léxico na linha (\d+), coluna (\d+): (.*?)(?: Sugestão: (.*))?$")


def arquivos_tonto(entradas):
    achados = []
    for e in entradas:
        if os.path.isdir(e):
            achados += glob.glob(os.path.join(e, "**", "*.tonto"), recursive=True)
        else:
            achados.append(e)
    return sorted(achados)


def analisar_texto(fonte, nome="<texto>"):
    buf = io.StringIO()
    with redirect_stdout(buf):  # o lexer imprime os erros dele em stdout
        resultado, erros = parse(fonte)
    lex = []
    for linha in buf.getvalue().splitlines():
        m = LEX_ERR.match(linha.strip())
        if m:
            lex.append({"line": int(m[1]), "column": int(m[2]), "message": m[3].strip(),
                        "suggestion": m[4] or "Verifique a convenção de nomes."})
    return {"arquivo": nome, "resultado": resultado, "erros_lexicos": lex, "erros_sintaticos": erros}


def analisar_arquivo(caminho):
    with open(caminho, encoding="utf-8") as f:
        return analisar_texto(f.read(), caminho)


def tabela_sintese(analises):
    L = ["=== TABELA SÍNTESE ==="]
    total = dict.fromkeys(["classes", "rel_int", "rel_ext", "datatypes", "enums", "gensets"], 0)
    pacotes = set()
    for a in analises:
        r = a["resultado"]
        if not r:
            continue
        pacotes.add(r["package"]["name"])
        rels_int = [(c["name"], m) for c in r["classes"] for m in c["attributes"]
                    if m.get("kind") == "relation"]
        rels_ext = [x for x in r["relations"] if not x["internal"]]
        L.append(f"\nPacote {r['package']['name']}  ({a['arquivo']})")
        L.append(f"  Classes ({len(r['classes'])}): " +
                 ", ".join(f"{c['stereotype']} {c['name']}" for c in r["classes"]))
        L.append(f"  Relações internas ({len(rels_int)}): " +
                 ", ".join(f"{c}->{m['target']}" for c, m in rels_int))
        L.append(f"  Relações externas ({len(rels_ext)}): " +
                 ", ".join(f"{x['source']}->{x['target']}" for x in rels_ext))
        L.append(f"  Datatypes ({len(r['datatypes'])}): " + ", ".join(d["name"] for d in r["datatypes"]))
        L.append(f"  Enums ({len(r['enums'])}): " + ", ".join(e["name"] for e in r["enums"]))
        L.append(f"  Gensets ({len(r['gensets'])}): " + ", ".join(g["name"] for g in r["gensets"]))
        for k, v in (("classes", r["classes"]), ("rel_int", rels_int), ("rel_ext", rels_ext),
                     ("datatypes", r["datatypes"]), ("enums", r["enums"]), ("gensets", r["gensets"])):
            total[k] += len(v)
    L.append(f"\nTOTAL: {len(pacotes)} pacote(s), {total['classes']} classe(s), "
             f"{total['rel_int']} relação(ões) interna(s), {total['rel_ext']} externa(s), "
             f"{total['datatypes']} datatype(s), {total['enums']} enum(s), {total['gensets']} genset(s)")
    return "\n".join(L)


def relatorio_erros(analises):
    L = ["=== RELATÓRIO DE ERROS ==="]
    n = 0
    for a in analises:
        erros = [("léxico", e) for e in a["erros_lexicos"]] + \
                [("sintático", e) for e in a["erros_sintaticos"]]
        if not erros:
            continue
        L.append(f"\n{a['arquivo']}")
        for tipo, e in sorted(erros, key=lambda x: x[1]["line"]):
            n += 1
            col = f":{e['column']}" if e.get("column") else ""
            L.append(f"  [{tipo}] linha {e['line']}{col} - {e['message']}")
            L.append(f"      Sugestão: {e['suggestion']}")
    L.insert(1, f"Total: {n} erro(s)" if n else "Nenhum erro encontrado.")
    return "\n".join(L)

def para_json(analises):
    arquivos = []
    for a in analises:
        r = a["resultado"]
        item = {
            "arquivo": a["arquivo"],
            "erros_lexicos": a["erros_lexicos"],
            "erros_sintaticos": a["erros_sintaticos"],
        }
        if r:
            item.update({
                "pacote": r["package"]["name"],
                "imports": [i["name"] for i in r["imports"]],
                "classes": [
                    {"nome": c["name"], "estereotipo": c["stereotype"], "pai": c["parent"],
                     "relacoes_internas": [m for m in c["attributes"] if m.get("kind") == "relation"]}
                    for c in r["classes"]
                ],
                "relacoes_externas": [x for x in r["relations"] if not x["internal"]],
                "datatypes": [d["name"] for d in r["datatypes"]],
                "enums": [{"nome": e["name"], "individuos": e["individuals"]} for e in r["enums"]],
                "gensets": r["gensets"],
            })
        arquivos.append(item)
    return json.dumps({"arquivos": arquivos}, ensure_ascii=False, indent=2)