# ⚽ ScoutPro — Player Intelligence Platform

> Football player scouting & profiling platform powered by StatsBomb Open Data  
> **Julie Landrevie · Football Data & Video Analyst**

---

## Aperçu

ScoutPro est une interface de recrutement football data-driven permettant de :
- 🔍 **Rechercher** des joueurs selon position, club, nationalité, âge, note, dispositif tactique, ouverture au transfert
- 📊 **Profiler** chaque joueur avec une fiche style carte FIFA : radar d'attributs, points forts/faibles, systèmes adaptés
- 🎯 **Matcher** des profils selon le style de jeu de son équipe (possession, contre-attaque, pressing haut…)
- 💶 **Estimer** la valeur marchande et la probabilité de transaction
- 📈 **Comparer** deux joueurs d'une même position côte à côte

## Données

| Source | Compétitions | Joueurs |
|--------|-------------|---------|
| StatsBomb Open Data | UEFA Euro 2024 & 2020, FIFA World Cup 2022 & 2018, Copa America 2024, AFCON 2023, La Liga (6 saisons), Ligue 1 (3 saisons), Bundesliga (2 saisons), Champions League (2 saisons), Premier League, Serie A, MLS | **2263 joueurs uniques** |

Attributs calculés : PAC · TIR · PAS · DRI · DEF · PHY + xG, passes progressives, dribbles, pressings, passes clés, assists…

## Structure

```
scoutpro/
├── app.py               # Application Streamlit interactive
├── data_pipeline.py     # Pipeline de collecte StatsBomb → JSON/CSV
├── portfolio.html       # Version portfolio standalone (dark mode)
├── requirements.txt     # Dépendances Python
└── data/
    ├── players.json     # 2263 joueurs profilés
    └── players.csv
```

## Installation & lancement

```bash
pip install -r requirements.txt

# Rafraîchir les données (optionnel — data/ déjà inclus)
python data_pipeline.py

# Lancer l'application
streamlit run app.py
```

## Version portfolio

Ouvrir `portfolio.html` directement dans un navigateur — aucune installation requise.  
80 joueurs intégrés en statique, filtres interactifs, matching tactique, dark mode natif.

## Stack technique

```
Python · pandas · numpy · statsbombpy
Streamlit · Plotly · mplsoccer · matplotlib
Git · GitHub
```

## Certifications & formation

- 🎓 Sports Analytics — University of Michigan (Coursera)
- 🎓 Analyse Vidéo et Data dans le Sport — Université de Lorraine  
- 🎓 Dartfish Certified Analyst
- 📧 julie.landrevie@free.fr
