"""
fix_all.py — Correction complète players.json en une passe
1. Noms : Prénom + Nom (supprime prénoms intermédiaires)
2. Nationalités : base étendue par nom de famille
3. Notes : apply_reference.json en priorité, sinon plafonnement réaliste
4. Ajout des joueurs manquants dans la référence

Usage : python fix_all.py
"""
import json, unicodedata, re
from pathlib import Path

# ── NETTOYAGE NOM ─────────────────────────────────────────────────────────────

MANUAL_NAMES = {
    # Espagne
    'Mikel Oyarzabal Ugarte':          'Mikel Oyarzabal',
    'Ferrán Torres García':            'Ferran Torres',
    'Daniel Olmo Carvajal':            'Dani Olmo',
    'Martín Zubimendi Ibáñez':         'Martín Zubimendi',
    'Robin Aime Robert Le Normand':    'Robin Le Normand',
    'Pau Francisco Torres':            'Pau Torres',
    'Alejandro Balde Martínez':        'Alejandro Balde',
    'Alejandro Baldé Martínez':        'Alejandro Balde',
    'Alejandro Garnacho Ferreyra':     'Alejandro Garnacho',
    'Alejandro Grimaldo García':       'Alejandro Grimaldo',
    'Alexis Alejandro Sánchez Sánchez':'Alexis Sánchez',
    'Álvaro Borja Morata Martín':      'Álvaro Morata',
    'Santiago Cazorla González':       'Santi Cazorla',
    'Ignacio Monreal Eraso':           'Nacho Monreal',
    'Pedro Eliezer Rodríguez Ledesma': 'Pedro',
    'Nacho Fernández Iglesias':        'Nacho',
    'Rodrigo Hernández Cascante':      'Rodri',
    'Marc Cucurella Saseta':           'Marc Cucurella',
    'Mikel Merino Zazón':              'Mikel Merino',
    'Fabián Ruiz Peña':                'Fabián Ruiz',
    'Lamine Yamal Nasraoui Ebana':     'Lamine Yamal',
    'Pedro González López':            'Pedri',
    'Anssumane Fati':                  'Ansu Fati',
    'Sergio Busquets i Burgos':        'Sergio Busquets',
    'Francesc Fàbregas i Soler':       'Cesc Fàbregas',
    'Daniel Carvajal Ramos':           'Dani Carvajal',
    'Jesús Navas González':            'Jesús Navas',
    'Ferran Torres García':            'Ferran Torres',
    # France
    'Kylian Mbappé Lottin':            'Kylian Mbappé',
    'Aurélien Djani Tchouaméni':       'Aurélien Tchouaméni',
    'Dayotchanculle Upamecano':        'Dayot Upamecano',
    'Theo Bernard François Hernández': 'Theo Hernandez',
    'Presnel Kimpembe':                'Presnel Kimpembe',
    'Arnaud Kalimuendo Muinga':        'Arnaud Kalimuendo',
    'Eduardo Camavinga':               'Eduardo Camavinga',
    'Randal Kolo Muani':               'Randal Kolo Muani',
    'Youssouf Fofana':                 'Youssouf Fofana',
    # Portugal
    'Cristiano Ronaldo dos Santos Aveiro': 'Cristiano Ronaldo',
    'Bruno Miguel Borges Fernandes':   'Bruno Fernandes',
    'João Félix Sequeira':             'João Félix',
    'Bernardo Mota Veiga de Carvalho e Silva': 'Bernardo Silva',
    'Rúben Santos Gato Alves Dias':    'Rúben Dias',
    'Vitor Machado Ferreira':          'Vitinha',
    'Marcos Aoás Corrêa':              'Marquinhos',
    'André Filipe Tavares Gomes':      'André Gomes',
    # Argentine
    'Lionel Andrés Messi Cuccittini':  'Lionel Messi',
    'Ángel Fabián Di María Hernández': 'Ángel Di María',
    'Lautaro Javier Martínez':         'Lautaro Martínez',
    'Darwin Gabriel Núñez Ribeiro':    'Darwin Núñez',
    'Alexis Mac Allister':             'Alexis Mac Allister',
    # Allemagne
    'Edmond Fayçal Tapsoba':           'Edmond Tapsoba',
    'Piero Martín Hincapié Reyna':     'Piero Hincapié',
    'Ilkay Gündogan':                  'İlkay Gündoğan',
    'Odilon Kossonou':                 'Odilon Kossonou',
    'Juan Bernat Velasco':             'Juan Bernat',
    # Brésil
    'Alisson Ramsés Becker':           'Alisson',
    'Andreas Hoelgebaum Pereira':      'Andreas Pereira',
    # Angleterre
    'Jude Victor William Bellingham':  'Jude Bellingham',
    'Harry Edward Kane':               'Harry Kane',
    # Maroc
    'Achraf Hakimi Mouh':              'Achraf Hakimi',
    # Divers
    'Victor Okoh Boniface':            'Victor Boniface',
    'Georges Mikautadze':              'Georges Mikautadze',
    'Breel-Donald Embolo':             'Breel Embolo',
    'Luka Jović':                      'Luka Jovic',
    'Hugo Ekitike':                    'Hugo Ekitike',
}

