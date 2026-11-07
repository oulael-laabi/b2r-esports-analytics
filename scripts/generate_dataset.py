#!/usr/bin/env python3
"""
============================================================
ESPORTS PERFORMANCE ANALYTICS SYSTEM
Generateur de jeu de donnees de demonstration
Ref : B2R-STU-2026-IPD-01

But :
    Produire un jeu de donnees coherent avec le schema
    (joueurs / logs_performance / match_telemetry / evaluations_coach)
    de taille suffisante pour que les methodes statistiques des
    modules P3 a P7 soient interpretables :
      - Z-score / sigmoide (P4) : distribution reelle
      - coefficient de stabilite (P4, version Spearman) : classement non trivial
      - regression de tendance (P6) : ~30 points par joueur
      - backtest des alertes (P6) : incidents "verite terrain" connus

Aucune dependance : bibliotheque standard uniquement.

Usage :
    python scripts/generate_dataset.py
    python scripts/generate_dataset.py --players 14 --days 35 --matches 24 --seed 42

Sorties :
    data/generated/joueurs.csv
    data/generated/logs_performance.csv
    data/generated/match_telemetry.csv
    data/generated/evaluations_coach.csv
    data/generated/incidents_ground_truth.csv   (pour le backtest P6)
    data/raw/joueurs_saisie.csv                  (format formulaire, entree du notebook P1)
    sql/03_load_generated_data.sql               (INSERT prets pour phpMyAdmin)
============================================================
"""

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, pstdev

ROOT = Path(__file__).resolve().parents[1]

# ------------------------------------------------------------------
# 1. Definition des joueurs (niveau latent -> pilote toutes les stats)
# ------------------------------------------------------------------
# skill        : 0..1  niveau de jeu global
# consistency  : 0..1  regularite (1 = tres stable d'un jour a l'autre)
# wellbeing    : 0..1  etat mental de base
# trend        : derive quotidienne du bien-etre / de la perf (+ = progression)
# source       : 'reelle' (2 joueurs conserves du projet initial) / 'synthetique'
#
# Les 2 joueurs reels sont pseudonymises dans ce depot public (tags
# remplaces, noms legaux anonymises, dates de naissance generees).
# consistency / wellbeing suivent globalement le niveau, avec des ecarts
# volontaires (joueurs "cas d'ecole" pour le staff) :
#   DRIFT_MA : tres bon mais instable et en declin  -> doit sortir bas du ranking
#   ATLAS7   : niveau correct mais slump marque
#   REZA_ / Yuki_op : niveau modeste mais reguliers et en nette progression
BASE_PLAYERS = [
    # tag,       equipe, jeu, role,      ville,     skill cons  wb   trend   source
    # equipe 1 = B2R Fortnite (Main) · 2 = PUBG (Main) · 3 = Valorant (Main)
    # equipe 6 = B2R Free Fire (Academy)  -> les 5 joueurs "en developpement"
    ("VEGA_X",   1, 1, "IGL",     "Fes",    0.82, 0.82, 0.80, +0.006, "reelle"),
    ("SARA_GG",  3, 3, "Sniper",  "Rabat",  0.76, 0.84, 0.80, +0.004, "synthetique"),
    ("ORYX",     1, 1, "Fragger", "Meknes", 0.68, 0.70, 0.70, +0.003, "reelle"),
    ("DRIFT_MA", 2, 2, "Fragger", "Tanger", 0.71, 0.46, 0.52, -0.010, "synthetique"),
    ("KENZO_B",  2, 2, "IGL",     "Meknes", 0.62, 0.72, 0.68, +0.002, "synthetique"),
    ("ATLAS7",   1, 1, "Flex",    "Fes",    0.59, 0.56, 0.55, -0.008, "synthetique"),
    ("OMZ",      3, 3, "Support", "Fes",    0.55, 0.78, 0.78, +0.004, "synthetique"),
    ("Yuki_op",  6, 7, "Sniper",  "Casa",   0.49, 0.80, 0.80, +0.009, "synthetique"),
    ("Ghost_UIR",6, 7, "Fragger", "Meknes", 0.47, 0.62, 0.62, +0.002, "synthetique"),
    ("REZA__",   6, 7, "Support", "Rabat",  0.43, 0.82, 0.82, +0.010, "synthetique"),
    ("VIPER_ac", 6, 7, "Flex",    "Rabat",  0.41, 0.66, 0.66, +0.004, "synthetique"),
    ("Nael_ff",  6, 7, "IGL",     "Fes",    0.37, 0.58, 0.62, +0.006, "synthetique"),
]

