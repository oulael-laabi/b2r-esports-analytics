/* ============================================================
   02 — Donnees de reference (catalogue jeux + equipes)
   A executer APRES 01_schema.sql
   ============================================================ */
USE b2r_intelligence_db;

/* ---- Catalogue des 10 jeux B2R ---- */
INSERT INTO jeux (jeu_id, nom, plateforme, genre, actif, date_ajout) VALUES
(1,  'Fortnite',       'PC/Console', 'Battle Royale', 1, '2026-01-01'),
(2,  'PUBG Mobile',    'Mobile',     'Battle Royale', 1, '2026-01-01'),
(3,  'Valorant',       'PC',         'FPS Tactique',  1, '2026-01-01'),
(4,  'FC Mobile',      'Mobile',     'Football',      1, '2026-01-01'),
(5,  'EA FC 25',       'PC/Console', 'Football',      1, '2026-01-01'),
(6,  'Mobile Legends', 'Mobile',     'MOBA',          1, '2026-01-01'),
(7,  'Free Fire',      'Mobile',     'Battle Royale', 1, '2026-01-01'),
(8,  'Street Fighter', 'PC/Console', 'Fighting',      1, '2026-01-01'),
(9,  'Call of Duty',   'PC/Mobile',  'FPS',           1, '2026-01-01'),
(10, 'eFootball',      'PC/Mobile',  'Football',      1, '2026-01-01');

/* ---- Equipes : 1 par jeu (jeu_id unique — requis par le modele Power BI).
   B2R Free Fire est le roster Academy (joueurs en developpement). ---- */
INSERT INTO equipes (equipe_id, nom, jeu_id, tier, date_creation, active) VALUES
(1, 'B2R Fortnite',       1, 'Main Roster', '2026-01-01', 1),
(2, 'B2R PUBG Mobile',    2, 'Main Roster', '2024-01-01', 1),
(3, 'B2R Valorant',       3, 'Main Roster', '2025-01-01', 1),
(4, 'B2R FC Mobile',      4, 'Main Roster', '2024-01-01', 1),
(5, 'B2R Mobile Legends', 6, 'Main Roster', '2024-01-01', 1),
(6, 'B2R Free Fire',      7, 'Academy',     '2026-02-01', 1);

/* ---- Plans d'entrainement (Staff Layer) ---- */
INSERT INTO training_plans (equipe_id, date_debut_plan, objectif_quotidien, variation_tactique, notes) VALUES
(1, '2026-05-19', '4h de scrim plus 1h aim training', 'Focus rotation early game',       'Roster complet disponible'),
(3, '2026-05-19', '3h scrim plus 1h theorie macro',   'Travail des executes cote A',      'Nouveau calendrier de scrims'),
(6, '2026-05-19', '2h30 scrim plus 1h VOD review',    'Fondamentaux de positionnement',   'Roster Academy en integration');

/* ---- Objectifs equipe ---- */
INSERT INTO objectifs_equipe (equipe_id, description, deadline, statut) VALUES
(1, 'Reduire les eliminations en early game de 20% avant les qualifs regionales', '2026-07-15', 'En cours'),
(3, 'Atteindre 55% de winrate sur les scrims officiels',                          '2026-07-01', 'En cours'),
(6, 'Promouvoir 2 joueurs Academy vers le Main Roster avant septembre',           '2026-09-01', 'En cours');