PARTICULES = {'de','di','van','von','le','la','du','mac','mc','al','el',
              'ben','bin','dos','das','da','do','del','della','degli',
              'los','las','san','saint','le','af','av','of','y'}

def clean_name(raw: str) -> str:
    if raw in MANUAL_NAMES:
        return MANUAL_NAMES[raw]
    parts = raw.strip().split()
    if len(parts) <= 2:
        return raw
    prenom = parts[0]
    # Construire le nom de famille : dernier mot, avec particule si présente
    if len(parts) >= 3 and parts[-2].lower() in PARTICULES:
        nom = parts[-2] + ' ' + parts[-1]
    else:
        nom = parts[-1]
    # Éviter doublon (Sánchez Sánchez)
    if len(parts) >= 3 and parts[-1].lower() == parts[-2].lower():
        nom = parts[-1]
    return f"{prenom} {nom}"

# ── NATIONALITÉS ──────────────────────────────────────────────────────────────

NAT_BY_LASTNAME = {
    # France
    'mbappe':'FR','mbappe lottin':'FR','tchouameni':'FR','upamecano':'FR',
    'rabiot':'FR','kante':'FR','griezmann':'FR','dembele':'FR','thuram':'FR',
    'giroud':'FR','coman':'FR','barcola':'FR','camavinga':'FR','fofana':'FR',
    'kolo muani':'FR','saliba':'FR','kounde':'FR','konate':'FR','maignan':'FR',
    'hernandez':'FR','pavard':'FR','varane':'FR','lloris':'FR','mandanda':'FR',
    'lenglet':'FR','zouma':'FR','koscielny':'FR','pogba':'FR','benzema':'FR',
    'martial':'FR','lacazette':'FR','lemar':'FR','fekir':'FR','sissoko':'FR',
    'tolisso':'FR','matuidi':'FR','kimpembe':'FR','veretout':'FR',
    'ndombele':'FR','aouar':'FR','kalimuendo':'FR','cherki':'FR','doue':'FR',
    'olise':'FR','akliouche':'FR','mateta':'FR','lacroix':'FR','gusto':'FR',
    'digne':'FR','zaire-emery':'FR','zaire emery':'FR','ekitike':'FR',
    'nkunku':'FR','camara':'FR','diaby':'FR','guendouzi':'FR','clauss':'FR',
    # Espagne
    'busquets':'ES','pedri':'ES','gavi':'ES','yamal':'ES','olmo':'ES',
    'morata':'ES','rodri':'ES','laporte':'ES','carvajal':'ES','alba':'ES',
    'ramos':'ES','pique':'ES','iniesta':'ES','silva':'ES','navas':'ES',
    'merino':'ES','cucurella':'ES','grimaldo':'ES','balde':'ES',
    'oyarzabal':'ES','zubimendi':'ES','torres':'ES','le normand':'ES',
    'pau torres':'ES','ferran':'ES','asensio':'ES','fabregas':'ES',
    # Allemagne
    'muller':'DE','kimmich':'DE','gundogan':'DE','kroos':'DE','neuer':'DE',
    'hummels':'DE','sane':'DE','musiala':'DE','wirtz':'DE','havertz':'DE',
    'gnabry':'DE','goretzka':'DE','rudiger':'DE','tah':'DE','andrich':'DE',
    'tapsoba':'DE','hincapie':'DE','mittelstadt':'DE','undav':'DE',
    'schlotterbeck':'DE','brandt':'DE','fullkrug':'DE',
    # Portugal
    'ronaldo':'PT','fernandes':'PT','felix':'PT','leao':'PT','dias':'PT',
    'bernardo':'PT','vitinha':'PT','cancelo':'PT','pepe':'PT',
    'guerreiro':'PT','jota':'PT','neves':'PT','ruben':'PT','dalot':'PT',
    # Argentine
    'messi':'AR','di maria':'AR','alvarez':'AR','de paul':'AR',
    'mac allister':'AR','otamendi':'AR','molina':'AR','tagliafico':'AR',
    'romero':'AR','acuna':'AR','garnacho':'AR','dybala':'AR',
    'lautaro':'AR','martinez':'AR','nunez':'AR',
    # Brésil
    'neymar':'BR','vinicius':'BR','rodrygo':'BR','raphinha':'BR',
    'casemiro':'BR','militao':'BR','marquinhos':'BR','alisson':'BR',
    'ederson':'BR','richarlison':'BR','paqueta':'BR','fred':'BR',
    'fabinho':'BR','antony':'BR','endrick':'BR','savinho':'BR',
    # Pays-Bas
    'van dijk':'NL','de jong':'NL','gakpo':'NL','depay':'NL',
    'dumfries':'NL','de ligt':'NL','wijnaldum':'NL','veerman':'NL',
    # Belgique
    'de bruyne':'BE','hazard':'BE','lukaku':'BE','courtois':'BE',
    'tielemans':'BE','carrasco':'BE','dendoncker':'BE','witsel':'BE',
    # Angleterre
    'kane':'EN','bellingham':'EN','saka':'EN','foden':'EN','rice':'EN',
    'trippier':'EN','walker':'EN','maguire':'EN','pickford':'EN',
    'rashford':'EN','mount':'EN','grealish':'EN','sterling':'EN',
    'alexander-arnold':'EN','henderson':'EN','james':'EN','salah':'EG',
    # Italie
    'chiesa':'IT','barella':'IT','verratti':'IT','donnarumma':'IT',
    'bonucci':'IT','chiellini':'IT','immobile':'IT','insigne':'IT',
    'pellegrini':'IT','tonali':'IT','scamacca':'IT','frattesi':'IT',
    'retegui':'IT','raspadori':'IT','bastoni':'IT','dimarco':'IT',
    # Maroc
    'hakimi':'MA','ziyech':'MA','boufal':'MA','en-nesyri':'MA',
    'amrabat':'MA','ounahi':'MA','saiss':'MA','mazraoui':'MA',
    # Croatie
    'modric':'HR','kovacic':'HR','gvardiol':'HR','brozovic':'HR',
    'perisic':'HR','kramaric':'HR','livakovic':'HR','sutalo':'HR',
    # Sénégal
    'mane':'SN','mendy':'SN','gueye':'SN','diatta':'SN','diedhiou':'SN',
    # Serbie
    'vlahovic':'RS','jovic':'RS','milinkovic':'RS','tadic':'RS',
    'kostic':'RS','maksimovic':'RS',
    # Norvège
    'haaland':'NO','odegaard':'NO','sorloth':'NO',
    # Suède
    'ibrahimovic':'SE','isak':'SE','kulusevski':'SE',
    # Autres
    'benzema':'FR','diallo':'SN','coulibaly':'ML',
    'boniface':'NG','osimhen':'NG','lookman':'NG',
    'mikautadze':'GE','kossonou':'CI',
}

