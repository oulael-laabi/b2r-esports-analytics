# Traçabilité des livrables — P1 à P7

*Document de correspondance entre le cahier des charges **B2R-STU-2026-IPD-01**
(sept livrables interconnectés) et les artefacts du dépôt.*

Le dépôt v2 est organisé **par couche technique** (`sql/`, `scripts/`,
`notebooks/`, `powerbi/`, `outputs/`) et non plus par livrable comme la v1
(`P1_Player_Database/` … `P7_Studio_Sync/`). Ce choix supprime la duplication
(mapping joueur unique, schéma SQL unifié, orchestrateur unique) mais rend la
correspondance avec le cahier des charges moins visible. Ce fichier la rétablit.

Chaque notebook porte en tête `# Pn — <nom>` + `Ref : B2R-STU-2026-IPD-01`.

---

## Vue d'ensemble

| # | Livrable | Techno (cahier des charges) | KPI cible | Résultat mesuré (démo, seed 42) | Statut |
|---|---|---|---|---|---|
| **P1** | Player Database System | MySQL, Python ETL | taux d'erreur saisie < 1 % | 0 % (fichier propre) · 45 % détectés sur le fichier volontairement erroné (5/11) | ✅ Atteint |
| **P2** | Player Dashboard | Power BI (connexion MySQL, mode Import) | dashboard 4 pages | 4 pages, 6 tables importées, actualisation à la demande | ✅ Atteint |
| **P3** | Match Analysis System | Python, NumPy, Pandas | traitement < 5 min | ≈ 0,05 s pour 264 matchs | ✅ Atteint |
| **P4** | Player Ranking System | Z-score → sigmoïde, Spearman | coeff. stabilité > 0,85 | **ρ ≈ 0,94** (2 fenêtres) · ρ ≈ 0,84 vs profil latent | ✅ Atteint (données démo) |
| **P5** | Coach Feedback Analytics | Pandas, catégorisation mots-clés | pipeline agrégation + cross-tab | pipeline + cross-tab livrés · 75 % des évals coach alignées | ✅ Atteint (pipeline) |
| **P6** | Weekly AI Reports | régression, détection d'anomalies, ReportLab | accuracy alertes > 90 % (backtest) | rappel ≈ 71 % · précision ≈ 49 % · **F1 ≈ 58 %** · accuracy ≈ 62 % | ❌ Non atteint — voir `PROJECT_SCOPE.md` |
| **P7** | Studio + Data Sync | vues SQL, export JSON | délai de production −50 % | export JSON instantané vs recherche manuelle (gain non chiffré) | 🟠 Qualitatif |

> Les KPIs P2 (« engagement joueurs > 90 % »), P5 (« adoption staff > 75 % ») et
> P7 (« −50 % ») sont des métriques d'usage produit / organisationnelles, non
> mesurables dans le périmètre du stage. Détail des chiffres et des limites :
> [`PROJECT_SCOPE.md`](PROJECT_SCOPE.md).

---

## P1 — Player Database System

**But :** base relationnelle des joueurs + validation ETL du formulaire Staff
**avant** insertion. KPI : taux d'erreur de saisie < 1 %.

| Rôle | Fichier |
|---|---|
| Schéma (13 tables + contraintes) | `sql/01_schema.sql` |
| Données de référence (10 jeux, 6 équipes, plans) | `sql/02_seed_reference.sql` |
| Chargement données générées | `sql/03_load_generated_data.sql` |
| Rebuild complet (01+02+03, DROP/CREATE DB) | `sql/00_rebuild_all.sql` |
| Validation ETL (5 règles : 4 ERREUR + 1 AVERTISSEMENT) | `notebooks/p1_etl_validation.py` (`.ipynb`) |
| Entrée du formulaire | `data/raw/joueurs_saisie.csv` |
| Fichier de test volontairement erroné | `data/raw/joueurs_saisie_demo_erreurs.csv` |
| Sorties | `data/exports/joueurs_valides.csv`, `joueurs_erreurs.csv`, `joueurs_avertissements.csv` |

**KPI :** 0 erreur sur le fichier propre ; sur le fichier de test, 5 des 11
lignes rejetées — chaque règle (tag manquant/mal formé, FK inexistante, date
future, âge hors 14–40, `nom_legal` manquant → avertissement) est démontrée.

---

## P2 — Player Dashboard

**But :** dashboard décisionnel Power BI branché sur MySQL en **mode Import**
(actualisation à la demande, après exécution du pipeline). KPI : 4 pages.

| Rôle | Fichier |
|---|---|
| Rapport Power BI | `powerbi/B2R_Player_Dashboard.pbix` |
| Notice (pages, connexion, contrainte modèle) | `powerbi/README.md` |
| Tables consommées | `logs_performance`, `objectifs_joueurs`, `player_ranking` (+ `jeux`, `equipes`, `joueurs` importées par le modèle) |

**Pas de notebook** : le livrable est le fichier `.pbix`. Contrainte non
triviale : `equipes.jeu_id` doit être **unique** (une équipe par jeu), sinon le
rafraîchissement du modèle échoue. Détail dans `powerbi/README.md`.

---

## P3 — Match Analysis System

**But :** parser la télémétrie post-match pour exposer les déficits techniques
par joueur. KPI : traitement < 5 min post-saisie.

