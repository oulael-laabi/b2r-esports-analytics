/* ============================================================
   ESPORTS PERFORMANCE ANALYTICS SYSTEM
   Schema relationnel — MySQL / MariaDB
   Organisme d'accueil : BACK2REVENGE STUDIO
   Ref : B2R-STU-2026-IPD-01

   13 tables + 4 vues (P7).
   Ordre d'execution : 01_schema -> 02_seed_reference
                       -> 03_load_generated_data -> 05_views
   ============================================================ */

DROP DATABASE IF EXISTS b2r_intelligence_db;
CREATE DATABASE b2r_intelligence_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE b2r_intelligence_db;

/* ---- 1. JEUX ---- */
CREATE TABLE jeux (
    jeu_id      INT AUTO_INCREMENT PRIMARY KEY,
    nom         VARCHAR(100) NOT NULL,
    plateforme  VARCHAR(50),
    genre       VARCHAR(50),
    actif       TINYINT(1) DEFAULT 1,
    date_ajout  DATE
) ENGINE=InnoDB;

/* ---- 2. EQUIPES ---- */
CREATE TABLE equipes (
    equipe_id     INT AUTO_INCREMENT PRIMARY KEY,
    nom           VARCHAR(100) NOT NULL,
    jeu_id        INT NOT NULL,
    tier          ENUM('Main Roster','Academy','Amateur') DEFAULT 'Academy',
    date_creation DATE,
    active        TINYINT(1) DEFAULT 1,
    CONSTRAINT fk_equipes_jeu FOREIGN KEY (jeu_id) REFERENCES jeux(jeu_id)
) ENGINE=InnoDB;

/* ---- 3. JOUEURS ---- */
CREATE TABLE joueurs (
    joueur_id      INT AUTO_INCREMENT PRIMARY KEY,
    nom_legal      VARCHAR(100),
    tag_ingame     VARCHAR(50) NOT NULL UNIQUE,
    equipe_id      INT,
    jeu_principal  INT,
    jeu_secondaire INT,
    role_tactique  VARCHAR(50),
    pays           VARCHAR(50) DEFAULT 'Maroc',
    ville          VARCHAR(50),
    date_naissance DATE,
    date_rejoins   DATE,
    actif          TINYINT(1) DEFAULT 1,
    -- distingue les donnees reelles des donnees de demonstration
    source_donnee  ENUM('reelle','synthetique') DEFAULT 'synthetique',
    CONSTRAINT fk_joueurs_equipe FOREIGN KEY (equipe_id)      REFERENCES equipes(equipe_id),
    CONSTRAINT fk_joueurs_jeu1   FOREIGN KEY (jeu_principal)  REFERENCES jeux(jeu_id),
    CONSTRAINT fk_joueurs_jeu2   FOREIGN KEY (jeu_secondaire) REFERENCES jeux(jeu_id)
) ENGINE=InnoDB;

/* ---- 4. TOURNOIS ---- */
CREATE TABLE tournois (
    tournoi_id     INT AUTO_INCREMENT PRIMARY KEY,
    nom            VARCHAR(150) NOT NULL,
    jeu_id         INT,
    type           ENUM('Online','LAN','Hybride') DEFAULT 'Online',
    scope          ENUM('Local','National','Africain','International') DEFAULT 'National',
    nb_equipes     INT,
    nb_joueurs     INT,
    prize_pool_usd DECIMAL(10,2),
    date_debut     DATE,
    date_fin       DATE,
    organisateur   VARCHAR(100),
    CONSTRAINT fk_tournois_jeu FOREIGN KEY (jeu_id) REFERENCES jeux(jeu_id)
) ENGINE=InnoDB;

/* ---- 5. PARTICIPATIONS TOURNOI ---- */
CREATE TABLE participations_tournoi (
    participation_id INT AUTO_INCREMENT PRIMARY KEY,
    tournoi_id       INT NOT NULL,
    equipe_id        INT NOT NULL,
    classement_final INT,
    points_gagnes    INT DEFAULT 0,
    notes            TEXT,
    CONSTRAINT fk_part_tournoi FOREIGN KEY (tournoi_id) REFERENCES tournois(tournoi_id),
    CONSTRAINT fk_part_equipe  FOREIGN KEY (equipe_id)  REFERENCES equipes(equipe_id)
) ENGINE=InnoDB;

/* ---- 6. LOGS PERFORMANCE QUOTIDIENNE ---- */
CREATE TABLE logs_performance (
    log_id             INT AUTO_INCREMENT PRIMARY KEY,
    joueur_id          INT NOT NULL,
    date_log           DATE NOT NULL,
    heures_training    DECIMAL(4,2),
    nb_parties         INT,
    nb_victoires       INT,
    nb_defaites        INT,
    kda                DECIMAL(5,2),
    precision_tirs     DECIMAL(5,2),
    score_perf         DECIMAL(5,2),
    humeur             TINYINT CHECK (humeur BETWEEN 1 AND 10),
    focus              TINYINT CHECK (focus BETWEEN 1 AND 10),
    fatigue_mentale    TINYINT CHECK (fatigue_mentale BETWEEN 1 AND 10),
    clarte_reaction    TINYINT CHECK (clarte_reaction BETWEEN 1 AND 10),
    plainte_physique   TEXT,
    probleme_technique TEXT,
    notes_libres       TEXT,
    CONSTRAINT fk_logs_joueur FOREIGN KEY (joueur_id) REFERENCES joueurs(joueur_id),
    UNIQUE KEY unique_log_jour (joueur_id, date_log)
) ENGINE=InnoDB;