def get_nationality(name: str, current: str) -> str:
    if current and current not in ('EU', None, ''):
        return current
    norm = unicodedata.normalize("NFD", name.lower())
    norm = "".join(c for c in norm if unicodedata.category(c) != "Mn")
    for key, nat in NAT_BY_LASTNAME.items():
        if key in norm:
            return nat
    return current or 'EU'

# ── RÉFÉRENCE MANUELLE ────────────────────────────────────────────────────────

def normalize(s):
    s = unicodedata.normalize("NFD", s.lower().strip())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def match_score(a, b):
    wa = set(normalize(a).split())
    wb = set(normalize(b).split())
    if not wa or not wb: return 0
    common = len(wa & wb)
    last = 2 if normalize(a).split()[-1] == normalize(b).split()[-1] else 0
    return (common + last) / (max(len(wa), len(wb)) + 2)

# ── PLAFONNEMENT NOTES ────────────────────────────────────────────────────────

MAX_BY_POS = {
    'GK':88,'CB':86,'LB':85,'RB':85,'LWB':83,'RWB':83,
    'CDM':89,'CM':88,'CAM':89,'LM':84,'RM':84,
    'LW':92,'RW':92,'ST':93,'MID':86,
}

# ── APPLICATION ───────────────────────────────────────────────────────────────