EVALUATORS = [
    # nom,     biais_global, biais_leadership
    ("Symbol", 0.0,  0.0),
    ("MrFall", 0.15, 0.45),   # note un peu plus haut, surtout le leadership
]

PLAINTES_PHYSIQUES = [
    "Legere douleur au poignet droit apres session longue",
    "Fatigue oculaire en fin de session",
    "Tensions dans la nuque, posture a corriger",
    "Maux de tete en fin de journee de scrim",
]
PROBLEMES_TECHNIQUES = [
    "Latence elevee (120ms) pendant les scrims du soir",
    "Micro-coupures reseau en debut de partie",
    "Crash du client a deux reprises pendant les scrims",
    "Souris qui double-clique, materiel a remplacer",
]

COMMENTS = {
    "positif": [
        "Tres bonne periode, progression visible sur les fondamentaux",
        "Excellente regularite, continuer sur cette lancee",
        "Leader naturel, vision du jeu au-dessus de la moyenne",
        "Impact constant en scrim, joueur fiable",
    ],
    "technique": [
        "Doit travailler la precision en situation de duel rapproche",
        "Execution mecanique a renforcer, trop d'erreurs sous pression",
        "KDA en dessous des attentes sur la periode",
        "Prises d'espace trop risquees, revoir le timing des entrees",
    ],
    "mental": [
        "Signes de fatigue en fin de semaine, surveiller la charge",
        "Manque de constance entre les bons et les mauvais jours",
        "Bonne gestion du stress en scrim officiel",
        "Baisse de focus notable sur les sessions du soir",
    ],
    "leadership": [
        "Communication en match a ameliorer, calls trop tardifs",
        "Prise de parole plus assumee en tant que shotcaller",
        "Bon relais des calls de l'IGL, complementaire",
        "Doit structurer les mid-rounds, trop de flottement",
    ],
    "progression": [
        "Maintenir les efforts sur l'entrainement individuel",
        "Objectifs hebdomadaires globalement atteints",
        "Doit formaliser une routine d'echauffement",
        "Bonne assiduite sur les VOD reviews",
    ],
}


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def clampi(x, lo, hi):
    return int(round(clamp(x, lo, hi)))


