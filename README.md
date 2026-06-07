# ⚽ ScoutPro — Player Intelligence Platform

> Football player scouting & profiling platform powered by StatsBomb Open Data  
> **Julie Landrevie · Football Data & Video Analyst**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://scoutpro-football.streamlit.app)
[![GitHub](https://img.shields.io/badge/GitHub-Julie--Landrevie-181717?style=flat-square&logo=github)](https://github.com/Julie-Landrevie/scoutpro-football)

---

## Aperçu

ScoutPro est une interface de recrutement football data-driven inspirée des cartes FIFA.  
La **v2** enrichit chaque fiche joueur avec un **Scout Report** basé sur les vraies données StatsBomb — stats avancées, percentiles par groupe de poste, et analyse sur des centaines de matchs réels.

### Fonctionnalités

- 🔍 **Recherche** par position, club, nationalité, âge, note, dispositif tactique, ouverture au transfert
- 📊 **Profil joueur** — fiche FIFA-like, radar d'attributs, barres PAC/TIR/PAS/DRI/DEF/PHY
- 🎯 **Matching tactique** — top 5 profils selon le style de jeu et la formation
- 📈 **Comparaison** — radar superposé entre deux joueurs du même poste
- 💶 **Valeur marchande** — estimation par tranche de niveau + référence manuelle pour 98 stars
- 🔬 **Scout Report** *(v2)* — stats réelles StatsBomb : xG/90, passes progressives, pressing, carries, interceptions, percentiles vs groupe de poste

---

## Scout Report — stats avancées

Pour les joueurs couverts par les données StatsBomb open data (6 343 joueurs enrichis), un onglet **🔬 Scout Report** apparaît avec :

| Catégorie | Métriques |
|-----------|-----------|
| Offensif | xG total · xG/90 · xA/90 · Passes clés/90 · Tirs/90 · Buts |
| Progression | Passes progressives/90 · Carries progressives/90 · Distance portée balle · Passes tiers offensif |
| Pressing & Défense | Pressings/90 · Récupérations/90 · Interceptions/90 · Duels gagnés % |
| Percentiles | Chaque stat comparée aux joueurs du même groupe de poste (ATT / MID / CDM / DEF / GK) |

> ⚠️ Les stats reflètent les matchs couverts par StatsBomb — pas nécessairement une saison complète. Le club affiché correspond à la période couverte, pas au club actuel.

---

## Données

| Source | Compétitions couvertes | Joueurs |
|--------|----------------------|---------|
| StatsBomb Open Data | La Liga 16 saisons (2005-2021) · UCL 11 saisons (2008-2019) · Premier League 2015/16 & 2003/04 · Ligue 1 3 saisons · Bundesliga 2 saisons · Serie A 2015/16 · World Cup 2018 & 2022 · Euro 2020 & 2024 · Copa America 2024 · AFCON 2023 · MLS 2023 | **6 343 joueurs enrichis** |
| Référence manuelle | Valeurs Transfermarkt + notes FIFA approximatives | **98 stars** |

---

## Structure du projet

```
scoutpro-football/
├── app.py                        # Application Streamlit v2
├── data_pipeline.py              # Pipeline StatsBomb → players.json
├── scout_report_pipeline.py      # Enrichissement stats avancées EDF
├── extend_all_data.py            # Enrichissement maximal 43 compétitions
├── compute_percentiles.py        # Calcul percentiles par groupe de poste
├── fix_all.py                    # Correction noms / nationalités / notes
├── apply_reference.py            # Application référence manuelle 98 stars
├── enrich_from_fbref.py          # Enrichissement FBref (soccerdata)
├── requirements.txt
└── data/
    ├── players.json              # 959 joueurs profilés
    ├── players_reference.json    # Référence manuelle 98 stars
    └── enriched/                 # 6 343 fichiers JSON stats avancées
```

---

## Installation & lancement

```bash
git clone https://github.com/Julie-Landrevie/scoutpro-football.git
cd scoutpro-football
pip install -r requirements.txt

# Régénérer les données (optionnel — 30-60 min)
python data_pipeline.py
python extend_all_data.py
python compute_percentiles.py
python apply_reference.py
python fix_all.py

streamlit run app.py
```

---

## Stack technique

```
Python 3.11+ · pandas · numpy · statsbombpy · soccerdata
Streamlit · Plotly · mplsoccer · matplotlib
Git · GitHub · Streamlit Cloud
```

---

## Certifications & formation

- 🎓 Sports Analytics — University of Michigan (Coursera)
- 🎓 Analyse Vidéo et Data dans le Sport — Université de Lorraine
- ✅ Dartfish Certified Analyst
- 🔨 Once Sport Certified *(en cours)*
- 🔨 Nacsport Certified *(en cours)*

---

📩 [julie.landrevie@free.fr](mailto:julie.landrevie@free.fr) · [Portfolio](https://notion.so/julie-landrevie) · [LinkedIn](https://linkedin.com/in/julie-landrevie)
