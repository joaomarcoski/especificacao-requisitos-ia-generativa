# Mede quanto do texto de cada cenário está presente nos trechos recuperados (contexto do RAGAS).
# Cobertura = proporção das sequências de 6 palavras do cenário encontradas nos trechos.
# Somente leitura, não chama a API. Uso: python cobertura_cenario_contexto.py
import glob, json, re
from pathlib import Path

PASTA = Path(__file__).resolve().parents[1] / "Execuções Oficiais"
N = 6


def toks(s):
    return re.findall(r"\w+", s.lower())


def main():
    res = []
    for f in sorted(PASTA.glob("ragas_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        cen = d["question"].split("Documento(s) de cen", 1)[1].split("\n", 1)[1]
        t = toks(cen)
        grams = [tuple(t[i:i + N]) for i in range(len(t) - N + 1)]
        ctx = set()
        for c in d["contexts"]:
            u = toks(c)
            ctx |= {tuple(u[i:i + N]) for i in range(len(u) - N + 1)}
        cov = sum(g in ctx for g in grams) / len(grams)
        res.append((f.name, cov))
        print(f"{cov:.4f}  {f.name}")
    print(">=0,98:", sum(c >= 0.98 for _, c in res), "| entre 0,5 e 0,98:",
          sum(0.5 <= c < 0.98 for _, c in res), "| <0,5:", sum(c < 0.5 for _, c in res))


if __name__ == "__main__":
    main()