def gen_logs(players, start, days, rng):
    rows = []
    incidents = []
    log_id = 1
    for pid, p in players:
        for d in range(days):
            day = start + timedelta(days=d)
            # derive centree : moyenne ~ inchangee, pente reelle dans le temps
            drift = p["trend"] * (d - days / 2)
            noise = lambda s: rng.gauss(0, s * (1.0 - 0.6 * p["consistency"]))

            wb = clamp(p["wellbeing"] + drift + rng.gauss(0, 0.06), 0.05, 0.98)
            skill_day = clamp(p["skill"] + drift * 0.5 + noise(0.10), 0.05, 0.98)

            heures = round(clamp(rng.gauss(2.2 + 2.4 * p["skill"], 0.7), 0.5, 6.5), 2)
            nb_parties = clampi(rng.gauss(5 + 7 * skill_day, 2), 2, 15)
            wr = clamp(0.34 + 0.42 * skill_day + noise(0.10), 0.05, 0.95)
            nb_vict = clampi(nb_parties * wr, 0, nb_parties)
            nb_def = nb_parties - nb_vict
            kda = round(clamp(rng.gauss(1.1 + 2.7 * skill_day, 0.25), 0.3, 9.9), 2)
            prec = round(clamp(rng.gauss(52 + 28 * skill_day, 4), 30, 96), 2)
            score = round(clamp(28 + 55 * skill_day + 4 * (kda - 2) + 0.25 * (prec - 65)
                                + rng.gauss(0, 5), 10, 99), 2)

            humeur = clampi(rng.gauss(3 + 6 * wb, 1), 1, 10)
            focus = clampi(rng.gauss(3 + 6 * wb, 1), 1, 10)
            fatigue = clampi(rng.gauss(9 - 6 * wb, 1), 1, 10)
            clarte = clampi(rng.gauss(3 + 6 * wb, 1), 1, 10)

            plainte = probleme = None
            # incident (blessure / fatigue oculaire / souci technique) :
            # cluster de surcharge -> fatigue elevee, surtout apres grosse charge.
            # C'est ce signal que le systeme d'alertes P6 doit apprendre a capter.
            surcharge = fatigue >= 6 or (fatigue >= 5 and heures >= 4.5)
            p_incident = (0.42 if surcharge else 0.02) + 0.03 * (1 - wb)
            if rng.random() < p_incident:
                if rng.random() < 0.5:
                    plainte = rng.choice(PLAINTES_PHYSIQUES)
                    itype = "physique"
                else:
                    probleme = rng.choice(PROBLEMES_TECHNIQUES)
                    itype = "technique"
                # l'incident degrade les metriques du jour
                kda = round(kda * 0.80, 2)
                prec = round(prec * 0.88, 2)
                score = round(score * 0.85, 2)
                focus = clampi(focus - 2, 1, 10)
                fatigue = clampi(fatigue + 2, 1, 10)
                incidents.append({
                    "joueur_id": pid, "date_log": day.isoformat(),
                    "type_incident": itype,
                })

            rows.append({
                "log_id": log_id, "joueur_id": pid, "date_log": day.isoformat(),
                "heures_training": heures, "nb_parties": nb_parties,
                "nb_victoires": nb_vict, "nb_defaites": nb_def,
                "kda": kda, "precision_tirs": prec, "score_perf": score,
                "humeur": humeur, "focus": focus, "fatigue_mentale": fatigue,
                "clarte_reaction": clarte,
                "plainte_physique": plainte, "probleme_technique": probleme,
                "notes_libres": None,
            })
            log_id += 1
    return rows, incidents


ROLE_PROFILE = {  # (kills_base, deaths_base, assists_base, obj_base)
    "Fragger": (16, 8, 4, 2.0),
    "Flex":    (13, 7, 6, 2.5),
    "IGL":     (11, 7, 8, 3.0),
    "Sniper":  (14, 6, 3, 1.5),
    "Support": (7,  6, 11, 3.5),
}


def gen_matches(players, start, days, matches, rng):
    rows = []
    tid = 1
    for pid, p in players:
        kb, db, ab, ob = ROLE_PROFILE[p["role"]]
        for _ in range(matches):
            day = start + timedelta(days=rng.randint(0, days - 1))
            sk = clamp(p["skill"] + rng.gauss(0, 0.12 * (1.4 - p["consistency"])), 0.05, 0.98)
            kills = clampi(rng.gauss(kb * (0.55 + sk), kb * 0.20), 0, 40)
            deaths = clampi(rng.gauss(db * (1.4 - sk), 1.5), 1, 16)
            assists = clampi(rng.gauss(ab * (0.6 + sk), 1.7), 0, 20)
            prec = round(clamp(rng.gauss(52 + 28 * sk, 6), 28, 96), 2)
            dmg_in = clampi(kills * 155 + rng.gauss(400, 250), 300, 6000)
            dmg_out = clampi(deaths * 250 + rng.gauss(600, 250), 300, 5000)
            survie = clampi(rng.gauss(550 + 550 * sk, 160), 180, 1500)
            obj = clampi(rng.gauss(ob * (0.5 + sk), 1.2), 0, 6)
            wr = clamp(0.34 + 0.42 * sk, 0.05, 0.95)
            r = rng.random()
            res = "Victoire" if r < wr else ("Nul" if r < wr + 0.05 else "Defaite")
            rows.append({
                "telemetry_id": tid, "joueur_id": pid, "analyse_id": None,
                "date_match": day.isoformat(), "kills": kills, "deaths": deaths,
                "assists": assists, "degats_infliges": dmg_in, "degats_subis": dmg_out,
                "precision_tirs_match": prec, "temps_survie_sec": survie,
                "objectifs_captures": obj, "resultat_match": res,
            })
            tid += 1
    rows.sort(key=lambda x: (x["date_match"], x["joueur_id"]))
    for i, row in enumerate(rows, 1):
        row["telemetry_id"] = i
    return rows


