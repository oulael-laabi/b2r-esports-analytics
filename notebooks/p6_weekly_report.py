# %% [markdown]
# # P6 — Weekly AI Reports
# **Ref :** B2R-STU-2026-IPD-01
#
# Script batch : agrégation hebdo, détection d'anomalies, prévision par
# régression, rapport PDF exécutif. KPI : **accuracy des alertes > 90 % via
# backtesting**.
#
# **Changement vs v1** : l'accuracy n'est plus une constante (`92.0`). Elle est
# **mesurée** par `b2r_common.backtest_alerts()` contre les incidents connus
# (`data/generated/incidents_ground_truth.csv`) : le générateur a injecté des
# incidents (blessure, latence…) les jours de faible bien-être ; on vérifie que
# le système d'alertes les capte.

# %%
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path.cwd().parent / "scripts"))
import b2r_common as b2r

# %% [markdown]
# ## 1. Chargement + fenêtre hebdomadaire

# %%
logs = b2r.load_table("logs_performance")
logs["date_log"] = pd.to_datetime(logs["date_log"])
dim = b2r.player_dim()[["joueur_id", "tag_ingame", "role_tactique", "tier"]]
ranking = b2r.read_export("B2R_Player_Ranking")

fin = logs.date_log.max()
debut = fin - pd.Timedelta(days=6)
semaine = logs[logs.date_log.between(debut, fin)].merge(dim, on="joueur_id", how="left")
print(f"Semaine analysée : {debut.date()} → {fin.date()}  ({len(semaine)} logs)")

# %% [markdown]
# ## 2. Agrégats hebdomadaires par joueur

# %%
wk = semaine.groupby(["joueur_id", "tag_ingame"]).agg(
    nb_sessions=("log_id", "count"),
    heures_moy=("heures_training", "mean"),
    winrate_moy=("nb_victoires", "sum"),
    parties=("nb_parties", "sum"),
    kda_moy=("kda", "mean"),
    precision_moy=("precision_tirs", "mean"),
    score_perf_moy=("score_perf", "mean"),
    humeur_moy=("humeur", "mean"),
    focus_moy=("focus", "mean"),
    fatigue_moy=("fatigue_mentale", "mean"),
    clarte_moy=("clarte_reaction", "mean"),
).reset_index()
wk["winrate_moy"] = np.round(wk.winrate_moy / wk.parties * 100, 1)
wk = wk.round(2)
wk

# %% [markdown]
# ## 3. Détection d'anomalies → niveaux d'alerte

# %%
TH = b2r.DEFAULT_THRESHOLDS  # fatigue>6.5, focus<6, kda<1.8, winrate<45, precision<60

def alertes_joueur(r):
    a = []
    if r.fatigue_moy > TH["fatigue"]:
        a.append(f"Fatigue élevée ({r.fatigue_moy}/10)")
    if r.focus_moy < TH["focus"]:
        a.append(f"Focus bas ({r.focus_moy}/10)")
    if r.kda_moy < TH["kda"]:
        a.append(f"KDA insuffisant ({r.kda_moy})")
    if r.winrate_moy < TH["winrate"]:
        a.append(f"Winrate bas ({r.winrate_moy}%)")
    if r.precision_moy < TH["precision"]:
        a.append(f"Précision faible ({r.precision_moy}%)")
    return a

wk["alertes"] = wk.apply(alertes_joueur, axis=1)
wk["nb_alertes"] = wk.alertes.str.len()
wk["niveau"] = np.where(wk.nb_alertes >= 3, "CRITIQUE",
                np.where(wk.nb_alertes >= 1, "ATTENTION", "OK"))
for _, r in wk.iterrows():
    print(f"{r.tag_ingame:<10} [{r.niveau}]  " + " | ".join(r.alertes))

# %% [markdown]
# ## 4. Prévision semaine suivante (régression linéaire sur toute la fenêtre)

# %%
prev = []
for jid, g in logs.sort_values("date_log").groupby("joueur_id"):
    y = g.score_perf.to_numpy(float)
    tag = dim.loc[dim.joueur_id == jid, "tag_ingame"].iloc[0]
    if len(y) < 3:
        continue
    x = np.arange(len(y))
    a, b = np.polyfit(x, np.nan_to_num(y, nan=np.nanmean(y)), 1)
    prev.append({"tag_ingame": tag, "tendance_pente": round(a, 3),
                 "score_actuel": round(y[-1], 1),
                 "score_prevu_s+1": round(a * (len(y) + 7) + b, 1),
                 "direction": "Hausse" if a > 0.05 else "Baisse" if a < -0.05 else "Stable"})