def run():
    with open("data/players.json", encoding="utf-8") as f:
        players = json.load(f)

    # Charger référence si elle existe
    ref_index = {}
    ref_path = Path("data/players_reference.json")
    if ref_path.exists():
        with open(ref_path, encoding="utf-8") as f:
            ref_data = json.load(f)
        for r in ref_data["players"]:
            ref_index[normalize(r["name"])] = r
        print(f"✅ Référence chargée : {len(ref_index)} joueurs")

    names_fixed = nats_fixed = notes_fixed = ref_matched = 0

    for p in players:
        raw = p.get("player", "")

        # 1. Nettoyer le nom
        clean = clean_name(raw)
        if clean != raw:
            p["player"] = clean
            names_fixed += 1

        # 2. Nationalité
        new_nat = get_nationality(p["player"], p.get("nationality", "EU"))
        if new_nat != p.get("nationality"):
            p["nationality"] = new_nat
            nats_fixed += 1

        # 3. Chercher dans la référence (priorité absolue)
        best_ref = None
        best_score = 0.55
        for ref_name, ref in ref_index.items():
            s = match_score(normalize(p["player"]), ref_name)
            if s > best_score:
                best_score = s
                best_ref = ref

        if best_ref:
            p["overall"]      = best_ref["overall"]
            p["market_value"] = best_ref["market_value"]
            p["nationality"]  = best_ref["nationality"]
            p["ref_matched"]  = True
            ref_matched += 1
        else:
            # 4. Plafonner la note si pas dans la référence
            pos = p.get("pos", "MID")
            max_ov = MAX_BY_POS.get(pos, 86)
            if p.get("overall", 0) > max_ov:
                p["overall"] = max_ov
                notes_fixed += 1

    with open("data/players.json", "w", encoding="utf-8") as f:
        json.dump(players, f, ensure_ascii=False, indent=2)

    print(f"\n✅ players.json mis à jour")
    print(f"   Noms corrigés      : {names_fixed}")
    print(f"   Nationalités       : {nats_fixed}")
    print(f"   Référence matchée  : {ref_matched}")
    print(f"   Notes plafonnées   : {notes_fixed}")

    # Vérification
    with open("data/players.json", encoding="utf-8") as f:
        players = json.load(f)

    stars = ["Mbappé","Ronaldo","Messi","Griezmann","Giroud","Kolo Muani",
             "Busquets","Tchouaméni","Bellingham","Haaland","Lenglet","Coman"]
    print("\n🔍 Stars :")
    for p in players:
        if any(s in str(p.get("player","")) for s in stars):
            ref = "✅" if p.get("ref_matched") else "—"
            print(f"  {ref} {p['player']:<30} | {p['pos']:<5} | {p['overall']:>3} | {p['nationality']:<3} | {p['market_value']}")

    print("\n🔝 Top 10 overall :")
    top = sorted(players, key=lambda x: x.get("overall",0), reverse=True)[:10]
    for p in top:
        ref = "✅" if p.get("ref_matched") else "—"
        print(f"  {ref} {p['overall']:>3} | {p['player']:<30} | {p['pos']:<5} | {p['nationality']}")

    # Noms longs restants
    longs = [p.get("player") for p in players if len(str(p.get("player","")).split()) > 2]
    print(f"\nNoms longs restants : {len(longs)}")
    for n in sorted(longs)[:10]:
        print(f"  {n}")

if __name__ == "__main__":
    run()
