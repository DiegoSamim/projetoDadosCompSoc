from pathlib import Path
import sys, nbformat
from nbclient import NotebookClient
caminho = sys.argv[1]
nb = nbformat.read(caminho, as_version=4)
NotebookClient(nb, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(Path(__file__).resolve().parents[2] / "notebooks")}}).execute()
nbformat.write(nb, caminho)
for i, c in enumerate(nb.cells):
    if c.cell_type == "code":
        for o in c.outputs:
            t = o.get("text") or o.get("data", {}).get("text/plain", "") if o.output_type != "error" else "ERRO " + o.get("ename","") + o.get("evalue","")
            if t: print(f"[{i}]", t[:1500])
