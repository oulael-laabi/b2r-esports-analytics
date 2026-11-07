# Base de données — procédure

Base cible : `b2r_intelligence_db` (MySQL / MariaDB, phpMyAdmin sur `localhost`).

## Procédure simple — 2 imports, aucun ordre à retenir

| Étape | Action | Fichier |
|---|---|---|
| 0 | **Sauvegarde** de l'ancienne base | phpMyAdmin → Exporter → SQL |
| 1 | Import n°1 (reconstruit tout) | `sql/00_rebuild_all.sql` |
| 2 | Calcul du ranking | `python scripts/run_pipeline.py` |
| 3 | Import n°2 (finalise) | `data/exports/99_finalize_db.sql` |
| 4 | Power BI | ouvrir le `.pbix` → Actualiser |

`00_rebuild_all.sql` contient **schéma + jeux + équipes + 12 joueurs + logs +
matchs + évaluations** (il fait lui-même `DROP DATABASE` / `CREATE DATABASE`).
`99_finalize_db.sql` contient **player_ranking + les 4 vues**.

### Vérification (onglet SQL)

```sql
SELECT (SELECT COUNT(*) FROM joueurs)           AS joueurs,     -- 12
       (SELECT COUNT(*) FROM logs_performance)  AS logs,        -- 420
       (SELECT COUNT(*) FROM match_telemetry)   AS matchs,      -- 264
       (SELECT COUNT(*) FROM evaluations_coach) AS evals,       -- 72
       (SELECT COUNT(*) FROM equipes)           AS equipes,     -- 6
       (SELECT COUNT(*) FROM player_ranking)    AS ranking,     -- 12  (après étape 3)
       (SELECT COUNT(*) FROM v_top_performers)  AS vue_top;     -- 12  (après étape 3)
```

## Fichiers séparés (si besoin de rejouer une partie)

| Fichier | Contenu | Ordre |
|---|---|---|
| `01_schema.sql` | 13 tables + contraintes (DROP + CREATE DATABASE) | 1 |
| `02_seed_reference.sql` | `jeux`, `equipes` (4 Main + 2 Academy), training plans | 2 |
| `03_load_generated_data.sql` | `joueurs`, `logs_performance`, `match_telemetry`, `evaluations_coach` | 3 |
| `05_views.sql` | 4 vues `v_*` (lisent `player_ranking`) | après P4 |

`00_rebuild_all.sql` = `01` + `02` + `03` concaténés (régénéré par le générateur).

## Notes

- `source_donnee` (`'reelle'` / `'synthetique'`) sur `joueurs` distingue les 2
  joueurs réels (tags `VEGA_X`, `ORYX`) des 10 joueurs de démonstration.
- `v_player_of_the_week` corrigée : fenêtre glissante de 7 jours.
- Ne jamais éditer à la main : `logs_performance`, `match_telemetry`,
  `player_ranking`, les vues `v_*` (régénérés par le pipeline).
- Ajout d'un vrai joueur : `INSERT INTO joueurs (... , source_donnee) VALUES (..., 'reelle');`
