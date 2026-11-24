"""Estabilidade do LDA: ajusta cada k com 10 sementes e mede quanto os tópicos se repetem (similaridade de cosseno)."""
import numpy as np
from hdb.cli import _banco
from hdb import config, topicos as T
docs = [d for d in _banco().anuncios_do_corpus(config.VERSAO_CORPUS) if d["texto_padrao"].strip()]
textos = [d["texto_padrao"] for d in docs]
SEMENTES = range(10)
def cos(a, b):
    a = a / np.linalg.norm(a, axis=1, keepdims=True); b = b / np.linalg.norm(b, axis=1, keepdims=True)
    return a @ b.T
print(f"{len(docs)} anúncios; 10 sementes por k\n")
print("k | perplexidade média | estabilidade (similaridade média do melhor par, vs semente 0) | tópicos com sim>=0,8")
res = {}
for k in (4, 6, 8, 10, 12):
    comp, perp = [], []
    for s in SEMENTES:
        m, v, X = T.ajustar(textos, k, s)
        perp.append(m.perplexity(X)); comp.append(m.components_ / m.components_.sum(1, keepdims=True))
    base = comp[0]
    sims = []; bons = []
    for c in comp[1:]:
        best = cos(base, c).max(axis=1)   # melhor par para cada tópico da semente 0
        sims.append(best.mean()); bons.append((best >= 0.8).mean())
    res[k] = (comp, v)
    print(f"{k:2d} | {np.mean(perp):7.1f} | {np.mean(sims):.2f} (min {np.min(sims):.2f}) | {np.mean(bons)*100:3.0f}%")
# tópicos da semente 0 mais estáveis/instáveis em k=8
comp, v = res[8]; voc = v.get_feature_names_out()
base = comp[0]
est = np.mean([cos(base, c).max(axis=1) for c in comp[1:]], axis=0)
print("\nk=8, semente 0: estabilidade de cada tópico (média nas outras 9 sementes)")
for t in np.argsort(-est):
    print(f"  tópico {t}: {est[t]:.2f}  {', '.join(voc[j] for j in np.argsort(-base[t])[:8])}")
