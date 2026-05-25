"""
ScoutPro — Application Streamlit de recrutement & profilage
Données : StatsBomb Open Data (data/players.json)
Lancement : streamlit run app.py
"""

import json, ast
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from pathlib import Path

# ── Config page ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ScoutPro | Recrutement Football",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS custom ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Fond général */
[data-testid="stAppViewContainer"] { background: #0a0e1a; }
[data-testid="stSidebar"] { background: #111827 !important; border-right: 1px solid #1e2d45; }
section[data-testid="stSidebar"] * { color: #c9d1e0 !important; }

/* Métriques */
[data-testid="metric-container"] {
    background: #161f30; border: 1px solid #1e2d45; border-radius: 10px; padding: 12px;
}
[data-testid="metric-container"] label { color: #6b7fa3 !important; font-size:12px !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #e8ecf4 !important; }

/* Carte joueur */
.player-card {
    background: linear-gradient(135deg, #1a2a1a 0%, #0d1f0d 50%, #162b16 100%);
    border: 1px solid rgba(0,200,83,0.25); border-radius: 16px; padding: 24px; text-align: center;
}
.overall-badge {
    font-size: 64px; font-weight: 900; color: #ffd700; line-height:1; margin-bottom:4px;
}
.player-title { font-size: 22px; font-weight: 700; color: #fff; letter-spacing:1px; }
.player-sub { font-size: 14px; color: #6b7fa3; margin-top: 4px; }
.pos-badge {
    display: inline-block; background: rgba(0,200,83,0.15); border: 1px solid rgba(0,200,83,0.4);
    color: #00c853; font-size: 12px; font-weight: 700; padding: 3px 12px; border-radius: 20px; letter-spacing:1px; margin-top:8px;
}
.tag-pos  { background:#0d2e1a; border:1px solid #10b981; color:#10b981; border-radius:20px; padding:4px 10px; font-size:12px; margin:3px; display:inline-block; }
.tag-neg  { background:#2e0d0d; border:1px solid #ef4444; color:#ef4444; border-radius:20px; padding:4px 10px; font-size:12px; margin:3px; display:inline-block; }
.tag-sys  { background:#0d1e2e; border:1px solid #3b82f6; color:#60a5fa; border-radius:20px; padding:4px 10px; font-size:12px; margin:3px; display:inline-block; }
.tag-form { background:#1a1a2e; border:1px solid #8b5cf6; color:#a78bfa; border-radius:20px; padding:4px 10px; font-size:12px; margin:3px; display:inline-block; }

/* Section titres */
.section-header {
    font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #4b6080;
    border-bottom: 1px solid #1e2d45; padding-bottom: 8px; margin-bottom: 16px;
}
.transfer-bar { height: 8px; border-radius: 4px; background: linear-gradient(90deg, #ef4444, #f59e0b, #10b981); }
</style>
""", unsafe_allow_html=True)


# ── Chargement données ─────────────────────────────────────────────────────
@st.cache_data
def load_players():
    path = Path("data/players.json")
    if not path.exists():
        st.error("❌ Fichier data/players.json introuvable. Lancez d'abord : python data_pipeline.py")
        st.stop()
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.DataFrame(raw)

    # Parse listes stockées en string
    for col in ['formations','strengths','weaknesses','systems','competitions']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x if isinstance(x, list) else ast.literal_eval(str(x)) if x else [])
    return df


df_all = load_players()

# Déduplique les joueurs (même nom → meilleur overall)
df = df_all.sort_values('overall', ascending=False).drop_duplicates(subset='player').reset_index(drop=True)


# ── Sidebar filtres ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ ScoutPro")
    st.markdown("<div style='color:#4b6080;font-size:11px;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:16px'>Recrutement & Profilage</div>", unsafe_allow_html=True)

    search = st.text_input("🔍 Recherche joueur", placeholder="Nom du joueur…")

    st.markdown("---")
    st.markdown("**Filtres**")

    pos_options = ["Toutes"] + sorted(df['pos'].unique().tolist())
    pos_sel = st.selectbox("Position", pos_options)

    nat_options = ["Toutes"] + sorted(df['nationality'].dropna().unique().tolist())
    nat_sel = st.selectbox("Nationalité", nat_options)

    # Clubs
    clubs = ["Tous"] + sorted(df['team'].dropna().unique().tolist())
    club_sel = st.selectbox("Club", clubs)

    rating_min = st.slider("Note minimale", 55, 97, 65)
    
    # Compétitions
    all_comps = sorted(set(c for comps in df['competitions'] for c in comps))
    comp_sel = st.multiselect("Compétitions", all_comps)

    # Formations
    all_forms = ['4-3-3','4-4-2','4-2-3-1','3-5-2','3-4-3','5-3-2']
    form_sel = st.multiselect("Dispositif tactique", all_forms)

    transfer_options = {"Tous": None, "Probable (>70%)": "high", "Incertain (40-70%)": "med", "Peu probable (<40%)": "low"}
    transfer_label = st.selectbox("Ouverture au transfert", list(transfer_options.keys()))
    transfer_sel = transfer_options[transfer_label]

    st.markdown("---")
    st.markdown("**Stats avancées**")
    min_goals = st.slider("Buts min", 0, 15, 0)
    min_xg = st.slider("xG min", 0.0, 8.0, 0.0, step=0.5)


# ── Filtrage ───────────────────────────────────────────────────────────────
mask = pd.Series([True] * len(df))

if search:
    mask &= df['player'].str.lower().str.contains(search.lower(), na=False)
if pos_sel != "Toutes":
    mask &= df['pos'] == pos_sel
if nat_sel != "Toutes":
    mask &= df['nationality'] == nat_sel
if club_sel != "Tous":
    mask &= df['team'] == club_sel

mask &= df['overall'] >= rating_min
mask &= df['goals'] >= min_goals
mask &= df['xg_total'] >= min_xg

if comp_sel:
    mask &= df['competitions'].apply(lambda x: any(c in x for c in comp_sel))
if form_sel:
    mask &= df['formations'].apply(lambda x: any(f in x for f in form_sel))
if transfer_sel == "high":
    mask &= df['transfer_open'] >= 70
elif transfer_sel == "med":
    mask &= (df['transfer_open'] >= 40) & (df['transfer_open'] < 70)
elif transfer_sel == "low":
    mask &= df['transfer_open'] < 40

filtered = df[mask].reset_index(drop=True)


# ── Layout principal ────────────────────────────────────────────────────────
col_list, col_detail = st.columns([1, 2], gap="medium")

# ── Colonne gauche : liste joueurs ─────────────────────────────────────────
with col_list:
    st.markdown(f"<div class='section-header'>🎯 {len(filtered)} joueurs trouvés</div>", unsafe_allow_html=True)

    if filtered.empty:
        st.info("Aucun joueur ne correspond aux filtres.")
    else:
        # Sélecteur joueur
        player_names = filtered['player'].tolist()
        selected_name = st.selectbox(
            "Sélectionner un joueur",
            player_names,
            format_func=lambda n: f"{n} ({filtered[filtered['player']==n]['pos'].values[0]}) — {filtered[filtered['player']==n]['overall'].values[0]}"
        )
        selected = filtered[filtered['player'] == selected_name].iloc[0]

        # Tableau résumé scrollable
        st.markdown("---")
        st.markdown("<div class='section-header'>Liste des joueurs</div>", unsafe_allow_html=True)
        
        table_df = filtered[['player','pos','team','overall','goals','xg_total','transfer_open']].copy()
        table_df.columns = ['Joueur','Pos','Club','Note','Buts','xG','Transfert%']
        table_df['xG'] = table_df['xG'].round(2)
        st.dataframe(
            table_df,
            hide_index=True,
            use_container_width=True,
            height=350,
            column_config={
                "Note": st.column_config.ProgressColumn("Note", min_value=55, max_value=97, format="%d"),
                "Transfert%": st.column_config.ProgressColumn("Transfert%", min_value=0, max_value=100, format="%d%%"),
            }
        )


# ── Colonne droite : profil joueur ─────────────────────────────────────────
with col_detail:
    if filtered.empty:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.info("Utilisez les filtres pour trouver des joueurs.")
        st.stop()

    p = selected

    # ── Carte FIFA ──────────────────────────────────────────────────────────
    initials = ''.join(w[0] for w in p['player'].split()[:2]).upper()
    comp_str = ' · '.join(p['competitions'][:3])

    st.markdown(f"""
    <div class="player-card">
        <div class="overall-badge">{p['overall']}</div>
        <div style="font-size:40px;font-weight:900;margin:8px 0;color:#8fbb6b">{initials}</div>
        <div class="player-title">{p['player']}</div>
        <div class="player-sub">{p['team']} · {p['nationality']}</div>
        <div class="pos-badge">{p['pos']}</div>
        <br>
        <div style="color:#4b6080;font-size:11px;margin-top:4px">{comp_str}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Métriques clés ──────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("🎯 Buts", int(p['goals']))
    m2.metric("📊 xG", f"{p['xg_total']:.2f}")
    m3.metric("🔑 Passes clés", int(p['key_passes']))
    m4.metric("💶 Valeur", p['market_value'])
    m5.metric("🔄 Transfert", f"{p['transfer_open']}%")

    # ── Tabs ────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Attributs", "⚡ Profil tactique", "💶 Marché", "📈 Comparaison"])

    # ── Tab 1 : Radar + barres ──────────────────────────────────────────────
    with tab1:
        c1, c2 = st.columns(2)

        # Radar chart
        cats = ['Vitesse','Tir','Passe','Dribble','Défense','Physique']
        vals = [p['pace_score'], p['shoot_score'], p['pass_score'],
                p['dribble_score'], p['defense_score'], p['physic_score']]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=cats + [cats[0]],
            fill='toself',
            fillcolor='rgba(0,200,83,0.15)',
            line=dict(color='#00c853', width=2),
            name=p['player'],
        ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor='#0d1f0d',
                radialaxis=dict(visible=True, range=[40, 99], color='#4b6080', gridcolor='#1e2d45'),
                angularaxis=dict(color='#c9d1e0', gridcolor='#1e2d45'),
            ),
            showlegend=False,
            paper_bgcolor='transparent',
            plot_bgcolor='transparent',
            height=300,
            margin=dict(l=40, r=40, t=20, b=20),
        )
        c1.plotly_chart(fig_radar, use_container_width=True)

        # Barres horizontales
        with c2:
            st.markdown("<div class='section-header'>Attributs détaillés</div>", unsafe_allow_html=True)
            attrs = {'Vitesse': p['pace_score'], 'Tir': p['shoot_score'], 'Passe': p['pass_score'],
                     'Dribble': p['dribble_score'], 'Défense': p['defense_score'], 'Physique': p['physic_score']}
            for attr, val in attrs.items():
                color = '#10b981' if val >= 80 else '#3b82f6' if val >= 70 else '#f59e0b' if val >= 60 else '#ef4444'
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                    <div style="width:80px;font-size:12px;color:#6b7fa3">{attr}</div>
                    <div style="flex:1;background:#1a2235;border-radius:3px;height:8px">
                        <div style="width:{val}%;background:{color};height:8px;border-radius:3px;transition:width 0.5s"></div>
                    </div>
                    <div style="width:30px;font-size:13px;font-weight:600;color:#e8ecf4;text-align:right">{val}</div>
                </div>
                """, unsafe_allow_html=True)

        # Stats brutes
        st.markdown("---")
        st.markdown("<div class='section-header'>Stats brutes (données StatsBomb)</div>", unsafe_allow_html=True)
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Passes totales", int(p['passes_total']))
        sc1.metric("Complétion passe", f"{p['pass_completion']*100:.0f}%")
        sc2.metric("Passes progressives", int(p['progressive_passes']))
        sc2.metric("Dribbles tentés", int(p['dribbles_total']))
        sc3.metric("Dribbles réussis", int(p['dribbles_won']))
        sc3.metric("Tirs tentés", int(p.get('shots_total', p['xg_total']/0.12 if p['xg_total']>0 else 0)))
        sc4.metric("Pressings", int(p['pressures']))
        sc4.metric("Assists", int(p['assists']))

    # ── Tab 2 : Profil tactique ─────────────────────────────────────────────
    with tab2:
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("<div class='section-header'>✅ Points forts</div>", unsafe_allow_html=True)
            strengths_html = ''.join(f'<span class="tag-pos">✓ {s}</span>' for s in p['strengths'])
            st.markdown(f"<div>{strengths_html}</div>", unsafe_allow_html=True)

            st.markdown("<br><div class='section-header'>❌ Points faibles</div>", unsafe_allow_html=True)
            weaknesses_html = ''.join(f'<span class="tag-neg">✗ {s}</span>' for s in p['weaknesses'])
            st.markdown(f"<div>{weaknesses_html}</div>", unsafe_allow_html=True)

        with col_b:
            st.markdown("<div class='section-header'>🔷 Systèmes adaptés</div>", unsafe_allow_html=True)
            sys_html = ''.join(f'<span class="tag-sys">◆ {s}</span>' for s in p['systems'])
            st.markdown(f"<div>{sys_html}</div>", unsafe_allow_html=True)

            st.markdown("<br><div class='section-header'>📐 Dispositifs tactiques</div>", unsafe_allow_html=True)
            forms_html = ''.join(
                f'<span class="tag-form">{"★ " if f == p["best_formation"] else ""}{f}</span>'
                for f in p['formations']
            )
            st.markdown(f"<div>{forms_html}</div>", unsafe_allow_html=True)

        # Intégration collective
        st.markdown("---")
        st.markdown("<div class='section-header'>🤝 Intégration collective</div>", unsafe_allow_html=True)
        
        int_score = int((p['pass_score'] + p['physic_score'] + p['defense_score']) / 3)
        pressing_score = min(99, int(p['pressures'] / max(1, df['pressures'].quantile(0.95)) * 99))
        
        st.markdown(f"""
        **Style de jeu suggéré :** {p['systems'][0] if p['systems'] else 'Polyvalent'}  
        **Meilleur dispositif :** {p['best_formation']}  
        **Compétitions couvertes :** {' · '.join(p['competitions'][:4])}
        """)

        col_i1, col_i2, col_i3 = st.columns(3)
        col_i1.metric("Score collectif", f"{int_score}/99")
        col_i2.metric("Pressing index", f"{pressing_score}/99")
        col_i3.metric("Passes clés", int(p['key_passes']))

    # ── Tab 3 : Marché ──────────────────────────────────────────────────────
    with tab3:
        col_m1, col_m2 = st.columns(2)

        with col_m1:
            st.markdown("<div class='section-header'>💶 Estimation de valeur marchande</div>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#161f30;border:1px solid #1e2d45;border-radius:12px;padding:20px;text-align:center">
                <div style="font-size:11px;color:#4b6080;text-transform:uppercase;letter-spacing:1px">Fourchette estimée</div>
                <div style="font-size:36px;font-weight:800;color:#ffd700;margin:8px 0">{p['market_value']}</div>
                <div style="font-size:12px;color:#6b7fa3">Basé sur le profil StatsBomb</div>
            </div>
            """, unsafe_allow_html=True)

        with col_m2:
            st.markdown("<div class='section-header'>🔄 Ouverture au transfert</div>", unsafe_allow_html=True)
            to = p['transfer_open']
            color_t = '#10b981' if to >= 65 else '#f59e0b' if to >= 35 else '#ef4444'
            label_t = 'Probable' if to >= 65 else 'Incertain' if to >= 35 else 'Peu probable'
            st.markdown(f"""
            <div style="background:#161f30;border:1px solid #1e2d45;border-radius:12px;padding:20px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                    <span style="font-size:28px;font-weight:800;color:{color_t}">{to}%</span>
                    <span style="background:{color_t}22;border:1px solid {color_t}55;color:{color_t};border-radius:20px;padding:4px 12px;font-size:12px;font-weight:600">{label_t}</span>
                </div>
                <div style="height:8px;border-radius:4px;background:linear-gradient(90deg,#ef4444,#f59e0b,#10b981);">
                    <div style="width:{to}%;height:8px"></div>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:10px;color:#4b6080;margin-top:4px">
                    <span>Bloqué</span><span>Neutre</span><span>Ouvert</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("<div class='section-header'>📝 Points bloquants potentiels</div>", unsafe_allow_html=True)
        
        blockers = []
        if to < 30: blockers.append("🔴 Club peu enclin à céder le joueur")
        if p['overall'] >= 85: blockers.append("🟡 Prix élevé — négociation complexe")
        if len(p['weaknesses']) >= 3: blockers.append("🟡 Axes d'amélioration importants")
        if to >= 65: blockers.append("🟢 Profil accessible — fenêtre de transfert à saisir")
        
        for b in blockers:
            st.markdown(f"- {b}")

    # ── Tab 4 : Comparaison ─────────────────────────────────────────────────
    with tab4:
        st.markdown("<div class='section-header'>📈 Comparer avec d'autres joueurs</div>", unsafe_allow_html=True)

        same_pos = df[df['pos'] == p['pos']]['player'].tolist()
        compare_options = [pl for pl in same_pos if pl != p['player']]

        if compare_options:
            compare_name = st.selectbox("Comparer avec", compare_options)
            p2 = df[df['player'] == compare_name].iloc[0]

            attrs = ['pace_score','shoot_score','pass_score','dribble_score','defense_score','physic_score']
            labels = ['Vitesse','Tir','Passe','Dribble','Défense','Physique']

            vals1 = [p[a] for a in attrs]
            vals2 = [p2[a] for a in attrs]

            fig_comp = go.Figure()
            fig_comp.add_trace(go.Scatterpolar(r=vals1+[vals1[0]], theta=labels+[labels[0]],
                fill='toself', fillcolor='rgba(0,200,83,0.12)', line=dict(color='#00c853', width=2),
                name=p['player']))
            fig_comp.add_trace(go.Scatterpolar(r=vals2+[vals2[0]], theta=labels+[labels[0]],
                fill='toself', fillcolor='rgba(59,130,246,0.12)', line=dict(color='#3b82f6', width=2),
                name=compare_name))
            fig_comp.update_layout(
                polar=dict(
                    bgcolor='#0d1222',
                    radialaxis=dict(visible=True, range=[40, 99], color='#4b6080', gridcolor='#1e2d45'),
                    angularaxis=dict(color='#c9d1e0', gridcolor='#1e2d45'),
                ),
                legend=dict(bgcolor='transparent', font=dict(color='#c9d1e0')),
                paper_bgcolor='transparent', height=360,
                margin=dict(l=40, r=40, t=20, b=20),
            )
            st.plotly_chart(fig_comp, use_container_width=True)

            # Tableau comparatif
            comp_data = {
                'Attribut': labels + ['Overall','Buts','xG','Passes clés','Transfert%'],
                p['player']: vals1 + [p['overall'], int(p['goals']), round(p['xg_total'],2), int(p['key_passes']), p['transfer_open']],
                compare_name: vals2 + [p2['overall'], int(p2['goals']), round(p2['xg_total'],2), int(p2['key_passes']), p2['transfer_open']],
            }
            st.dataframe(pd.DataFrame(comp_data), hide_index=True, use_container_width=True)
        else:
            st.info(f"Aucun autre joueur en {p['pos']} disponible pour comparer.")


# ── Footer ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#2a3a55;font-size:11px'>"
    "ScoutPro · Données StatsBomb Open Data · Analyse data football"
    "</div>",
    unsafe_allow_html=True
)
