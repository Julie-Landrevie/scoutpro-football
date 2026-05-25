# ⚽ ScoutPro — Player Intelligence Platform

> Football player scouting & profiling platform powered by StatsBomb Open Data  
> **Julie Landrevie · Football Data & Video Analyst**
---

## Aperçu

ScoutPro est une interface de recrutement football data-driven inspirée des cartes FIFA permettant de :

- 🔍 **Rechercher** des joueurs selon position, club, nationalité, âge, note globale, dispositif tactique et ouverture au transfert
- 📊 **Profiler** chaque joueur avec une fiche style carte FIFA : radar d'attributs, barres PAC/TIR/PAS/DRI/DEF/PHY, points forts & faibles, systèmes adaptés
- 🎯 **Matcher** des profils selon le style de jeu de son équipe (possession, contre-attaque, pressing haut, bloc bas, jeu direct, transitions)
- 💶 **Estimer** la valeur marchande et la probabilité d'ouverture à une transaction
- 📈 **Comparer** deux joueurs d'une même position côte à côte via un radar superposé
  
🌐 **App en ligne :** [scoutpro-football.streamlit.app](https://scoutpro-football.streamlit.app)
---

## Données

| Source | Compétitions | Joueurs |
|--------|-------------|---------|
| StatsBomb Open Data | UEFA Euro 2024 & 2020 · FIFA World Cup 2022 & 2018 · Copa America 2024 · AFCON 2023 · La Liga (6 saisons) · Ligue 1 (3 saisons) · Bundesliga (2 saisons) · Champions League (2 saisons) · Premier League · Serie A · MLS | **2 263 joueurs uniques** |

Attributs calculés à partir des données brutes : PAC · TIR · PAS · DRI · DEF · PHY + xG · passes progressives · dribbles · pressings · passes clés · assists

---

## Structure du projet

```
scoutpro-football/
├── app.py                # Application Streamlit interactive (dark mode)
├── data_pipeline.py      # Pipeline de collecte StatsBomb → JSON/CSV
├── portfolio.html        # Version portfolio standalone — dark mode, 80 joueurs intégrés
├── requirements.txt      # Dépendances Python
└── data/
    ├── players.json      # 2 263 joueurs profilés
    └── players.csv
```

---

## Installation & lancement

```bash
# Cloner le repo
git clone https://github.com/Julie-Landrevie/scoutpro-football.git
cd scoutpro-football

# Installer les dépendances
pip install -r requirements.txt

# (Optionnel) Régénérer les données depuis StatsBomb
python data_pipeline.py

# Lancer l'application Streamlit
streamlit run app.py
```

---

## Version portfolio

Ouvrir `portfolio.html` directement dans un navigateur — **aucune installation requise**.  
80 joueurs intégrés en statique, filtres interactifs, matching tactique, dark mode natif.

---

## Fonctionnalités détaillées

### Filtres de recherche
- Nom, position, club, nationalité
- Note minimale (55–97)
- Tranche d'âge (17–40 ans)
- Dispositif tactique (4-3-3, 4-4-2, 4-2-3-1, 3-5-2, 3-4-3, 5-3-2)
- Ouverture au transfert (probable / incertain / peu probable)
- Stats avancées : buts minimum, xG minimum

### Fiche joueur
- Carte style FIFA avec note globale et 6 attributs
- Radar Plotly interactif
- Barres d'attributs colorées selon le niveau
- Tags points forts / points faibles / systèmes
- Formations compatibles avec meilleur dispositif mis en avant
- Compétitions couvertes

### Matching tactique
Sélectionner son style de jeu et sa formation → le moteur pondère les attributs selon le profil tactique et retourne le **top 5 des joueurs** les plus adaptés avec un score de compatibilité en %.

| Style | Attributs prioritaires |
|-------|----------------------|
| Possession / jeu court | Passe · Physique · Défense |
| Contre-attaque | Vitesse · Tir · Dribble |
| Pressing haut | Physique · Défense · Vitesse |
| Jeu direct / long | Physique · Tir · Défense |
| Transitions rapides | Vitesse · Dribble · Tir |
| Bloc bas défensif | Défense · Physique · Passe |

### Comparaison
Sélectionner un deuxième joueur de même position → radar superposé + tableau comparatif attribut par attribut.

---

## Stack technique

```
Python 3.11+
pandas · numpy · statsbombpy
Streamlit · Plotly · mplsoccer · matplotlib
Git · GitHub
```

---

## Certifications & formation

- 🎓 Sports Analytics — University of Michigan (Coursera)
- 🎓 Analyse Vidéo et Data dans le Sport — Université de Lorraine
- 🎓 Dartfish Certified Analyst
- 🎓 Once Sport Certified *(in progress)*
- 🎓 Nacsport Certified *(in progress)*

---

📩 julie.landrevie@free.fr