| Rôle | Fichier |
|---|---|
| Analyse | `notebooks/p3_match_analysis.py` (`.ipynb`) |
| Entrée | table `match_telemetry` / `data/generated/match_telemetry.csv` |
| Sorties (lues par P4 et P6) | `data/exports/match_analysis_stats.csv`, `match_analysis_details.csv`, `match_deficits.csv` |

**KPI :** ≈ 0,05 s pour 264 matchs (chronométré dans le notebook) — très
en-deçà des 5 min.

---

## P4 — Player Ranking System

**But :** score pondéré + classement dynamique.
`B2R_SCORE = Perf_Match×40 + Régularité×25 + Psychométrie×20 + Progression×15`,
normalisation Z-score → sigmoïde. KPI : coefficient de stabilité > 0,85.

| Rôle | Fichier |
|---|---|
| Calcul du ranking | `notebooks/p4_player_ranking.py` (`.ipynb`) |
| Normalisation, stabilité Spearman, backtest | `scripts/b2r_common.py` (`zscore_sigmoid`, `ranking_stability`) |
| Sorties | `data/exports/B2R_Player_Ranking.csv`, `player_ranking_insert.sql` |
| Chargement en base + vues | `data/exports/99_finalize_db.sql` |
| Vérité latente (validation) | `data/generated/ranking_latent_truth.csv` |

**KPI :** coefficient de stabilité = **corrélation de Spearman entre le
classement calculé sur la 1ʳᵉ et la 2ᵉ moitié de la fenêtre** (≈ 0,94) — et non
plus `1 − σ/µ` comme en v1. Corrélation ≈ 0,84 avec le niveau de jeu latent
ayant servi à générer la démo : le classement retrouve le niveau réel des
joueurs. Le classement étant *stable par construction* sur données synthétiques,
le coefficient de stabilité valide la cohérence de la méthode (voir
`PROJECT_SCOPE.md`).

---

## P5 — Coach Feedback Analytics

**But :** agréger les évaluations coach, les croiser avec la performance réelle,
catégoriser les commentaires par mots-clés. KPI : pipeline d'agrégation +
cross-tabulation.

| Rôle | Fichier |
|---|---|
| Analyse | `notebooks/p5_coach_analytics.py` (`.ipynb`) |
| Entrées | tables `evaluations_coach`, ranking P4 |
| Sorties | `data/exports/coach_coherence.csv`, `coach_crosstab.csv`, `coach_feedback_details.csv`, `coach_feedback_vs_performance.csv` |

**Note :** `coherence_score` compare l'évaluation coach et le `B2R_SCORE` sur la
**même échelle** (rangs normalisés 0–1). La « catégorisation NLP » du cahier des
charges = catégorisation par mots-clés (pas de modèle de langage).

---

## P6 — Weekly AI Reports

**But :** script batch — agrégation hebdo, détection d'anomalies, prévision par
régression, rapport PDF exécutif. KPI : accuracy des alertes > 90 % via
backtesting.

| Rôle | Fichier |
|---|---|
| Génération du rapport | `notebooks/p6_weekly_report.py` (`.ipynb`) |
| Backtest des alertes | `scripts/b2r_common.py` (`backtest_alerts`) |
| Vérité terrain des incidents | `data/generated/incidents_ground_truth.csv` |
| Sortie PDF | `outputs/reports/B2R_Weekly_Report_20260628.pdf` |

**KPI — non atteint :** les incidents sont une
classe rare (~15 % des jours-joueur), donc « ne jamais alerter » donne déjà
~85 % d'accuracy → l'accuracy seule est trompeuse. Le détecteur par seuils capte
71 % des incidents (rappel) au prix de nombreux faux positifs (F1 ≈ 58 %).
Atteindre la cible demande un **modèle supervisé** (arbre / gradient boosting)
sur les features psychométriques, principale perspective du projet. Différence
clé avec la version initiale : `accuracy = 92.0` était **codé en dur** ; ici la valeur est **mesurée par
backtest**.

---

## P7 — Studio + Data Sync

**But :** pipeline d'export média — 4 vues SQL Studio → un JSON structuré unique.
KPI : délai de production −50 % — gain qualitatif, non chiffré dans le périmètre
(export instantané vs recherche manuelle).

| Rôle | Fichier |
|---|---|
| Vues SQL | `sql/05_views.sql` — `v_player_of_the_week`, `v_top_performers`, `v_match_highlights`, `v_team_momentum` |
| Export | `notebooks/p7_studio_sync.py` (`.ipynb`) |
| Sortie | `outputs/studio/B2R_Studio_Export_2026-06-28.json` |
| Exports CSV des vues | `data/exports/v_*.csv` |

En base MySQL : lit directement les vues `v_*`. En fallback CSV (Colab) :
recalcule l'équivalent depuis les tables + le classement P4. Le JSON porte un
bloc `meta` (`document_ref`, `date_export`, `version`, `confidentiel`).

---

## Orchestration

`scripts/run_pipeline.py` enchaîne **P1 → P3 → P4 → P5 → P6 → P7** sans
intervention (P2 = Power BI, hors chaîne Python). Ordre complet dans le
[`README.md`](../README.md) racine et [`sql/README.md`](../sql/README.md).