df_prev = pd.DataFrame(prev)
print(df_prev.to_string(index=False))

# %% [markdown]
# ## 5. KPI — backtest du système d'alertes (**mesuré**, pas simulé)
#
# Le générateur a injecté des incidents (blessure, fatigue oculaire, souci
# technique) en période de surcharge. On mesure la capacité du détecteur à
# signaler ces épisodes 0 à 2 jours à l'avance.
#
# ⚠️ *La classe « incident » est rare (~13 % des jours-joueur). L'**accuracy**
# est donc trompeuse : toujours répondre « pas d'alerte » donnerait déjà ~87 %.
# Les métriques pertinentes pour un outil d'alerte précoce sont le **rappel**
# (ne pas rater d'incident) et le **F1**.*

# %%
incidents = pd.read_csv(b2r.GENERATED / "incidents_ground_truth.csv")
bt = b2r.backtest_alerts(logs, incidents, horizon_days=2)
base_rate_acc = round((1 - len(incidents) / len(logs)) * 100, 1)

print("BACKTEST DU SYSTÈME D'ALERTES  (règle : détérioration psychométrique)")
print("-" * 60)
print(f"  jours-joueur : {bt['n_jours']}   incidents : {len(incidents)}")
print(f"  TP={bt['TP']}  FP={bt['FP']}  FN={bt['FN']}  TN={bt['TN']}")
print(f"  rappel    : {bt['rappel']} %   <-- métrique clé (incidents captés)")
print(f"  précision : {bt['precision']} %")
print(f"  F1        : {bt['f1']} %")
print(f"  accuracy  : {bt['accuracy']} %   (référence 'toujours négatif' : {base_rate_acc} %)")
print()
print(f"Lecture : le détecteur par seuils capte ~{bt['rappel']:.0f} % des incidents "
      f"(rappel) mais génère beaucoup de faux positifs (précision ~{bt['precision']:.0f} %). "
      f"L'accuracy brute ({bt['accuracy']} %) est sous la référence 'toujours négatif' "
      f"({base_rate_acc} %) : sur une classe rare, un modèle supervisé (arbre/gradient "
      f"boosting sur les features psychométriques) est nécessaire pour viser la cible.")

# %% [markdown]
# ## 6. Génération du rapport PDF (ReportLab)

# %%
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

DATE = datetime(2026, 6, 28)
out = b2r.OUTPUTS / "reports" / f"B2R_Weekly_Report_{DATE:%Y%m%d}.pdf"
out.parent.mkdir(parents=True, exist_ok=True)

H = colors.HexColor
st_title = ParagraphStyle("t", fontSize=17, fontName="Helvetica-Bold", alignment=TA_CENTER, textColor=H("#1F2937"))
st_sub = ParagraphStyle("s", fontSize=10, fontName="Helvetica", alignment=TA_CENTER, textColor=H("#6B7280"), spaceAfter=16)
st_h2 = ParagraphStyle("h", fontSize=12.5, fontName="Helvetica-Bold", textColor=H("#1F2937"), spaceBefore=14, spaceAfter=6)
st_body = ParagraphStyle("b", fontSize=9.5, textColor=H("#374151"), spaceAfter=3)
st_alert = ParagraphStyle("a", fontSize=9.5, fontName="Helvetica-Bold", textColor=H("#DC2626"), spaceAfter=2)
st_ok = ParagraphStyle("o", fontSize=9.5, fontName="Helvetica-Bold", textColor=H("#059669"), spaceAfter=2)


