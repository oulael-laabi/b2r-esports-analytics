# %% [markdown]
# # P4 — Player Ranking System
# **Ref :** B2R-STU-2026-IPD-01
#
# Formule de score pondéré + classement dynamique. KPI : **coefficient de
# stabilité > 0,85**.
#
# ```
# B2R_SCORE = Perf_Match × 40 + Régularité × 25 + Psychométrie × 20 + Progression × 15
# ```
# Normalisation : Z-score → sigmoïde.
#
# **Changements vs v1**
# - *Progression* = pente de régression du `score_perf` dans le temps (vraie
#   tendance), et non plus le volume d'heures d'entraînement.
# - *Coefficient de stabilité* = corrélation de Spearman entre le classement
#   calculé sur la 1ʳᵉ et la 2ᵉ moitié de la fenêtre (`b2r_common.ranking_stability`),
#   au lieu de `1 - σ/µ`.
# - Validation supplémentaire : corrélation avec le **niveau latent** ayant servi
#   à générer les données de démo.

# %%
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.append(str(Path.cwd().parent / "scripts"))
import b2r_common as b2r

# %% [markdown]
# ## 1. Chargement : stats match (P3) + logs de performance

# %%
df_match = b2r.read_export("match_analysis_stats")
df_logs = b2r.load_table("logs_performance")
dim = b2r.player_dim()
print(f"{len(df_match)} joueurs (stats match), {len(df_logs)} logs")

# %% [markdown]
# ## 2. Agrégats psychométriques + tendance (progression)

# %%
psy = df_logs.groupby("joueur_id").agg(
    humeur_moy=("humeur", "mean"),
    focus_moy=("focus", "mean"),
    fatigue_moy=("fatigue_mentale", "mean"),
    clarte_moy=("clarte_reaction", "mean"),
    heures_training_moy=("heures_training", "mean"),
    nb_jours_loggues=("log_id", "count"),
).reset_index()

# score psychométrique (bien-être mental, fatigue inversée) sur 10
psy["score_psycho"] = np.round(
    (psy.humeur_moy + psy.focus_moy + (10 - psy.fatigue_moy) + psy.clarte_moy) / 4, 2)


# progression = pente de la régression linéaire du score_perf ~ jour
def slope(g):
    g = g.sort_values("date_log")
    y = g.score_perf.to_numpy(dtype=float)
    if len(y) < 3 or np.all(np.isnan(y)):
        return 0.0
    x = np.arange(len(y))
    return float(np.polyfit(x, np.nan_to_num(y, nan=np.nanmean(y)), 1)[0])


df_logs["date_log"] = pd.to_datetime(df_logs["date_log"])
trend = (df_logs.groupby("joueur_id", group_keys=False)
         .apply(slope).rename("progression_slope").reset_index())
psy = psy.merge(trend, on="joueur_id")
psy[["joueur_id", "score_psycho", "progression_slope", "heures_training_moy"]]

# %% [markdown]
# ## 3. Fusion

# %%
# df_match (P3) porte déjà tag_ingame / role_tactique / tier ; on ajoute source_donnee
r = (df_match.merge(psy, on="joueur_id", how="left")
     .merge(dim[["joueur_id", "source_donnee"]], on="joueur_id", how="left")
     .rename(columns={"role_tactique": "role"}))
r["tier"] = r["tier"].fillna("Academy")

# %% [markdown]
# ## 4. Normalisation Z-score → sigmoïde

# %%
r["norm_perf_match"] = b2r.zscore_sigmoid(r.score_moyen)
r["norm_winrate"] = b2r.zscore_sigmoid(r.winrate_pct)
r["norm_kda"] = b2r.zscore_sigmoid(r.kda_moyen)
r["norm_precision"] = b2r.zscore_sigmoid(r.precision_moyenne)
r["norm_psycho"] = b2r.zscore_sigmoid(r.score_psycho)
r["norm_progression"] = b2r.zscore_sigmoid(r.progression_slope)
# régularité = inverse de l'instabilité KDA
r["norm_regularite"] = b2r.zscore_sigmoid(-r.kda_std)

# %% [markdown]
# ## 5. Formule B2R Score

# %%
r["perf_match_composite"] = r[["norm_perf_match", "norm_kda",
                               "norm_precision", "norm_winrate"]].mean(axis=1)
r["B2R_SCORE"] = np.round(
    r.perf_match_composite * 40
    + r.norm_regularite * 25
    + r.norm_psycho * 20
    + r.norm_progression * 15, 2)

r = r.sort_values("B2R_SCORE", ascending=False).reset_index(drop=True)
r["RANK"] = r.index + 1
r[["RANK", "tag_ingame", "tier", "role", "B2R_SCORE", "winrate_pct",
   "kda_moyen", "precision_moyenne", "score_psycho", "progression_slope"]]

# %% [markdown]
# ## 6. KPI — coefficient de stabilité (Spearman entre 2 fenêtres temporelles)

# %%
stab = b2r.ranking_stability(df_logs, score_col="score_perf")
print(f"Coefficient de stabilité : {stab['stability_coeff']}  "
      f"(n={stab['n_joueurs']}, p={stab['p_value']})")
print(f"KPI (> 0,85)             : {'OK' if stab['kpi_atteint'] else 'NON ATTEINT'}")

# %% [markdown]
# ## 7. Validation — cohérence avec le profil latent (données de démo)
# Le `latent_composite` combine niveau, régularité, bien-être et tendance — dans
# l'esprit de la formule B2R. On vérifie que le classement calculé le reproduit,
# puis on isole les joueurs dont le rang B2R s'écarte fortement du **niveau brut**
# (ce sont les cas que le staff doit regarder).

# %%
truth = pd.read_csv(b2r.GENERATED / "ranking_latent_truth.csv")
chk = r[["joueur_id", "tag_ingame", "RANK"]].merge(
    truth[["joueur_id", "rang_latent", "rang_skill_pur"]], on="joueur_id")

rho_c, p_c = spearmanr(chk.RANK, chk.rang_latent)
rho_s, _ = spearmanr(chk.RANK, chk.rang_skill_pur)
print(f"ρ(classement B2R, profil latent composite) = {rho_c:.3f} (p = {p_c:.4f})")
print(f"ρ(classement B2R, niveau brut seul)        = {rho_s:.3f}")
print("→ pipeline validé : corrélation significative avec le profil latent"
      if (rho_c > 0.6 and p_c < 0.05) else "→ écart à investiguer")

chk["ecart_vs_niveau"] = chk.rang_skill_pur - chk.RANK
print("\nJoueurs dont le rang B2R s'écarte le plus du niveau brut :")
print(chk.reindex(chk.ecart_vs_niveau.abs().sort_values(ascending=False).index)
      .head(4)[["tag_ingame", "RANK", "rang_skill_pur", "ecart_vs_niveau"]]
      .to_string(index=False))

# %% [markdown]
# ## 8. Export + SQL pour `player_ranking`

# %%
export_cols = ["joueur_id", "RANK", "tag_ingame", "tier", "role", "B2R_SCORE",
               "winrate_pct", "kda_moyen", "kda_std", "precision_moyenne",
               "ratio_degats_moyen", "score_psycho", "heures_training_moy",
               "progression_slope"]
df_rank = r[export_cols].copy()
b2r.write_export(df_rank, "B2R_Player_Ranking")
sql_path = b2r.ranking_to_sql(df_rank)
print(f"→ data/exports/B2R_Player_Ranking.csv")
print(f"→ data/exports/{sql_path.name}  (import phpMyAdmin : player_ranking + vues, en 1 fichier)")
