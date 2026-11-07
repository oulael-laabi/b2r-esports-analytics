"""
============================================================
ESPORTS PERFORMANCE ANALYTICS SYSTEM
Module commun aux notebooks P1 -> P7
Ref : B2R-STU-2026-IPD-01

Objectif : supprimer la duplication entre les notebooks
  - une seule source pour le mapping joueur_id -> tag / role / tier
  - une seule fonction de normalisation Z-score -> sigmoide
  - le vrai coefficient de stabilite du ranking (Spearman)
  - le backtest du systeme d'alertes (P6)
  - un acces base unifie (MySQL en local, CSV en fallback sur Colab)

Dependances : pandas, numpy, scipy, SQLAlchemy, PyMySQL
============================================================
"""
from __future__ import annotations

import configparser
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_CFG_PATH = ROOT / "config" / "db.ini"
_CFG_EXAMPLE = ROOT / "config" / "db.example.ini"

# echanges inter-notebooks (sorties de P3 lues par P4/P6, etc.)
EXPORTS = ROOT / "data" / "exports"
GENERATED = ROOT / "data" / "generated"
OUTPUTS = ROOT / "outputs"

# tables lisibles directement en fallback CSV
_CSV_TABLES = {
    "joueurs": "data/generated/joueurs.csv",
    "equipes": None,          # reference : pas de CSV -> voir _REFERENCE
    "logs_performance": "data/generated/logs_performance.csv",
    "match_telemetry": "data/generated/match_telemetry.csv",
    "evaluations_coach": "data/generated/evaluations_coach.csv",
}

_REFERENCE_JEUX = pd.DataFrame(
    [(i, n) for i, n in enumerate(
        ["Fortnite", "PUBG Mobile", "Valorant", "FC Mobile", "EA FC 25",
         "Mobile Legends", "Free Fire", "Street Fighter", "Call of Duty", "eFootball"], 1)],
    columns=["jeu_id", "nom"])

# equipes de reference (miroir de sql/02_seed_reference.sql) pour le mode CSV
_REFERENCE_EQUIPES = pd.DataFrame([
    (1, "B2R Fortnite",       1, "Main Roster"),
    (2, "B2R PUBG Mobile",    2, "Main Roster"),
    (3, "B2R Valorant",       3, "Main Roster"),
    (4, "B2R FC Mobile",      4, "Main Roster"),
    (5, "B2R Mobile Legends", 6, "Main Roster"),
    (6, "B2R Free Fire",      7, "Academy"),
], columns=["equipe_id", "nom", "jeu_id", "tier"])


# ------------------------------------------------------------------
# Configuration / acces base
# ------------------------------------------------------------------
def _load_cfg() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(_CFG_PATH if _CFG_PATH.exists() else _CFG_EXAMPLE)
    return cfg


def get_engine():
    """Retourne un engine SQLAlchemy, ou None si on doit utiliser le fallback CSV."""
    cfg = _load_cfg()
    if cfg.getboolean("options", "use_csv_fallback", fallback=True):
        return None
    try:
        from sqlalchemy import create_engine
        m = cfg["mysql"]
        url = (f"mysql+pymysql://{m['user']}:{m.get('password','')}"
               f"@{m['host']}:{m.get('port','3306')}/{m['database']}")
        eng = create_engine(url)
        eng.connect().close()
        return eng
    except Exception as exc:  # pragma: no cover
        print(f"[b2r_common] connexion MySQL impossible ({exc}) -> fallback CSV")
        return None


def load_table(name: str) -> pd.DataFrame:
    """Charge une table depuis MySQL si dispo, sinon depuis le CSV correspondant."""
    eng = get_engine()
    if eng is not None:
        return pd.read_sql(f"SELECT * FROM {name}", eng)

    if name == "equipes":
        return _REFERENCE_EQUIPES.copy()
    if name == "jeux":
        return _REFERENCE_JEUX.copy()
    rel = _CSV_TABLES.get(name)
    if rel is None:
        raise KeyError(f"Pas de fallback CSV pour la table '{name}'")
    path = ROOT / rel
    if not path.exists():
        raise FileNotFoundError(
            f"{path} introuvable. Lancer d'abord : python scripts/generate_dataset.py")
    return pd.read_csv(path)


