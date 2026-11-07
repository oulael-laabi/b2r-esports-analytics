# %% [markdown]
# # P5 — Coach Feedback Analytics
# **Ref :** B2R-STU-2026-IPD-01
#
# Agrège les évaluations coach, les croise avec la performance réelle, et
# catégorise les commentaires. KPI : pipeline d'agrégation + cross-tabulation.
#
# **Changement vs v1** : `coherence_score` compare maintenant l'évaluation coach
# et le B2R_SCORE **sur la même échelle** (rangs normalisés 0–1), au lieu de
# mélanger une note /10 et un score /100.

# %%
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path.cwd().parent / "scripts"))
import b2r_common as b2r

# %% [markdown]
# ## 1. Chargement

# %%
ev = b2r.load_table("evaluations_coach")
dim = b2r.player_dim()[["joueur_id", "tag_ingame", "role_tactique"]]
ev = ev.merge(dim, on="joueur_id", how="left")
ev["score_calcule"] = np.round(
    ev[["discipline", "communication", "execution_mecanique", "vitesse_adaptation"]].mean(axis=1), 2)
print(f"{len(ev)} évaluations — {ev.evaluateur.nunique()} évaluateurs, {ev.joueur_id.nunique()} joueurs")
ev.head()

# %% [markdown]
# ## 2. Agrégation par joueur

# %%
agg = ev.groupby(["joueur_id", "tag_ingame"]).agg(
    nb_evals=("eval_id", "count"),
    discipline_moy=("discipline", "mean"),
    communication_moy=("communication", "mean"),
    execution_mec_moy=("execution_mecanique", "mean"),
    adaptation_moy=("vitesse_adaptation", "mean"),
    score_coach_moyen=("score_global", "mean"),
    score_coach_min=("score_global", "min"),
    score_coach_max=("score_global", "max"),
).round(2).reset_index()
agg.sort_values("score_coach_moyen", ascending=False)

# %% [markdown]
# ## 3. Cross-tabulation évaluateur × joueur

# %%
cross = ev.pivot_table(values="score_global", index="evaluateur",
                       columns="tag_ingame", aggfunc="mean").round(2)
cross["_moyenne_evaluateur"] = cross.mean(axis=1).round(2)
cross

# %% [markdown]
# ## 4. Catégorisation des commentaires (mots-clés, insensible aux accents)

# %%
CATEGORIES = {
    "Performance technique": ["precision", "mecanique", "execution", "kda", "kills", "aim", "duel"],
    "Mental / Regularite":  ["regularite", "stabilite", "instable", "constance", "fatigue", "stress", "focus"],
    "Leadership":           ["leader", "leadership", "vision", "communication", "call", "shotcaller", "equipe"],
    "Progression":          ["progression", "ameliorer", "amelioration", "efforts", "assiduite", "routine", "vod"],
    "Point positif":        ["excellent", "tres bon", "fiable", "impact", "naturel", "au-dessus"],
}


def _norm(txt):
    txt = unicodedata.normalize("NFKD", str(txt)).encode("ascii", "ignore").decode().lower()
    return txt


def categoriser(txt):
    if pd.isna(txt):
        return "Non categorise"
    t = _norm(txt)
    found = [cat for cat, kws in CATEGORIES.items() if any(k in t for k in kws)]
    return " | ".join(found) if found else "Autre"


ev["categories"] = ev.commentaire.apply(categoriser)
freq = (ev.categories.str.split(" | ", regex=False).explode()
        .value_counts())
print("Fréquence des catégories de feedback :")
print(freq.to_string())
ev[["tag_ingame", "evaluateur", "periode", "commentaire", "categories"]].head(10)

# %% [markdown]
# ## 5. Croisement évaluation coach vs performance réelle (même échelle)

# %%
perf = b2r.read_export("match_analysis_stats")[
    ["joueur_id", "kda_moyen", "winrate_pct", "precision_moyenne"]]
rank = b2r.read_export("B2R_Player_Ranking")[["joueur_id", "B2R_SCORE"]]

x = agg.merge(perf, on="joueur_id", how="left").merge(rank, on="joueur_id", how="left")

# rangs normalisés 0..1 -> comparables
x["coach_rank01"] = x.score_coach_moyen.rank(pct=True)
x["b2r_rank01"] = x.B2R_SCORE.rank(pct=True)
x["coherence_ecart"] = (x.coach_rank01 - x.b2r_rank01).abs().round(2)
x["alignement"] = np.where(x.coherence_ecart < 0.20, "Aligné",
                    np.where(x.coherence_ecart < 0.40, "Ecart modéré", "Divergent"))

print(x[["tag_ingame", "score_coach_moyen", "B2R_SCORE", "kda_moyen",
         "winrate_pct", "coherence_ecart", "alignement"]]
      .sort_values("coherence_ecart", ascending=False).to_string(index=False))

taux_align = (x.alignement != "Divergent").mean() * 100
print(f"\nÉvaluations coach alignées avec la performance mesurée : {taux_align:.0f} %")

# %% [markdown]
# ## 6. Export

# %%
b2r.write_export(agg, "coach_feedback_vs_performance")
b2r.write_export(cross.reset_index(), "coach_crosstab")
b2r.write_export(ev, "coach_feedback_details")
b2r.write_export(x, "coach_coherence")
print("→ data/exports/coach_*.csv")
