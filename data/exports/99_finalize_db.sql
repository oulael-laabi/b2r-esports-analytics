-- ============================================================
-- 99 — FINALISATION DE LA BASE (un seul import)
-- A importer APRES sql/00_rebuild_all.sql + scripts/run_pipeline.py
-- Contenu : player_ranking (donnees) + 4 vues Studio
-- ============================================================

USE b2r_intelligence_db;
TRUNCATE TABLE player_ranking;
INSERT INTO `player_ranking` (`joueur_id`, `tag_ingame`, `tier`, `role`, `B2R_SCORE`, `winrate_pct`, `kda_moyen`, `kda_std`, `precision_moyenne`, `ratio_degats_moyen`, `score_psycho`, `heures_training_moy`) VALUES
(1, 'VEGA_X', 'Main Roster', 'IGL', 67.11, 59.1, 6.3, 1.97, 74.8, 1.69, 7.25, 4.23),
(10, 'REZA__', 'Academy', 'Support', 58.38, 54.5, 3.21, 0.74, 63.9, 0.75, 7.19, 3.2),
(2, 'SARA_GG', 'Main Roster', 'Sniper', 56.51, 50.0, 8.32, 5.63, 76.4, 2.49, 7.27, 4.03),
(3, 'ORYX', 'Main Roster', 'Fragger', 56.24, 63.6, 4.5, 1.94, 70.5, 1.73, 6.55, 3.94),
(8, 'Yuki_op', 'Academy', 'Sniper', 55.91, 63.6, 3.49, 1.18, 62.9, 1.48, 6.9, 3.28),
(5, 'KENZO_B', 'Main Roster', 'IGL', 52.55, 63.6, 4.55, 1.7, 68.6, 1.44, 6.33, 3.55),
(9, 'Ghost_UIR', 'Academy', 'Fragger', 49.41, 72.7, 2.99, 0.85, 65.5, 1.2, 5.87, 3.26),
(11, 'VIPER_ac', 'Academy', 'Flex', 46.24, 45.5, 2.77, 0.86, 65.2, 0.98, 6.39, 3.31),
(7, 'OMZ', 'Main Roster', 'Support', 44.63, 50.0, 5.18, 3.93, 65.5, 1.02, 6.99, 3.61),
(6, 'ATLAS7', 'Main Roster', 'Flex', 41.22, 50.0, 4.34, 2.24, 72.2, 1.42, 5.79, 3.76),
(12, 'Nael_ff', 'Academy', 'IGL', 39.63, 36.4, 2.56, 0.6, 61.7, 0.79, 5.94, 3.21),
(4, 'DRIFT_MA', 'Main Roster', 'Fragger', 38.51, 50.0, 5.64, 2.46, 72.0, 2.0, 5.31, 3.81);


/* ============================================================
   05 — Vues SQL pour la couche Studio (P7)
   A executer APRES le calcul du ranking (notebook P4 -> table player_ranking)
   ============================================================ */
USE b2r_intelligence_db;

/* ---- VUE 1 : Player of the Week ----
   Meilleur joueur sur les 7 derniers jours de logs disponibles.
   (l'ancienne version agregeait tout l'historique -> corrige ici) */
CREATE OR REPLACE VIEW v_player_of_the_week AS
SELECT
    j.joueur_id,
    j.tag_ingame,
    j.role_tactique,
    e.nom AS equipe,
    ROUND(AVG(lp.score_perf), 2)     AS score_semaine,
    ROUND(AVG(lp.kda), 2)            AS kda_moyen,
    ROUND(AVG(lp.precision_tirs), 2) AS precision_moyenne,
    SUM(lp.nb_victoires)             AS total_victoires,
    SUM(lp.nb_parties)               AS total_parties,
    ROUND(SUM(lp.nb_victoires) * 100.0 / NULLIF(SUM(lp.nb_parties), 0), 1) AS winrate_pct,
    ROUND(AVG(lp.humeur), 1)         AS humeur_moy,
    ROUND(AVG(lp.focus), 1)          AS focus_moy
FROM logs_performance lp
JOIN joueurs j ON lp.joueur_id = j.joueur_id
JOIN equipes e ON j.equipe_id = e.equipe_id
WHERE lp.date_log >= (SELECT MAX(date_log) FROM logs_performance) - INTERVAL 7 DAY
GROUP BY j.joueur_id, j.tag_ingame, j.role_tactique, e.nom
ORDER BY score_semaine DESC
LIMIT 1;

/* ---- VUE 2 : Top Performers ---- */
CREATE OR REPLACE VIEW v_top_performers AS
SELECT
    ROW_NUMBER() OVER (ORDER BY pr.B2R_SCORE DESC) AS classement,
    pr.tag_ingame,
    pr.tier,
    pr.role,
    pr.B2R_SCORE,
    pr.winrate_pct,
    pr.kda_moyen,
    pr.precision_moyenne,
    pr.score_psycho,
    mt.kills                AS best_kills,
    mt.precision_tirs_match AS best_precision
FROM player_ranking pr
LEFT JOIN (
    SELECT joueur_id,
           MAX(kills)                AS kills,
           MAX(precision_tirs_match) AS precision_tirs_match
    FROM match_telemetry
    GROUP BY joueur_id
) mt ON pr.joueur_id = mt.joueur_id
ORDER BY pr.B2R_SCORE DESC;

/* ---- VUE 3 : Match Highlights ---- */
CREATE OR REPLACE VIEW v_match_highlights AS
SELECT
    mt.telemetry_id,
    j.tag_ingame,
    j.role_tactique,
    mt.date_match,
    mt.kills,
    mt.deaths,
    mt.assists,
    ROUND((mt.kills + mt.assists) / NULLIF(mt.deaths, 1), 2) AS kda_match,
    mt.degats_infliges,
    mt.precision_tirs_match,
    mt.objectifs_captures,
    mt.resultat_match,
    CASE
        WHEN mt.kills >= 25                THEN 'HIGHLIGHT - Carry performance'
        WHEN mt.precision_tirs_match >= 83 THEN 'HIGHLIGHT - Precision record'
        WHEN mt.objectifs_captures >= 5    THEN 'HIGHLIGHT - Objectifs domination'
        ELSE 'Performance standard'
    END AS tag_contenu
FROM match_telemetry mt
JOIN joueurs j ON mt.joueur_id = j.joueur_id
ORDER BY mt.kills DESC, mt.precision_tirs_match DESC;

/* ---- VUE 4 : Team Momentum ---- */
CREATE OR REPLACE VIEW v_team_momentum AS
SELECT
    e.nom AS equipe,
    COUNT(DISTINCT j.joueur_id)    AS nb_joueurs_actifs,
    ROUND(AVG(pr.B2R_SCORE), 2)    AS score_equipe_moyen,
    ROUND(AVG(pr.winrate_pct), 1)  AS winrate_equipe,
    ROUND(AVG(pr.kda_moyen), 2)    AS kda_equipe,
    ROUND(AVG(pr.score_psycho), 2) AS bien_etre_moyen,
    CASE
        WHEN AVG(pr.B2R_SCORE) >= 55 THEN 'En forme - Bon moment pour communiquer'
        WHEN AVG(pr.B2R_SCORE) >= 45 THEN 'Stable - Performance normale'
        ELSE 'En difficulte - Privilegier le discret'
    END AS recommandation_studio
FROM player_ranking pr
JOIN joueurs j ON pr.joueur_id = j.joueur_id
JOIN equipes e ON j.equipe_id = e.equipe_id
GROUP BY e.nom
ORDER BY score_equipe_moyen DESC;
