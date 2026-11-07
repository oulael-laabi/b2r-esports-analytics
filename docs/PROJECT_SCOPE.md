# Périmètre et limites du travail

*Ce document précise le périmètre réel du travail et ses limites. Il complète
le chapitre 6.2 du rapport de projet (« Limites et périmètre du travail »).*

## Ce qui est livré

Un système d'analyse de performance esport **de bout en bout**, de la base
relationnelle jusqu'aux exports Studio, couvrant les 7 livrables du cahier
des charges (P1 à P7).

## Nature des données

Le système est validé sur un **jeu de données de démonstration** :

- **2 joueurs réels** conservés du périmètre initial (`source_donnee = 'reelle'`),
  aux noms légaux anonymisés.
- **10 joueurs synthétiques** générés par `scripts/generate_dataset.py`
  (`source_donnee = 'synthetique'`) : ~35 jours de logs et ~22 matchs chacun.

Les données synthétiques sont produites à partir d'un **niveau de jeu latent**
par joueur (fichier `data/generated/ranking_latent_truth.csv`), plus du bruit
et des incidents. En conséquence, le classement est **stable par
construction** : le coefficient de stabilité mesuré (P4) valide la *cohérence
de la méthode*, pas la stabilité d'un roster réel. La corrélation de ρ ≈ 0,84
entre le classement calculé et ce niveau latent montre en revanche que le
classement retrouve le niveau réel des joueurs.

## KPIs — statut (valeurs mesurées sur le jeu de démo, seed 42)

| KPI | Cible | Résultat mesuré | Statut |
|---|---|---|---|
| P1 – taux d'erreur saisie | < 1 % | 0 % sur le fichier propre ; 45 % sur le fichier de test volontairement erroné (5/11) | **Atteint** — chaque règle démontrée |
| P2 – dashboard | 4 pages | 4 pages, 6 tables MySQL importées (mode Import, actualisation à la demande) | **Atteint** |
| P2 – engagement joueurs | > 90 % | non mesurable dans le périmètre | métrique d'usage produit, hors stage |
| P3 – traitement | < 5 min | ≈ 0,05 s pour 264 matchs | **Atteint** |
| P4 – coeff. stabilité | > 0,85 | **ρ ≈ 0,94** (Spearman entre 2 fenêtres temporelles) ; ρ ≈ 0,84 avec le profil latent | **Atteint** sur données de démo |
| P5 – pipeline coach | agrégation + cross-tab | pipeline livré ; ≈ 75 % des évaluations coach *alignées* avec la performance mesurée | **Atteint** |
| P5 – adoption staff | > 75 % | non mesurable dans le périmètre | métrique organisationnelle, hors stage |
| P6 – fiabilité alertes | accuracy > 90 % | rappel ≈ 71 %, précision ≈ 49 %, **F1 ≈ 58 %**, accuracy ≈ 62 % (réf. base ≈ 85 %) | **Non atteint** — voir ci-dessous |
| P7 – délai de production | −50 % | export JSON instantané vs recherche manuelle, gain non chiffré | **Qualitatif** |

### P6 — pourquoi le KPI « accuracy > 90 % » n'est pas le bon indicateur

Les incidents sont une **classe rare** (~15 % des jours-joueur). Répondre
« pas d'alerte » en permanence donne déjà ~85 % d'accuracy : l'accuracy seule
est donc trompeuse. Le détecteur par seuils implémenté capte **71 % des
incidents** (rappel) au prix de nombreux faux positifs (précision 49 %, F1 58 %).
Atteindre réellement la cible demande un **modèle supervisé** (arbre de décision
ou gradient boosting) entraîné sur les features psychométriques ; c'est la
principale perspective du projet. Par rapport à la version initiale, où la
valeur `accuracy = 92.0` était **codée en dur**, la fiabilité est ici
**mesurée par backtest** contre des incidents connus.

## Ce qui n'est pas réalisé

- **Pas de déploiement** sur BACK2REVENGE.COM : la base et les notebooks tournent
  en local (MySQL/phpMyAdmin + Google Colab / venv). La « plateforme de
  production » est une perspective, pas un livrable.
- **Pas d'ordonnancement automatique** : le pipeline s'exécute à la demande
  (import SQL → notebooks), et le dashboard Power BI s'actualise manuellement.
  Le KPI « ranking mis à jour chaque semaine » suppose un cron ou un
  orchestrateur, non couvert.
- **P5 « NLP »** = catégorisation par mots-clés (pas de modèle de langage).
- **Couche Studio partiellement couverte** : les vues « Player of the Week » et
  « Match Highlights » sont livrées ; « Team of the Month » n'est approché que par
  `v_team_momentum` (état de forme d'équipe, pas un palmarès mensuel) et les
  « Esports Documentaries » ne sont pas traités.
- **Conformité données personnelles incomplète** (loi n° 09-08, CNDP) : les
  indices psychométriques sont des données sensibles. Aucune déclaration CNDP,
  aucune durée de conservation définie, ni mécanisme de consentement ou de droit
  d'accès / suppression : prérequis avant tout déploiement sur le roster réel
  (voir §3.6 du rapport).