def tbl(data, widths):
    t = Table(data, colWidths=widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), H("#1F2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [H("#F9FAFB"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.3, H("#D1D5DB")),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


story = [
    Paragraph("BACK2REVENGE — RAPPORT EXÉCUTIF HEBDOMADAIRE", st_title),
    Paragraph(f"Semaine du {debut:%d/%m} au {fin:%d/%m/%Y} · CONFIDENTIEL", st_sub),
    HRFlowable(width="100%", thickness=1.5, color=H("#1F2937")), Spacer(1, 0.3 * cm),
]

# 1. Performance
story += [Paragraph("1. Performance hebdomadaire", st_h2)]
d = [["Joueur", "Sess.", "Winrate", "KDA", "Préc.", "Score"]]
for _, r in wk.iterrows():
    d.append([r.tag_ingame, int(r.nb_sessions), f"{r.winrate_moy}%", r.kda_moy,
              f"{r.precision_moy}%", r.score_perf_moy])
story += [tbl(d, [3.2 * cm, 1.6 * cm, 2 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm]), Spacer(1, 0.3 * cm)]

# 2. Alertes
story += [Paragraph("2. Alertes détectées", st_h2)]
if wk.nb_alertes.sum() == 0:
    story += [Paragraph("Aucune alerte cette semaine.", st_ok)]
else:
    for _, r in wk[wk.nb_alertes > 0].iterrows():
        story += [Paragraph(f"[{r.niveau}] {r.tag_ingame}", st_alert)]
        story += [Paragraph("• " + a, st_body) for a in r.alertes]
story += [Spacer(1, 0.3 * cm)]

# 3. Classement B2R
story += [Paragraph("3. Classement B2R (P4)", st_h2)]
d = [["#", "Joueur", "Tier", "Rôle", "B2R", "Winrate", "KDA", "Psycho"]]
for _, r in ranking.sort_values("RANK").iterrows():
    d.append([int(r.RANK), r.tag_ingame, r.tier, r.role, r.B2R_SCORE,
              f"{r.winrate_pct}%", r.kda_moyen, r.score_psycho])
story += [tbl(d, [0.9 * cm, 2.6 * cm, 2.4 * cm, 1.9 * cm, 1.6 * cm, 1.9 * cm, 1.5 * cm, 1.6 * cm]),
          Spacer(1, 0.3 * cm)]

# 4. Prévisions
story += [Paragraph("4. Prévisions semaine suivante", st_h2)]
d = [["Joueur", "Pente", "Score actuel", "Score prévu", "Direction"]]
for _, r in df_prev.iterrows():
    d.append([r.tag_ingame, r.tendance_pente, r.score_actuel, r["score_prevu_s+1"], r.direction])
story += [tbl(d, [3 * cm, 2 * cm, 2.6 * cm, 2.6 * cm, 2.4 * cm]), Spacer(1, 0.3 * cm)]

# 5. Fiabilité du système d'alertes (backtest)
story += [Paragraph("5. Fiabilité du système d'alertes (backtest mesuré)", st_h2)]
d = [["Rappel", "Précision", "F1", "Accuracy", "Réf. base"],
     [f"{bt['rappel']}%", f"{bt['precision']}%", f"{bt['f1']}%", f"{bt['accuracy']}%",
      f"{base_rate_acc}%"]]
story += [tbl(d, [2.6 * cm] * 5),
          Paragraph(f"Backtest : {bt['n_jours']} jours-joueur, {len(incidents)} incidents "
                    f"connus, horizon 2 j. Classe rare : le rappel et le F1 priment sur "
                    f"l'accuracy. Piste d'amélioration : détecteur supervisé.", st_body)]

story += [Spacer(1, 0.4 * cm), HRFlowable(width="100%", thickness=1, color=H("#D1D5DB")),
          Paragraph("Rapport généré automatiquement — B2R Intelligence Platform",
                    ParagraphStyle("f", fontSize=7.5, alignment=TA_CENTER, textColor=H("#9CA3AF")))]

SimpleDocTemplate(str(out), pagesize=A4, rightMargin=1.8 * cm, leftMargin=1.8 * cm,
                  topMargin=1.8 * cm, bottomMargin=1.8 * cm).build(story)
print(f"→ {out}")

# %% [markdown]
# ## 7. Résumé exécutif (console)

# %%
print("=" * 56)
print("RAPPORT P6 — WEEKLY AI REPORTS")
print("=" * 56)
print(f"Joueurs suivis          : {len(wk)}")
print(f"Alertes CRITIQUE        : {(wk.niveau == 'CRITIQUE').sum()}")
print(f"Alertes ATTENTION       : {(wk.niveau == 'ATTENTION').sum()}")
print(f"Alertes — rappel {bt['rappel']} % | précision {bt['precision']} % | F1 {bt['f1']} %")
print(f"  (accuracy {bt['accuracy']} % vs référence base {base_rate_acc} % — classe rare)")
print(f"PDF                     : {out.name}")
