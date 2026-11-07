USE b2r_intelligence_db;
TRUNCATE TABLE player_ranking;
INSERT INTO `player_ranking` (`joueur_id`, `tag_ingame`, `tier`, `role`, `B2R_SCORE`, `winrate_pct`, `kda_moyen`, `kda_std`, `precision_moyenne`, `ratio_degats_moyen`, `score_psycho`, `heures_training_moy`) VALUES
(1, 'VEGA_X', 'Main Roster', 'IGL', 67.08, 59.1, 6.3, 1.97, 74.8, 1.69, 7.25, 4.23),
(10, 'REZA__', 'Main Roster', 'Support', 58.36, 54.5, 3.21, 0.74, 63.9, 0.75, 7.19, 3.2),
(2, 'SARA_GG', 'Main Roster', 'Sniper', 56.51, 50.0, 8.32, 5.63, 76.4, 2.49, 7.27, 4.03),
(3, 'ORYX', 'Main Roster', 'Fragger', 56.22, 63.6, 4.5, 1.94, 70.5, 1.73, 6.55, 3.94),
(8, 'Yuki_op', 'Main Roster', 'Sniper', 55.89, 63.6, 3.49, 1.18, 62.9, 1.48, 6.9, 3.28),
(5, 'KENZO_B', 'Main Roster', 'IGL', 52.52, 63.6, 4.55, 1.7, 68.6, 1.44, 6.33, 3.55),
(9, 'Ghost_UIR', 'Academy', 'Fragger', 49.39, 72.7, 2.99, 0.85, 65.5, 1.2, 5.87, 3.26),
(11, 'VIPER_ac', 'Academy', 'IGL', 46.5, 45.5, 2.78, 0.81, 65.2, 0.86, 6.39, 3.31),
(7, 'OMZ', 'Main Roster', 'Support', 44.64, 50.0, 5.18, 3.93, 65.5, 1.02, 6.99, 3.61),
(6, 'ATLAS7', 'Main Roster', 'Flex', 41.2, 50.0, 4.34, 2.24, 72.2, 1.42, 5.79, 3.76),
(12, 'Nael_ff', 'Academy', 'Flex', 39.56, 36.4, 2.52, 0.58, 61.7, 0.9, 5.94, 3.21),
(4, 'DRIFT_MA', 'Main Roster', 'Fragger', 38.49, 50.0, 5.64, 2.46, 72.0, 2.0, 5.31, 3.81);
