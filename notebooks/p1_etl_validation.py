# %% [markdown]
# # P1 — Player Database System : validation ETL
# **Ref :** B2R-STU-2026-IPD-01
#
# Valide le fichier de saisie des joueurs (formulaire Staff) **avant** insertion
# dans MySQL. Cible du cahier des charges : **taux d'erreur de saisie < 1 %**.
#
# Règles :
# | Contrôle | Type | Effet |
# |---|---|---|
# | `tag_ingame` présent, format `[A-Za-z0-9_]{2,50}`, unique | ERREUR | ligne rejetée |
# | `equipe_id` / `jeu_principal` entier positif **et existant** en base | ERREUR | ligne rejetée |
# | `date_naissance` / `date_rejoins` au format `AAAA-MM-JJ`, non futures | ERREUR | ligne rejetée |
# | âge cohérent (14–40 ans) | ERREUR | ligne rejetée |
# | `nom_legal` manquant | AVERTISSEMENT | ligne conservée, signalée |

# %%
import re
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

sys.path.append(str(Path.cwd().parent / "scripts"))
import b2r_common as b2r

DATE_FMT = "%Y-%m-%d"
TODAY = date(2026, 8, 29)
SAISIE_CSV = b2r.ROOT / "data" / "raw" / "joueurs_saisie.csv"

# %% [markdown]
# ## 1. Chargement du fichier de saisie + des référentiels

# %%
df = pd.read_csv(SAISIE_CSV)
equipes_ok = set(b2r.load_table("equipes")["equipe_id"])
jeux_ok = set(b2r.load_table("jeux")["jeu_id"])
print(f"{len(df)} lignes à valider — {SAISIE_CSV.name}")
print(f"Référentiels : {len(equipes_ok)} équipes, {len(jeux_ok)} jeux")
df.head()

# %% [markdown]
# ## 2. Fonctions de validation

# %%
def v_date(val, champ):
    if pd.isna(val) or str(val).strip() == "":
        return f"{champ} manquante"
    try:
        d = datetime.strptime(str(val).strip(), DATE_FMT).date()
    except ValueError:
        return f"{champ} format invalide (attendu AAAA-MM-JJ) : '{val}'"
    if d > TODAY:
        return f"{champ} dans le futur : {d}"
    return None


def v_fk(val, champ, ref):
    if pd.isna(val):
        return f"{champ} manquant"
    try:
        v = int(val)
    except (ValueError, TypeError):
        return f"{champ} doit être un entier : '{val}'"
    if v <= 0:
        return f"{champ} doit être positif : {v}"
    if v not in ref:
        return f"{champ} = {v} inexistant en base"
    return None


def valider(df):
    tags_vus, err_rows, warn_rows, valid_rows = set(), [], [], []
    for i, row in df.iterrows():
        errs, warns = [], []

        tag = str(row.get("tag_ingame", "")).strip()
        if not tag or tag == "nan":
            errs.append("tag_ingame manquant")
        elif not re.match(r"^[A-Za-z0-9_]{2,50}$", tag):
            errs.append(f"tag_ingame invalide : '{tag}'")
        elif tag in tags_vus:
            errs.append(f"tag_ingame en double : '{tag}'")
        else:
            tags_vus.add(tag)

        if pd.isna(row.get("nom_legal")) or str(row.get("nom_legal")).strip() == "":
            warns.append("nom_legal manquant (recommandé)")

        for champ, ref in [("equipe_id", equipes_ok), ("jeu_principal", jeux_ok)]:
            m = v_fk(row.get(champ), champ, ref)
            if m:
                errs.append(m)

        for champ in ("date_naissance", "date_rejoins"):
            m = v_date(row.get(champ), champ)
            if m:
                errs.append(m)

        try:
            age = (TODAY - datetime.strptime(str(row["date_naissance"]).strip(), DATE_FMT).date()).days / 365.25
            if not (14 <= age <= 40):
                errs.append(f"âge incohérent : {age:.0f} ans")
        except Exception:
            pass

        rec = {"ligne_csv": i + 2, "tag_ingame": tag}
        if errs:
            err_rows.append({**rec, "erreurs": " | ".join(errs)})
        else:
            valid_rows.append(row)
            if warns:
                warn_rows.append({**rec, "avertissements": " | ".join(warns)})
    return pd.DataFrame(valid_rows), pd.DataFrame(err_rows), pd.DataFrame(warn_rows)


# %% [markdown]
# ## 3. Exécution + rapport

# %%
df_valides, df_erreurs, df_warn = valider(df)
n = len(df)
taux = len(df_erreurs) / n * 100 if n else 0

print("=" * 56)
print("RAPPORT DE VALIDATION ETL — B2R PLAYER DATA")
print("=" * 56)
print(f"Lignes totales      : {n}")
print(f"Lignes valides      : {len(df_valides)}")
print(f"Lignes en erreur    : {len(df_erreurs)}")
print(f"Avertissements      : {len(df_warn)} (lignes conservées)")
print(f"Taux d'erreur       : {taux:.2f} %")
print(f"Cible (< 1 %)       : {'OK' if taux < 1 else 'NON ATTEINTE'}")
print("=" * 56)
if len(df_erreurs):
    print(df_erreurs.to_string(index=False))
if len(df_warn):
    print("\nAvertissements :")
    print(df_warn.to_string(index=False))

# %% [markdown]
# ## 4. Export des résultats

# %%
b2r.write_export(df_valides, "joueurs_valides")
b2r.write_export(df_erreurs, "joueurs_erreurs")
b2r.write_export(df_warn, "joueurs_avertissements")
print("→ data/exports/joueurs_valides.csv / joueurs_erreurs.csv / joueurs_avertissements.csv")

# %% [markdown]
# ## 5. Démonstration du rejet (fichier volontairement erroné)
# Montre que chaque règle attrape bien son cas. Fichier :
# `data/raw/joueurs_saisie_demo_erreurs.csv`

# %%
demo = pd.read_csv(b2r.ROOT / "data" / "raw" / "joueurs_saisie_demo_erreurs.csv")
dv, de, dw = valider(demo)
taux_demo = len(de) / len(demo) * 100
print(f"Lignes : {len(demo)} | valides : {len(dv)} | erreurs : {len(de)} "
      f"| taux : {taux_demo:.1f} %  → cible < 1 % : {'OK' if taux_demo < 1 else 'NON ATTEINTE'}")
print(de.to_string(index=False))
if len(dw):
    print("\nAvertissements :")
    print(dw.to_string(index=False))
