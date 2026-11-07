# %% [markdown]
# # P7 — Studio + Data Sync
# **Ref :** B2R-STU-2026-IPD-01
#
# Pipeline d'export média : les 4 vues SQL Studio → un JSON structuré unique.
# KPI : export instantané (vs recherche manuelle).
#
# En base MySQL : lit directement les vues `v_*`.
# En fallback CSV (Colab) : recalcule l'équivalent depuis les tables + le
# classement P4.

# %%
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path.cwd().parent / "scripts"))
import b2r_common as b2r

DATE = "2026-06-28"

# %% [markdown]
# ## 1. Construction des 4 vues (base ou recalcul)

# %%
eng = b2r.get_engine()

if eng is not None:
    v_potw = pd.read_sql("SELECT * FROM v_player_of_the_week", eng)
    v_top = pd.read_sql("SELECT * FROM v_top_performers", eng)
    v_high = pd.read_sql("SELECT * FROM v_match_highlights", eng)
    v_mom = pd.read_sql("SELECT * FROM v_team_momentum", eng)
else:
    print("Mode CSV : recalcul des vues depuis les tables + ranking P4")
    logs = b2r.load_table("logs_performance")
    logs["date_log"] = pd.to_datetime(logs["date_log"])
    dim = b2r.player_dim()
    rank = b2r.read_export("B2R_Player_Ranking")
    tele = b2r.read_export("match_analysis_details")

    # v_player_of_the_week : meilleur score_perf sur les 7 derniers jours
    fin = logs.date_log.max()
    w = logs[logs.date_log > fin - pd.Timedelta(days=7)].groupby("joueur_id").agg(
        score_semaine=("score_perf", "mean"), kda_moyen=("kda", "mean"),
        precision_moyenne=("precision_tirs", "mean"),
        total_victoires=("nb_victoires", "sum"), total_parties=("nb_parties", "sum"),
        humeur_moy=("humeur", "mean"), focus_moy=("focus", "mean")).reset_index()
    w = w.merge(dim[["joueur_id", "tag_ingame", "role_tactique", "equipe"]], on="joueur_id")
    w["winrate_pct"] = (w.total_victoires / w.total_parties * 100).round(1)
    v_potw = w.sort_values("score_semaine", ascending=False).head(1).round(2)

    # v_top_performers
    best = tele.groupby("joueur_id").agg(best_kills=("kills", "max"),
                                         best_precision=("precision_tirs_match", "max")).reset_index()
    v_top = (rank.merge(best, on="joueur_id", how="left")
             .rename(columns={"RANK": "classement"})
             .sort_values("classement"))

    # v_match_highlights
    h = tele.copy()
    h["kda_match"] = ((h.kills + h.assists) / np.maximum(h.deaths, 1)).round(2)
    h["tag_contenu"] = np.select(
        [h.kills >= 25, h.precision_tirs_match >= 83, h.objectifs_captures >= 5],
        ["HIGHLIGHT - Carry performance", "HIGHLIGHT - Precision record",
         "HIGHLIGHT - Objectifs domination"], default="Performance standard")
    v_high = h.sort_values(["kills", "precision_tirs_match"], ascending=False)

    # v_team_momentum
    m = rank.merge(dim[["joueur_id", "equipe"]], on="joueur_id").groupby("equipe").agg(
        nb_joueurs_actifs=("joueur_id", "nunique"),
        score_equipe_moyen=("B2R_SCORE", "mean"),
        winrate_equipe=("winrate_pct", "mean"),
        kda_equipe=("kda_moyen", "mean"),
        bien_etre_moyen=("score_psycho", "mean")).round(2).reset_index()
    m["recommandation_studio"] = np.select(
        [m.score_equipe_moyen >= 55, m.score_equipe_moyen >= 45],
        ["En forme - Bon moment pour communiquer", "Stable - Performance normale"],
        default="En difficulte - Privilegier le discret")
    v_mom = m.sort_values("score_equipe_moyen", ascending=False)

print(f"Player of the Week : {v_potw.tag_ingame.iloc[0]}")
print(f"Top performers     : {len(v_top)}")
print(f"Highlights taggés  : {(v_high.tag_contenu != 'Performance standard').sum()}")
print(f"Équipes            : {len(v_mom)}")

# %% [markdown]
# ## 2. Assemblage du JSON

# %%
def clean(d):
    return {k: (None if (isinstance(v, float) and np.isnan(v)) else
                v.item() if hasattr(v, "item") else v) for k, v in d.items()}


payload = {
    "meta": {
        "source": "B2R Esports Intelligence Platform",
        "document_ref": "B2R-STU-2026-IPD-01",
        "date_export": DATE,
        "version": "P7-2.0",
        "confidentiel": True,
    },
    "player_of_the_week": clean(v_potw.iloc[0].to_dict()) if len(v_potw) else {},
    "top_performers": [clean(r) for r in v_top.to_dict("records")],
    "match_highlights": [clean(r) for r in
                         v_high[v_high.tag_contenu != "Performance standard"]
                         .head(20).to_dict("records")],
    "team_momentum": [clean(r) for r in v_mom.to_dict("records")],
}

# %% [markdown]
# ## 3. Export JSON + CSV des vues

# %%
out = b2r.OUTPUTS / "studio" / f"B2R_Studio_Export_{DATE}.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

for name, df in [("v_player_of_the_week", v_potw), ("v_top_performers", v_top),
                 ("v_match_highlights", v_high), ("v_team_momentum", v_mom)]:
    b2r.write_export(df, name)

print(f"→ {out}")
print("→ data/exports/v_*.csv")
print("\nAperçu Player of the Week :")
print(json.dumps(payload["player_of_the_week"], ensure_ascii=False, indent=2, default=str))
print(f"\n{len(payload['match_highlights'])} highlights, "
      f"{len(payload['team_momentum'])} équipes exportés.")
