# %% [markdown]
# # P3 — Match Analysis System
# **Ref :** B2R-STU-2026-IPD-01
#
# Parse la télémétrie post-match (`match_telemetry`) pour exposer les déficits
# techniques par joueur. KPI : **traitement < 5 min post-saisie**.
#
# Sorties (lues par P4 et P6) :
# `data/exports/match_analysis_stats.csv`, `match_analysis_details.csv`

# %%
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path.cwd().parent / "scripts"))
import b2r_common as b2r

# %% [markdown]
# ## 1. Chargement (base MySQL ou fallback CSV) + dimension joueur unique

# %%
t0 = time.perf_counter()
tele = b2r.load_table("match_telemetry")
dim = b2r.player_dim()[["joueur_id", "tag_ingame", "role_tactique", "tier"]]
tele = tele.merge(dim, on="joueur_id", how="left")
print(f"{len(tele)} matchs, {tele.joueur_id.nunique()} joueurs")
tele.head()

# %% [markdown]
# ## 2. Métriques dérivées (vectorisé NumPy)

# %%
tele["kda_match"] = np.round(
    (tele.kills + tele.assists) / np.maximum(tele.deaths, 1), 2)
tele["victoire_bin"] = (tele.resultat_match == "Victoire").astype(int)
tele["ratio_degats"] = np.round(
    tele.degats_infliges / np.maximum(tele.degats_subis, 1), 2)
# score de match pondéré B2R (identique à la v1)
tele["score_match"] = np.round(
    tele.kda_match * 0.35
    + tele.precision_tirs_match * 0.25
    + tele.ratio_degats * 0.20
    + tele.objectifs_captures * 0.20, 2)
tele[["tag_ingame", "date_match", "kda_match", "ratio_degats", "score_match"]].head()

# %% [markdown]
# ## 3. Statistiques descriptives par joueur

# %%
stats = tele.groupby(["joueur_id", "tag_ingame", "role_tactique", "tier"]).agg(
    nb_matchs=("telemetry_id", "count"),
    winrate_pct=("victoire_bin", lambda x: round(x.mean() * 100, 1)),
    kda_moyen=("kda_match", lambda x: round(x.mean(), 2)),
    kda_std=("kda_match", lambda x: round(x.std(ddof=0), 2)),
    kills_moyen=("kills", lambda x: round(x.mean(), 1)),
    deaths_moyen=("deaths", lambda x: round(x.mean(), 1)),
    precision_moyenne=("precision_tirs_match", lambda x: round(x.mean(), 1)),
    ratio_degats_moyen=("ratio_degats", lambda x: round(x.mean(), 2)),
    score_moyen=("score_match", lambda x: round(x.mean(), 2)),
    score_min=("score_match", "min"),
    score_max=("score_match", "max"),
).reset_index()
stats.sort_values("score_moyen", ascending=False)

# %% [markdown]
# ## 4. Détection des déficits techniques (seuils benchmarks B2R)

# %%
# seuil kda_std relevé (la variance KDA match-à-match est intrinsèquement élevée)
SEUILS = dict(kda=2.0, precision=65.0, winrate=50.0, ratio_degats=1.0, kda_std=1.6)

rapport = []
for _, r in stats.iterrows():
    d = []
    if r.kda_moyen < SEUILS["kda"]:
        d.append(f"KDA insuffisant ({r.kda_moyen} < {SEUILS['kda']})")
    if r.precision_moyenne < SEUILS["precision"]:
        d.append(f"Précision faible ({r.precision_moyenne}% < {SEUILS['precision']}%)")
    if r.winrate_pct < SEUILS["winrate"]:
        d.append(f"Winrate bas ({r.winrate_pct}% < {SEUILS['winrate']}%)")
    if r.ratio_degats_moyen < SEUILS["ratio_degats"]:
        d.append(f"Ratio dégâts négatif ({r.ratio_degats_moyen})")
    if r.kda_std > SEUILS["kda_std"]:
        d.append(f"Performance instable (σ KDA = {r.kda_std})")
    rapport.append({"tag_ingame": r.tag_ingame, "role": r.role_tactique,
                    "nb_deficits": len(d), "deficits": " | ".join(d) or "Aucun"})

df_deficits = pd.DataFrame(rapport)
print(df_deficits.to_string(index=False))

# %% [markdown]
# ## 5. KPI temps de traitement + export

# %%
elapsed = time.perf_counter() - t0
print(f"Temps de traitement : {elapsed:.3f} s  pour {len(tele)} matchs")
print(f"KPI (< 5 min = 300 s) : {'OK' if elapsed < 300 else 'NON ATTEINT'}")

b2r.write_export(stats, "match_analysis_stats")
b2r.write_export(tele, "match_analysis_details")
b2r.write_export(df_deficits, "match_deficits")
print("→ data/exports/match_analysis_stats.csv / match_analysis_details.csv / match_deficits.csv")