# ------------------------------------------------------------------
# Dimension joueur (remplace les dict {1:'VEGA_X', ...} dupliques)
# ------------------------------------------------------------------
def player_dim() -> pd.DataFrame:
    """
    joueur_id, tag_ingame, role_tactique, equipe, tier, source_donnee
    Source unique de verite pour tous les notebooks.
    """
    j = load_table("joueurs")
    e = load_table("equipes")[["equipe_id", "nom", "tier"]].rename(
        columns={"nom": "equipe"})
    dim = j.merge(e, on="equipe_id", how="left")
    cols = ["joueur_id", "tag_ingame", "role_tactique", "equipe", "tier"]
    if "source_donnee" in dim.columns:
        cols.append("source_donnee")
    return dim[cols].sort_values("joueur_id").reset_index(drop=True)


# ------------------------------------------------------------------
# Normalisation (P4)
# ------------------------------------------------------------------
def zscore_sigmoid(serie: pd.Series) -> pd.Series:
    """Z-score puis sigmoide -> [0,1]. Robuste, mais degenere si n < 4."""
    serie = pd.to_numeric(serie, errors="coerce")
    sd = serie.std(ddof=0)
    if sd == 0 or np.isnan(sd):
        return pd.Series(0.5, index=serie.index)
    z = (serie - serie.mean()) / sd
    return np.round(1.0 / (1.0 + np.exp(-z)), 4)


# ------------------------------------------------------------------
# Coefficient de stabilite du ranking (P4) — vraie definition
# ------------------------------------------------------------------
def ranking_stability(df_logs: pd.DataFrame,
                      score_col: str = "score_perf",
                      id_col: str = "joueur_id",
                      date_col: str = "date_log") -> dict:
    """
    Mesure a quel point le classement des joueurs reste coherent quand on
    le calcule sur deux moities temporelles de la fenetre de donnees.

    Retourne le coefficient de Spearman entre les deux classements
    (1 = classement parfaitement stable, KPI cible > 0.85).
    """
    from scipy.stats import spearmanr

    d = df_logs.copy()
    d[date_col] = pd.to_datetime(d[date_col])
    median_day = d[date_col].quantile(0.5)
    first = d[d[date_col] <= median_day]
    second = d[d[date_col] > median_day]

    r1 = first.groupby(id_col)[score_col].mean().rank(ascending=False)
    r2 = second.groupby(id_col)[score_col].mean().rank(ascending=False)
    common = r1.index.intersection(r2.index)
    rho, p = spearmanr(r1.loc[common], r2.loc[common])
    return {
        "stability_coeff": round(float(rho), 4),
        "p_value": round(float(p), 4),
        "n_joueurs": int(len(common)),
        "kpi_atteint": bool(rho > 0.85),
    }


# ------------------------------------------------------------------
# Backtest du systeme d'alertes (P6)
# ------------------------------------------------------------------
# seuils pour les DEFICITS de performance (P3 / rapport hebdo)
DEFAULT_THRESHOLDS = dict(fatigue=6.5, focus=6.0, kda=1.8, winrate=45.0, precision=60.0)


def _wellbeing_alert(d: pd.DataFrame) -> pd.Series:
    """
    Regle d'alerte "risque d'incident" : deterioration psychometrique soutenue.
    Un incident (blessure, latence, souci technique) suit generalement une
    baisse de bien-etre -> on surveille fatigue / focus / clarte, avec une
    condition de persistance sur 2 jours pour limiter les faux positifs.
    """
    d = d.sort_values(["joueur_id", "date_log"])
    jour = (d["fatigue_mentale"] >= 6) | \
           ((d["fatigue_mentale"] >= 5) & (d["focus"] <= 5)) | \
           (d["focus"] <= 4)
    veille = jour.groupby(d["joueur_id"]).shift(1, fill_value=False)
    return (jour | veille)  # se declenche le jour de la baisse et le lendemain


