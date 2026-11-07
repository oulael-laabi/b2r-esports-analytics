# P2 — Player Dashboard (Power BI)

> **Dépôt public :** le fichier `.pbix` n'est pas versionné (il embarque une copie
> des données en mode Import). Captures du rapport : [`docs/img/`](../docs/img/).

**Livrable P2 du cahier des charges B2R-STU-2026-IPD-01.**
Techno : Power BI Desktop, connexion MySQL. KPI : dashboard 4 pages.

Ce livrable n'a **pas de notebook** — l'artefact est le fichier
`B2R_Player_Dashboard.pbix`. Cette notice tient lieu de code source.

---

## Contenu

| | |
|---|---|
| Fichier | `B2R_Player_Dashboard.pbix` |
| Pages | 4 |
| Source | MySQL `b2r_intelligence_db` sur `localhost` (XAMPP / phpMyAdmin) |
| Tables importées par le modèle | `player_ranking`, `logs_performance`, `objectifs_joueurs`, `joueurs`, `equipes`, `jeux` |
| Tables affichées dans les visuels | `player_ranking`, `logs_performance`, `objectifs_joueurs` |

Le modèle relie `joueurs` → `equipes` → `jeux` (dimensions) et
`player_ranking` / `logs_performance` / `objectifs_joueurs` (faits) par
`joueur_id`.

---

## Rafraîchir le dashboard

Prérequis : la base est reconstruite et finalisée (voir
[`../sql/README.md`](../sql/README.md)) — c.-à-d. `player_ranking` **et** les
vues `v_*` existent.

1. Démarrer MySQL (XAMPP → *Start* MySQL).
2. Ouvrir `B2R_Player_Dashboard.pbix`.
3. Ruban **Accueil → Actualiser** (bouton, **ne pas** rouvrir le fichier).
4. Si Power BI demande les identifiants : `root`, mot de passe vide, base
   `b2r_intelligence_db`.

---

## ⚠️ Contrainte du modèle — `equipes.jeu_id` doit être unique

Le modèle Power BI suppose **une équipe par jeu**. Le schéma SQL ne l'impose
pas (FK simple, pas de `UNIQUE`), mais un `jeu_id` en double dans `equipes`
fait **échouer le rafraîchissement** et **annule en cascade** le chargement de
toutes les autres tables.

Vérifier **avant** d'actualiser (onglet SQL de phpMyAdmin) — doit renvoyer
**0 ligne** :

```sql
SELECT jeu_id, COUNT(*)
FROM equipes
GROUP BY jeu_id
HAVING COUNT(*) > 1;
```

Configuration correcte : 6 équipes, `jeu_id` ∈ {1, 2, 3, 4, 6, 7}.
`B2R Free Fire` (jeu_id 7) est le roster **Academy**. Voir
`../sql/02_seed_reference.sql`.

---

## Reconstruire la connexion (si le `.pbix` perd sa source)

Obtenir des données → **Base de données MySQL** →
Serveur `localhost`, Base `b2r_intelligence_db` → mode **Importer** →
sélectionner les 6 tables ci-dessus → **Charger**.