OBJECTIFS = [
    ("Maintenir plus de 70% de precision sur 5 matchs consecutifs", "precision_tirs >= 70"),
    ("Ameliorer le KDA moyen au-dessus de 2.5 sur la semaine", "kda >= 2.5"),
    ("Reduire le temps de reaction en duel rapproche", "clarte_reaction >= 8"),
    ("Stabiliser le winrate au-dessus de 60% sur les scrims", "winrate >= 60"),
    ("Limiter les morts en early game a moins de 2 par match", "deaths_early <= 2"),
    ("Tenir 4h de training structurees par jour", "heures_training >= 4"),
]


def gen_objectifs(players, start, days, rng):
    rows = []
    oid = 1
    statuts = ["Atteint", "En cours", "En cours", "Echoue", "Reporte"]
    for pid, p in players:
        for k in range(rng.randint(1, 3)):
            desc, metric = rng.choice(OBJECTIFS)
            sem = start + timedelta(days=7 * k)
            st = rng.choice(statuts) if k == 0 else "En cours"
            rows.append({
                "objectif_id": oid, "joueur_id": pid,
                "semaine_debut": sem.isoformat(), "description": desc,
                "metrique_cible": metric, "statut": st,
                "date_cloture": (sem + timedelta(days=6)).isoformat() if st in ("Atteint", "Echoue") else None,
            })
            oid += 1
    return rows


def gen_evaluations(players, start, days, rng):
    rows = []
    eid = 1
    # 3 periodes bi-hebdomadaires
    periodes = [
        (start + timedelta(days=10), "Bi-hebdo 1"),
        (start + timedelta(days=24), "Bi-hebdo 2"),
        (start + timedelta(days=days - 2), "Bi-hebdo 3"),
    ]
    for pid, p in players:
        for (dt, label) in periodes:
            for (ev_name, bias, lead_bias) in EVALUATORS:
                disc = clampi(rng.gauss(4 + 5.5 * p["skill"] + bias, 0.7), 1, 10)
                comm = clampi(rng.gauss(4 + 5.0 * p["skill"] + bias + lead_bias, 0.8), 1, 10)
                mech = clampi(rng.gauss(3.5 + 6.0 * p["skill"] + bias, 0.8), 1, 10)
                adap = clampi(rng.gauss(4 + 5.5 * p["skill"] + bias, 0.8), 1, 10)
                score_g = round(mean([disc, comm, mech, adap]) + rng.gauss(0, 0.2), 2)

                cats = []
                if p["skill"] >= 0.65:
                    cats.append("positif")
                if mech <= 6:
                    cats.append("technique")
                if p["wellbeing"] <= 0.63 or p["trend"] < 0:
                    cats.append("mental")
                if p["role"] in ("IGL", "Flex") or comm <= 6:
                    cats.append("leadership")
                if not cats or rng.random() < 0.4:
                    cats.append("progression")
                comment = " ; ".join(rng.choice(COMMENTS[c]) for c in cats[:2])

                rows.append({
                    "eval_id": eid, "joueur_id": pid, "evaluateur": ev_name,
                    "date_eval": dt.isoformat(), "periode": label,
                    "discipline": disc, "communication": comm,
                    "execution_mecanique": mech, "vitesse_adaptation": adap,
                    "score_global": score_g, "commentaire": comment,
                })
                eid += 1
    return rows


# ------------------------------------------------------------------
# Ecriture CSV + SQL
# ------------------------------------------------------------------
def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r[k]) for k in fieldnames})


def sql_val(v):
    if v is None or v == "":
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'"


