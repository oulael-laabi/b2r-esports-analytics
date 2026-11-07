#!/usr/bin/env python3
"""
Convertit les scripts `# %%` (format percent) de ce dossier en vrais .ipynb,
sans dépendance (ni jupytext ni nbformat).

    python notebooks/_to_ipynb.py           # tous les p*.py
    python notebooks/_to_ipynb.py p4_player_ranking.py

Chaque bloc délimité par `# %%` devient une cellule ; `# %% [markdown]` produit
une cellule Markdown (les `#` de commentaire sont retirés).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def parse(src: str):
    cells, cur, is_md = [], [], False

    def flush():
        if cur and "".join(cur).strip():
            if is_md:
                txt = "".join(cur)
                txt = "\n".join(l[2:] if l.startswith("# ") else l[1:] if l == "#" else l
                                for l in txt.splitlines())
                cells.append(("markdown", txt.strip() + "\n"))
            else:
                cells.append(("code", "".join(cur).strip("\n") + "\n"))
        cur.clear()

    for line in src.splitlines(keepends=True):
        s = line.strip()
        if s.startswith("# %%"):
            flush()
            is_md = "[markdown]" in s
        else:
            cur.append(line)
    flush()
    return cells


def to_nb(cells):
    out = []
    for kind, text in cells:
        c = {"cell_type": kind, "metadata": {}, "source": text.splitlines(keepends=True)}
        if kind == "code":
            c["outputs"] = []
            c["execution_count"] = None
        out.append(c)
    return {
        "cells": out,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                    "name": "python3"},
                     "language_info": {"name": "python"}},
        "nbformat": 4, "nbformat_minor": 5,
    }


def main():
    targets = sys.argv[1:] or [p.name for p in sorted(HERE.glob("p*.py"))]
    for name in targets:
        src = (HERE / name).read_text(encoding="utf-8")
        nb = to_nb(parse(src))
        dest = HERE / (Path(name).stem + ".ipynb")
        dest.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{name} -> {dest.name}  ({len(nb['cells'])} cellules)")


if __name__ == "__main__":
    main()
