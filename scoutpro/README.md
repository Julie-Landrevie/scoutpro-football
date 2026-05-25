# ScoutPro — Player Intelligence Platform
**Julie Landrevie · Football Data & Video Analyst**

Interface de recrutement et profilage de joueurs de football, style FIFA card, alimentée par StatsBomb Open Data.

## Structure
```
scoutpro/
├── data_pipeline.py   # Collecte & agrégation StatsBomb → JSON/CSV
├── app.py             # Application Streamlit interactive
├── portfolio.html     # Version portfolio statique (standalone)
├── data/
│   ├── players.json   # 551 joueurs profilés
│   └── players.csv
└── requirements.txt
```

## Installation
```bash
pip install -r requirements.txt
```

## Usage
```bash
# 1. Générer/rafraîchir les données
python data_pipeline.py

# 2. Lancer l'app Streamlit
streamlit run app.py

# 3. Version portfolio : ouvrir portfolio.html dans un navigateur
```

## Sources de données
- **StatsBomb Open Data** : UEFA Euro 2024, FIFA World Cup 2022, Copa America 2024, La Liga 2020/21, Ligue 1 2022/23, Bundesliga 2023/24
- **551 joueurs** profilés sur ~30 matchs par compétition
- Attributs calculés : PAC · TIR · PAS · DRI · DEF · PHY + métriques brutes (xG, passes, dribbles, pressings…)

## Fonctionnalités
- 🔍 Recherche multicritères (nom, position, nationalité, club, note, dispositif, ouverture transfert)
- 📊 Carte profil FIFA-like avec radar, barres d'attributs
- ⚡ Points forts / points faibles / systèmes adaptés générés automatiquement
- 💶 Estimation valeur marchande + probabilité de transfert
- 📈 Comparaison entre joueurs même position

## Stack technique
Python · pandas · StatsBomb Open Data · Streamlit · Plotly · mplsoccer