def sql_insert(table, rows, cols):
    if not rows:
        return f"-- (aucune ligne pour {table})\n"
    out = [f"INSERT INTO `{table}` (" + ", ".join(f"`{c}`" for c in cols) + ") VALUES"]
    vals = [",\n".join("(" + ", ".join(sql_val(r.get(c)) for c in cols) + ")" for r in rows)]
    return out[0] + "\n" + vals[0] + ";\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--players", type=int, default=12, help="nb de joueurs (max %d)" % len(BASE_PLAYERS))
    ap.add_argument("--days", type=int, default=35, help="nb de jours de logs par joueur")
    ap.add_argument("--matches", type=int, default=22, help="nb de matchs par joueur")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--start", default="2026-05-19", help="date de debut (AAAA-MM-JJ)")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    start = date.fromisoformat(args.start)
    n = min(args.players, len(BASE_PLAYERS))

    players = []
    for i, spec in enumerate(BASE_PLAYERS[:n], start=1):
        tag, eq, jeu, role, ville, skill, cons, wb, trend, source = spec
        players.append((i, {
            "tag": tag, "equipe_id": eq, "jeu_principal": jeu, "role": role,
            "ville": ville, "skill": skill, "consistency": cons,
            "wellbeing": wb, "trend": trend, "source": source,
        }))

    # --- joueurs ---
    joueurs_rows = []
    saisie_rows = []
    for pid, p in players:
        dob = date(rng.randint(2001, 2005), rng.randint(1, 12), rng.randint(1, 28))
        # date d'arrivee : entre janv. 2024 et mars 2026 (toujours anterieure aux logs)
        drej = date(2024, 1, 1) + timedelta(days=rng.randint(0, 790))
        nom = f"Joueur {pid:02d}"   # noms légaux anonymisés (RGPD / rapport public)
        joueurs_rows.append({
            "joueur_id": pid, "nom_legal": nom, "tag_ingame": p["tag"],
            "equipe_id": p["equipe_id"], "jeu_principal": p["jeu_principal"],
            "jeu_secondaire": None, "role_tactique": p["role"],
            "pays": "Maroc", "ville": p["ville"],
            "date_naissance": dob.isoformat(), "date_rejoins": drej.isoformat(),
            "actif": 1, "source_donnee": p["source"],
        })
        saisie_rows.append({
            "nom_legal": nom, "tag_ingame": p["tag"], "equipe_id": p["equipe_id"],
            "jeu_principal": p["jeu_principal"], "role_tactique": p["role"],
            "pays": "Maroc", "ville": p["ville"],
            "date_naissance": dob.isoformat(), "date_rejoins": drej.isoformat(),
        })

    logs_rows, incidents = gen_logs(players, start, args.days, rng)
    match_rows = gen_matches(players, start, args.days, args.matches, rng)
    eval_rows = gen_evaluations(players, start, args.days, rng)
    obj_rows = gen_objectifs(players, start, args.days, rng)

    gen = ROOT / "data" / "generated"
    write_csv(gen / "joueurs.csv", joueurs_rows, list(joueurs_rows[0].keys()))
    write_csv(ROOT / "data" / "raw" / "joueurs_saisie.csv", saisie_rows, list(saisie_rows[0].keys()))

    # fichier "sale" pour demontrer le rejet ETL (P1)
    sc = list(saisie_rows[0].keys())
    dirty = [dict(r) for r in saisie_rows[:6]] + [
        {**saisie_rows[6], "tag_ingame": saisie_rows[0]["tag_ingame"]},          # tag en double
        {**saisie_rows[7], "tag_ingame": "Bad Tag!", "nom_legal": ""},           # tag invalide + nom manquant
        {**saisie_rows[8], "equipe_id": 99},                                     # FK inexistante
        {**saisie_rows[9], "date_naissance": "2030-01-01"},                      # date future
        {**saisie_rows[10], "date_rejoins": "15/03/2026"},                       # mauvais format
    ]
    write_csv(ROOT / "data" / "raw" / "joueurs_saisie_demo_erreurs.csv", dirty, sc)
    write_csv(gen / "logs_performance.csv", logs_rows, list(logs_rows[0].keys()))
    write_csv(gen / "match_telemetry.csv", match_rows, list(match_rows[0].keys()))
    write_csv(gen / "evaluations_coach.csv", eval_rows, list(eval_rows[0].keys()))
    write_csv(gen / "objectifs_joueurs.csv", obj_rows, list(obj_rows[0].keys()))
    write_csv(gen / "incidents_ground_truth.csv", incidents, ["joueur_id", "date_log", "type_incident"])

    # --- SQL ---
    sql = [
        "/* ============================================================",
        "   03 — Chargement du jeu de donnees de demonstration",
        f"   Genere par scripts/generate_dataset.py (seed={args.seed}, "
        f"{n} joueurs, {args.days} jours, {args.matches} matchs/joueur)",
        "   A executer APRES 02_seed_reference.sql",
        "   ============================================================ */",
        "USE b2r_intelligence_db;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "TRUNCATE TABLE evaluations_coach;",
        "TRUNCATE TABLE match_telemetry;",
        "TRUNCATE TABLE logs_performance;",
        "TRUNCATE TABLE objectifs_joueurs;",
        "TRUNCATE TABLE player_ranking;",
        "DELETE FROM joueurs;",
        "ALTER TABLE joueurs AUTO_INCREMENT = 1;",
        "",
        sql_insert("joueurs", joueurs_rows, list(joueurs_rows[0].keys())),
        sql_insert("logs_performance", logs_rows, list(logs_rows[0].keys())),
        sql_insert("match_telemetry", match_rows, list(match_rows[0].keys())),
        sql_insert("evaluations_coach", eval_rows, list(eval_rows[0].keys())),
        sql_insert("objectifs_joueurs", obj_rows, list(obj_rows[0].keys())),
        "SET FOREIGN_KEY_CHECKS = 1;",
        "COMMIT;",
    ]
    data_sql = "\n".join(sql)
    (ROOT / "sql" / "03_load_generated_data.sql").write_text(data_sql, encoding="utf-8")

    # --- fichier tout-en-un : schema + reference + donnees (1 seul import) ---
    schema_sql = (ROOT / "sql" / "01_schema.sql").read_text(encoding="utf-8")
    seed_sql = (ROOT / "sql" / "02_seed_reference.sql").read_text(encoding="utf-8")
    rebuild = (
        "-- ============================================================\n"
        "-- 00 — RECONSTRUCTION COMPLETE DE LA BASE  (UN SEUL IMPORT)\n"
        "-- schema (01) + reference (02) + donnees de demonstration (03)\n"
        "-- Importer ce fichier dans phpMyAdmin, puis : python scripts/run_pipeline.py,\n"
        "-- puis importer data/exports/99_finalize_db.sql\n"
        "-- ============================================================\n\n"
        + schema_sql + "\n\n" + seed_sql + "\n\n" + data_sql + "\n"
    )
    (ROOT / "sql" / "00_rebuild_all.sql").write_text(rebuild, encoding="utf-8")

    # --- verite terrain : classement latent (pour comparer avec P4) ---
    # composite dans l'esprit de la formule B2R (perf + regularite + psycho + progression)
    def composite(p):  # memes poids que la formule B2R_SCORE
        return (0.40 * p["skill"] + 0.25 * p["consistency"]
                + 0.20 * p["wellbeing"] + 0.15 * (0.5 + p["trend"] * 25))

    by_skill = {pid: i for i, (pid, _) in
                enumerate(sorted(players, key=lambda x: x[1]["skill"], reverse=True), 1)}
    latent = sorted(players, key=lambda x: composite(x[1]), reverse=True)
    ranking_truth = [{"rang_latent": i, "rang_skill_pur": by_skill[pid],
                      "joueur_id": pid, "tag_ingame": p["tag"],
                      "latent_composite": round(composite(p), 4),
                      "skill": p["skill"], "consistency": p["consistency"],
                      "wellbeing": p["wellbeing"], "trend": p["trend"]}
                     for i, (pid, p) in enumerate(latent, 1)]
    write_csv(gen / "ranking_latent_truth.csv", ranking_truth, list(ranking_truth[0].keys()))

    # --- resume console ---
    print("=" * 60)
    print("JEU DE DONNEES DE DEMONSTRATION GENERE")
    print("=" * 60)
    print(f"Joueurs            : {len(joueurs_rows)}")
    print(f"Logs performance   : {len(logs_rows)}  ({args.days} j x {len(players)})")
    print(f"Matchs (telemetry) : {len(match_rows)}")
    print(f"Evaluations coach  : {len(eval_rows)}")
    print(f"Incidents (verite terrain, pour backtest P6) : {len(incidents)}")
    print()
    print("Classement latent attendu (a comparer avec le B2R_SCORE de P4) :")
    for r in ranking_truth:
        print(f"  {r['rang_latent']:2d}. {r['tag_ingame']:<10} skill={r['skill']:.2f}")
    print()
    print("Fichiers ecrits dans data/generated/, data/raw/ et sql/03_load_generated_data.sql")


if __name__ == "__main__":
    main()