def backtest_alerts(df_logs: pd.DataFrame,
                    incidents: pd.DataFrame,
                    thresholds: dict | None = None,
                    horizon_days: int = 2,
                    alert_rule=None) -> dict:
    """
    Compare les alertes "risque d'incident" du systeme aux incidents
    "verite terrain" (data/generated/incidents_ground_truth.csv).

    - `alert_rule(d) -> Series[bool]` : regle testee (defaut : _wellbeing_alert).
    - Un jour-joueur est VRAI positif si un incident survient ce jour-la ou
      dans les `horizon_days` jours SUIVANTS pour le meme joueur.

    Retourne precision / rappel / accuracy / F1 mesures (et non simules).
    """
    rule = alert_rule or _wellbeing_alert
    d = df_logs.copy()
    d["date_log"] = pd.to_datetime(d["date_log"])
    d = d.sort_values(["joueur_id", "date_log"]).reset_index(drop=True)
    d["alerte"] = rule(d).to_numpy()

    inc = incidents.copy()
    inc["date_log"] = pd.to_datetime(inc["date_log"])
    inc_set = set(zip(inc["joueur_id"], inc["date_log"].dt.date))

    def has_incident(row):
        for k in range(horizon_days + 1):
            if (row["joueur_id"], (row["date_log"] + pd.Timedelta(days=k)).date()) in inc_set:
                return True
        return False

    d["incident_proche"] = d.apply(has_incident, axis=1)

    tp = int((d["alerte"] & d["incident_proche"]).sum())
    fp = int((d["alerte"] & ~d["incident_proche"]).sum())
    fn = int((~d["alerte"] & d["incident_proche"]).sum())
    tn = int((~d["alerte"] & ~d["incident_proche"]).sum())

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    accuracy = (tp + tn) / len(d) if len(d) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "n_jours": int(len(d)), "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "precision": round(precision * 100, 1),
        "rappel": round(recall * 100, 1),
        "accuracy": round(accuracy * 100, 1),
        "f1": round(f1 * 100, 1),
        "kpi_accuracy_atteint": bool(accuracy * 100 > 90),
    }


def write_export(df: pd.DataFrame, name: str) -> Path:
    """Persiste une sortie de notebook dans data/exports/<name>.csv."""
    EXPORTS.mkdir(parents=True, exist_ok=True)
    path = EXPORTS / f"{name}.csv"
    df.to_csv(path, index=False)
    return path


def read_export(name: str) -> pd.DataFrame:
    path = EXPORTS / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} manquant. Exécuter le notebook amont d'abord.")
    return pd.read_csv(path)


def ranking_to_sql(df_ranking: pd.DataFrame) -> Path:
    """
    Genere data/exports/99_finalize_db.sql : un SEUL fichier a importer dans
    phpMyAdmin apres run_pipeline.py. Il contient :
      - TRUNCATE + INSERT de player_ranking
      - la (re)creation des 4 vues Studio (contenu de sql/05_views.sql)
    """
    cols = ["joueur_id", "tag_ingame", "tier", "role", "B2R_SCORE", "winrate_pct",
            "kda_moyen", "kda_std", "precision_moyenne", "ratio_degats_moyen",
            "score_psycho", "heures_training_moy"]
    lines = ["USE b2r_intelligence_db;", "TRUNCATE TABLE player_ranking;",
             "INSERT INTO `player_ranking` (`" + "`, `".join(cols) + "`) VALUES"]
    vals = []
    for _, r in df_ranking.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            cells.append("NULL" if pd.isna(v) else
                         (f"'{v}'" if isinstance(v, str) else repr(round(float(v), 2))
                          if isinstance(v, float) else str(v)))
        vals.append("(" + ", ".join(cells) + ")")

    views = (ROOT / "sql" / "05_views.sql").read_text(encoding="utf-8")
    header = ("-- ============================================================\n"
              "-- 99 — FINALISATION DE LA BASE (un seul import)\n"
              "-- A importer APRES sql/00_rebuild_all.sql + scripts/run_pipeline.py\n"
              "-- Contenu : player_ranking (donnees) + 4 vues Studio\n"
              "-- ============================================================\n\n")

    EXPORTS.mkdir(parents=True, exist_ok=True)
    path = EXPORTS / "99_finalize_db.sql"
    path.write_text(header + lines[0] + "\n" + lines[1] + "\n" + lines[2] + "\n"
                    + ",\n".join(vals) + ";\n\n\n" + views, encoding="utf-8")
    return path


if __name__ == "__main__":
    print("player_dim():")
    print(player_dim().to_string(index=False))