/* ---- 7. OBJECTIFS HEBDOMADAIRES JOUEURS ---- */
CREATE TABLE objectifs_joueurs (
    objectif_id    INT AUTO_INCREMENT PRIMARY KEY,
    joueur_id      INT NOT NULL,
    semaine_debut  DATE NOT NULL,
    description    TEXT NOT NULL,
    metrique_cible VARCHAR(100),
    statut         ENUM('En cours','Atteint','Echoue','Reporte') DEFAULT 'En cours',
    date_cloture   DATE,
    CONSTRAINT fk_objj_joueur FOREIGN KEY (joueur_id) REFERENCES joueurs(joueur_id)
) ENGINE=InnoDB;

/* ---- 8. EVALUATIONS COACH ---- */
CREATE TABLE evaluations_coach (
    eval_id             INT AUTO_INCREMENT PRIMARY KEY,
    joueur_id           INT NOT NULL,
    evaluateur          VARCHAR(100),
    date_eval           DATE NOT NULL,
    periode             VARCHAR(50),
    discipline          TINYINT CHECK (discipline BETWEEN 1 AND 10),
    communication       TINYINT CHECK (communication BETWEEN 1 AND 10),
    execution_mecanique TINYINT CHECK (execution_mecanique BETWEEN 1 AND 10),
    vitesse_adaptation  TINYINT CHECK (vitesse_adaptation BETWEEN 1 AND 10),
    score_global        DECIMAL(4,2),
    commentaire         TEXT,
    CONSTRAINT fk_eval_joueur FOREIGN KEY (joueur_id) REFERENCES joueurs(joueur_id)
) ENGINE=InnoDB;

/* ---- 9. ANALYSES POST-MATCH ---- */
CREATE TABLE analyses_match (
    analyse_id        INT AUTO_INCREMENT PRIMARY KEY,
    tournoi_id        INT,
    equipe_id         INT NOT NULL,
    date_match        DATE NOT NULL,
    adversaire        VARCHAR(100),
    resultat          ENUM('Victoire','Defaite','Nul'),
    notes_tactiques   TEXT,
    points_faibles    TEXT,
    points_forts      TEXT,
    axes_amelioration TEXT,
    CONSTRAINT fk_am_tournoi FOREIGN KEY (tournoi_id) REFERENCES tournois(tournoi_id),
    CONSTRAINT fk_am_equipe  FOREIGN KEY (equipe_id)  REFERENCES equipes(equipe_id)
) ENGINE=InnoDB;

/* ---- 10. OBJECTIFS EQUIPE ---- */
CREATE TABLE objectifs_equipe (
    obj_equipe_id INT AUTO_INCREMENT PRIMARY KEY,
    equipe_id     INT NOT NULL,
    description   TEXT NOT NULL,
    deadline      DATE,
    statut        ENUM('En cours','Atteint','Echoue') DEFAULT 'En cours',
    CONSTRAINT fk_obje_equipe FOREIGN KEY (equipe_id) REFERENCES equipes(equipe_id)
) ENGINE=InnoDB;

/* ---- 11. TRAINING PLANS (Staff Layer) ---- */
CREATE TABLE training_plans (
    plan_id            INT AUTO_INCREMENT PRIMARY KEY,
    equipe_id          INT NOT NULL,
    date_debut_plan    DATE NOT NULL,
    objectif_quotidien TEXT,
    variation_tactique TEXT,
    notes              TEXT,
    CONSTRAINT fk_tp_equipe FOREIGN KEY (equipe_id) REFERENCES equipes(equipe_id)
) ENGINE=InnoDB;

/* ---- 12. MATCH TELEMETRY (P3) ---- */
CREATE TABLE match_telemetry (
    telemetry_id         INT AUTO_INCREMENT PRIMARY KEY,
    joueur_id            INT NOT NULL,
    analyse_id           INT DEFAULT NULL,
    date_match           DATE NOT NULL,
    kills                INT DEFAULT 0,
    deaths               INT DEFAULT 0,
    assists              INT DEFAULT 0,
    degats_infliges      INT DEFAULT 0,
    degats_subis         INT DEFAULT 0,
    precision_tirs_match DECIMAL(5,2),
    temps_survie_sec     INT,
    objectifs_captures   INT DEFAULT 0,
    resultat_match       ENUM('Victoire','Defaite','Nul'),
    CONSTRAINT fk_mt_joueur  FOREIGN KEY (joueur_id)  REFERENCES joueurs(joueur_id),
    CONSTRAINT fk_mt_analyse FOREIGN KEY (analyse_id) REFERENCES analyses_match(analyse_id)
) ENGINE=InnoDB;

/* ---- 13. PLAYER RANKING (P4 — reecrite a chaque calcul) ---- */
CREATE TABLE player_ranking (
    ranking_id         INT AUTO_INCREMENT PRIMARY KEY,
    joueur_id          INT NOT NULL,
    tag_ingame         VARCHAR(50) NOT NULL,
    tier               VARCHAR(50),
    role               VARCHAR(50),
    B2R_SCORE          DECIMAL(5,2),
    winrate_pct        DECIMAL(5,1),
    kda_moyen          DECIMAL(5,2),
    kda_std            DECIMAL(5,2),
    precision_moyenne  DECIMAL(5,1),
    ratio_degats_moyen DECIMAL(5,2),
    score_psycho       DECIMAL(5,2),
    heures_training_moy DECIMAL(5,2),
    date_calcul        DATE NOT NULL DEFAULT (CURDATE()),
    CONSTRAINT fk_pr_joueur FOREIGN KEY (joueur_id) REFERENCES joueurs(joueur_id)
) ENGINE=InnoDB;
