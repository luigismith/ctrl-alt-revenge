#!/usr/bin/env python3
"""I livelli in LDtk: crea il progetto dalla legenda e passa le mappe fra LDtk e il testo.

La legenda (tipi di piastrelle, entità e zone) è quella della sessione mappe, in
docs/lore/livelli/legenda-ldtk.md; qui c'è la sua traduzione nel formato di LDtk 1.5.3.

Comandi (dalla radice del repo):

  python tools/ldtk/livelli_ldtk.py crea game/data/platform/prologo.txt game/data/platform/prologo.ldtk
      Crea il progetto LDtk con un livello fatto dalla mappa di testo. Serviva alla prima conversione
      del prologo, quando i testi dei cartelli stavano in game/src/platform/prologue.gd: ora stanno
      nel .ldtk, e il progetto si cambia nell'editor. Non sovrascrive senza --sovrascrivi.

  python tools/ldtk/livelli_ldtk.py txt game/data/platform/prologo.ldtk game/data/platform/prologo.txt
      Riscrive la mappa di testo dal livello LDtk, tenendo i commenti in testa al file. Serve agli
      script della grafica (tools/ambienti/), che leggono ancora il testo.

Il gioco legge il .ldtk da solo (game/src/platform/ldtk_map.gd): questo script non serve per giocare.
Tutto è deterministico: gli iid sono uuid5 dei nomi e gli uid sono numerati in ordine fisso, così
rifare il progetto dallo stesso testo dà lo stesso file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROLOGUE_GD = ROOT / "game/src/platform/prologue.gd"
GREYBOX_PNG = ROOT / "tools/ldtk/greybox.png"

TILE = 20
NS = uuid.UUID("6c1d7a52-2f3b-4c55-9a8e-43a52d0b6c21")  # spazio dei nomi degli iid del progetto

# --- Piastrelle (legenda §3) -------------------------------------------------------------------
# valore, nome, colore nell'editor. Il greybox ha una tessera per valore, nello stesso ordine.
CELLE = [
    (1, "Pieno", "#77757F"),
    (2, "Sottile", "#5F7391"),
    (3, "Bagnato", "#5E8FA8"),
    (4, "Elastico", "#E3D7B0"),
    (5, "Crollo", "#A2552F"),
    (6, "MuroFinto", "#8F8A5A"),
    (7, "Rompibile", "#9A948C"),
    (8, "Vuoto", "#3A0B10"),
    (9, "Elettrico", "#E5CF3A"),
]
VUOTO = 8

# --- Segni della mappa di testo ↔ entità ---------------------------------------------------------
# Le stesse regole stanno in ldtk_map.gd: se cambiano qui, cambiano anche là.
SEGNI_SCENA = {"MIMMO": "M"}

# --- Enum (legenda §4-5 e catalogo-powerup-tossiche.md) ----------------------------------------
ENUM = {
    "ScenaModo": ["su", "passaggio"],
    "BattutaChi": ["tere", "toto", "gig", "persona"],
    "BattutaQuando": ["passaggio", "vista", "dopo_arena"],
    "NemicoTipo": ["rider", "esattore", "noleggiato", "messo", "punk", "bruto", "colomba", "vedetta", "segugio",
                   "ragno"],
    "NemicoStato": ["fermo", "ronda", "agguato", "insegue"],
    "CancelloColore": ["azzurro", "arancio", "viola", "grigio"],
    "OggettoTipo": ["fiori", "chiave"],
    "DaLanciareTipo": ["cassetta", "bidone", "mela", "cestino"],
    "RistoroTipo": ["taralli", "caffe", "panzerotto", "scarcella", "bombola"],
    "PowerUpTipo": ["bomboletta", "abbonamento", "mascherina", "sovraccarico", "giubbotto", "badge", "ombrello"],
    "ArenaFine": ["tutti_ko", "messo_ko", "tempo"],
    "TossicaTipo": ["polvere", "fanghi", "gas", "seno", "nube"],
    "SegretoServe": ["niente", "vista", "spinta", "scatto", "rampino"],
    "TelecameraBlocca": ["niente", "x", "y"],
    "MeteoPioggia": ["no", "inizia", "forte"],
}
ENUM_COLORI = [0xE06666, 0xF6B26B, 0xFFD966, 0x93C47D, 0x76A5AF, 0x6FA8DC, 0x8E7CC3, 0xC27BA0]


# Campo: (nome, tipo, predefinito). Tipi: Int, Float, Bool, String, Enum:<Nome>, Point[], Ref, Ref[].
# Il predefinito None vuol dire «nessuno» (stringa vuota, riferimento vuoto, primo valore dell'enum).
def F(nome, tipo, predef=None, doc=None):
    return (nome, tipo, predef, doc)


# Entità: nome, larghezza, altezza, colore, forma, ridimensionabile, campi, descrizione.
# Le entità puntiformi hanno il perno in basso al centro: messe sulla griglia, il punto cade dove
# cadeva il segno della mappa di testo (centro in basso della cella). Le ridimensionabili e le zone
# hanno il perno in alto a sinistra e coprono celle intere.
ENTITA = [
    ("Partenza", 25, 100, "#4CD964", "Rectangle", False, [
        F("dopo_riavvio", "Bool", False, "la partenza dopo il riavvio (nel prologo: la tastiera del garage)")],
     "Dove comincia GIG. Nel testo: G, e X se dopo_riavvio."),
    ("Ripartenza", 20, 40, "#3DD6F5", "Rectangle", False, [
        F("id", "String"), F("cartello", "Ref?")],
     "Checkpoint: si riparte qui dopo un Vuoto o una vita persa."),
    ("Cartello", 20, 40, "#F5D63D", "Rectangle", False, [
        F("id", "String", None, "la lettera del cartello nella mappa di testo e nel codice"),
        F("titolo", "String"), F("riga", "String"), F("ripartenza", "Bool", True)],
     "Il cartello col titolo e la riga d'aiuto. Se ripartenza, superato coi piedi a terra diventa un checkpoint."),
    ("Uscita", 40, 100, "#FFFFFF", "Rectangle", False, [
        F("prossima", "String")],
     "Fine della mappa. Nel testo: Z."),
    ("Scena", 20, 40, "#E040FB", "Ellipse", False, [
        F("id", "String"), F("modo", "Enum:ScenaModo"), F("una_volta", "Bool", True)],
     "Fa partire una scena a murale. Nel testo: M per MIMMO."),
    ("Battuta", 20, 20, "#B388FF", "Ellipse", False, [
        F("chi", "Enum:BattutaChi"), F("id_testo", "String"), F("quando", "Enum:BattutaQuando")],
     "Una battuta in gioco che non ferma l'azione."),
    ("Nemico", 25, 100, "#FF3B30", "Rectangle", False, [
        F("tipo", "Enum:NemicoTipo"), F("arena", "Ref?", None, "vuoto = fuori dalle arene: solo i droni"),
        F("ondata", "Int", 0), F("stato", "Enum:NemicoStato"), F("percorso", "Point[]"),
        F("si_sveglia_a", "Ref?")],
     "Nemico d'arena, o drone fuori dalle arene (colomba, vedetta, segugio, ragno: legenda §4b)."),
    ("Pannello", 20, 40, "#00E5FF", "Rectangle", False, [
        F("apre", "Ref[]"), F("chiude", "Ref[]"), F("durata_s", "Float", 2.5), F("tenuta_tick", "Int", 30)],
     "Hacking «Collega e corri» (dopo il riavvio)."),
    ("Leva", 20, 20, "#00BFA5", "Rectangle", False, [
        F("apre", "Ref[]"), F("per_sempre", "Bool", True), F("durata_s", "Float", 0.0)],
     "Leva o pulsante: SU per 10 tick, anche col braccio bloccato."),
    ("Cancello", 20, 100, "#FF9500", "Rectangle", True, [
        F("colore", "Enum:CancelloColore"), F("aperto", "Bool", False)],
     "Si apre e si chiude, con un Pannello o una Leva."),
    ("Porta", 40, 100, "#C7A27C", "Rectangle", True, [
        F("si_chiude_dopo", "Bool", True)],
     "La porta che si chiude dietro (il garage). Nel testo: una / per cella."),
    ("Persona", 25, 100, "#FF80AB", "Rectangle", False, [
        F("id", "String"), F("chiede", "String"), F("serve", "Ref?"), F("premio", "Ref[]"), F("ringrazia", "String")],
     "Qualcuno da aiutare."),
    ("Oggetto", 20, 20, "#FFAB40", "Ellipse", False, [
        F("tipo", "Enum:OggettoTipo"), F("per", "Ref?")],
     "Si prende e si usa altrove (SU); uno alla volta, anche col braccio bloccato."),
    ("DaLanciare", 20, 20, "#A1887F", "Rectangle", False, [
        F("tipo", "Enum:DaLanciareTipo")],
     "Cassetta, bidone, mela (arena)."),
    ("Ristoro", 20, 20, "#69F0AE", "Ellipse", False, [
        F("tipo", "Enum:RistoroTipo")],
     "Cibo e bombole."),
    ("PowerUp", 20, 20, "#FFEA00", "Ellipse", False, [
        F("tipo", "Enum:PowerUpTipo"), F("ricompare", "Bool", False)],
     "Effetto a tempo (catalogo-powerup-tossiche.md)."),
    ("Registro", 20, 20, "#90CAF9", "Rectangle", False, [
        F("atto", "Int", 0), F("numero", "Int", 0), F("id_testo", "String")],
     "I 5 registri per atto, li mostra la Vista."),
    ("Firma", 20, 20, "#F48FB1", "Cross", False, [F("numero", "Int", 0)],
     "Le firme di Totò (Tamburi e Isola)."),
    ("Incisione", 20, 20, "#CE93D8", "Cross", False, [F("numero", "Int", 0)],
     "Le «GIG» nelle cupole e nella torre."),
    ("Affaccio", 20, 20, "#80DEEA", "Ellipse", False, [
        F("zoom", "Float", 0.8), F("durata_s", "Float", 2.0)],
     "Dove la telecamera si apre sul panorama."),
]

ZONE = [
    ("Arena", "#FF3B30", [
        F("id", "String"), F("inclinata", "Bool", True), F("corsie", "Int", 3), F("fine", "Enum:ArenaFine"),
        F("ripartenza", "Ref?")],
     "Arena di combattimento. Nel prologo il motore ricava ancora l'arena dal cartello f: questa zona è un riferimento."),
    ("Tossica", "#9CCC65", [
        F("tipo", "Enum:TossicaTipo"), F("danno_s", "Float", 0.0), F("ritardo_s", "Float", 0.0),
        F("ciclo_s", "Float", 0.0, "0 = sempre attiva"), F("attiva_s", "Float", 0.0)],
     "[nuovo] Zona che toglie energia (catalogo-powerup-tossiche.md)."),
    ("Segreto", "#FFD54F", [
        F("nome", "String"), F("serve", "Enum:SegretoServe")],
     "Un segreto: per contarli e controllare che si raggiungano."),
    ("Telecamera", "#4FC3F7", [
        F("blocca", "Enum:TelecameraBlocca"), F("zoom", "Float", 1.0)],
     "Blocca o allarga la telecamera."),
    ("Meteo", "#B0BEC5", [
        F("pioggia", "Enum:MeteoPioggia"), F("vento", "Float", 0.0)],
     "Pioggia e vento."),
]


class Uid:
    def __init__(self) -> None:
        self.n = 0

    def __call__(self) -> int:
        self.n += 1
        return self.n


def iid(*parti: str) -> str:
    return str(uuid.uuid5(NS, "/".join(parti)))


def hex_int(c: str) -> int:
    return int(c.lstrip("#"), 16)


# --- Definizioni ---------------------------------------------------------------------------------

def layer_def(ident: str, kind: str, uid: int, **kw) -> dict:
    d = {
        "__type": kind, "identifier": ident, "type": kind, "uid": uid, "doc": kw.get("doc"), "uiColor": None,
        "gridSize": TILE, "guideGridWid": 0, "guideGridHei": 0, "displayOpacity": kw.get("opacity", 1),
        "inactiveOpacity": kw.get("inactive", 1), "hideInList": False, "hideFieldsWhenInactive": kind == "Entities",
        "canSelectWhenInactive": True, "renderInWorldView": True, "pxOffsetX": 0, "pxOffsetY": 0,
        "parallaxFactorX": 0, "parallaxFactorY": 0, "parallaxScaling": True,
        "requiredTags": kw.get("tags", []), "excludedTags": [], "autoTilesKilledByOtherLayerUid": None,
        "uiFilterTags": [], "useAsyncRender": False, "intGridValues": kw.get("values", []),
        "intGridValuesGroups": [], "autoRuleGroups": kw.get("rules", []),
        "autoSourceLayerDefUid": kw.get("source"), "tilesetDefUid": kw.get("tileset"),
        "tilePivotX": 0, "tilePivotY": 0, "biomeFieldUid": None,
    }
    return d


def field_def(f, uid: int, enums: dict) -> dict:
    nome, tipo, predef, doc = f
    array = tipo.endswith("[]")
    base = tipo[:-2] if array else tipo
    nullable = base.endswith("?")
    base = base.rstrip("?")
    mode, pos, link = "NameAndValue", "Beneath", "StraightArrow"
    if base.startswith("Enum:"):
        e = enums[base[5:]]
        ftype, ttype = f"F_Enum({e['uid']})", f"LocalEnum.{e['identifier']}"
    elif base == "Ref":
        ftype, ttype, nullable = "F_EntityRef", "EntityRef", True
        mode, pos, link = "RefLinkBetweenCenters", "Above", "CurvedArrow"
    elif base == "Point":
        ftype, ttype = "F_Point", "Point"
        mode, pos, link = "PointPath", "Center", "DashedLine"
    else:
        ftype, ttype = {"Int": ("F_Int", "Int"), "Float": ("F_Float", "Float"), "Bool": ("F_Bool", "Bool"),
                        "String": ("F_String", "String")}[base]
    default = None
    if predef is not None:
        vid = {"Int": "V_Int", "Float": "V_Float", "Bool": "V_Bool"}.get(base, "V_String")
        default = {"id": vid, "params": [predef]}
    return {
        "identifier": nome, "doc": doc, "__type": f"Array<{ttype}>" if array else ttype, "uid": uid,
        "type": ftype, "isArray": array, "canBeNull": nullable and not array, "arrayMinLength": None,
        "arrayMaxLength": None, "editorDisplayMode": mode, "editorDisplayScale": 1, "editorDisplayPos": pos,
        "editorLinkStyle": link, "editorDisplayColor": None, "editorAlwaysShow": nome in ("id", "titolo", "tipo"),
        "editorShowInWorld": True, "editorCutLongValues": True, "editorTextSuffix": None, "editorTextPrefix": None,
        "useForSmartColor": False, "exportToToc": False, "searchable": nome in ("id", "titolo"), "min": None,
        "max": None, "regex": None, "acceptFileTypes": None, "defaultOverride": default, "textLanguageMode": None,
        "symmetricalRef": False, "autoChainRef": False, "allowOutOfLevelRef": True, "allowedRefs": "Any",
        "allowedRefsEntityUid": None, "allowedRefTags": [], "tilesetUid": None,
    }


def entity_def(ident, w, h, color, shape, resizable, fields, doc, uid, tag, zone, uids, enums) -> dict:
    corner = resizable or zone
    return {
        "identifier": ident, "uid": uid, "tags": [tag], "exportToToc": False, "allowOutOfBounds": False,
        "doc": doc, "width": w, "height": h, "resizableX": corner, "resizableY": corner,
        "minWidth": TILE if corner else None, "maxWidth": None, "minHeight": TILE if corner else None,
        "maxHeight": None, "keepAspectRatio": False, "tileOpacity": 1, "fillOpacity": 0.15 if zone else 0.6,
        "lineOpacity": 1, "hollow": False, "color": color, "renderMode": shape, "showName": True,
        "tilesetId": None, "tileRenderMode": "FitInside", "tileRect": None, "uiTileRect": None,
        "nineSliceBorders": [], "maxCount": 0, "limitScope": "PerLevel", "limitBehavior": "MoveLastOne",
        "pivotX": 0 if corner else 0.5, "pivotY": 0 if corner else 1,
        "fieldDefs": [field_def(f, uids(), enums) for f in fields],
    }


def build_defs(uids: Uid) -> tuple[dict, dict]:
    enums = {}
    for i, (nome, valori) in enumerate(ENUM.items()):
        enums[nome] = {
            "identifier": nome, "uid": uids(),
            "values": [{"id": v, "tileRect": None, "color": ENUM_COLORI[(i + j) % len(ENUM_COLORI)]}
                       for j, v in enumerate(valori)],
            "iconTilesetUid": None, "externalRelPath": None, "externalFileChecksum": None, "tags": [],
        }
    tileset_uid = uids()
    tileset = {
        "__cWid": len(CELLE), "__cHei": 1, "identifier": "Greybox", "uid": tileset_uid,
        "relPath": None,  # lo mette write_project, relativo al file .ldtk
        "embedAtlas": None, "pxWid": TILE * len(CELLE), "pxHei": TILE, "tileGridSize": TILE,
        "spacing": 0, "padding": 0, "tags": [], "tagsSourceEnumUid": None, "enumTags": [],
        "customData": [], "savedSelections": [], "cachedPixelData": None,
    }
    entities = [entity_def(*e[:7], e[7], uids(), "entita", False, uids, enums) for e in ENTITA]
    entities += [entity_def(z[0], 5 * TILE, 5 * TILE, z[1], "Rectangle", True, z[2], z[3], uids(), "zona", True,
                            uids, enums) for z in ZONE]
    coll_uid, grey_uid, ent_uid, zone_uid = uids(), uids(), uids(), uids()
    rules_group = {
        "uid": uids(), "name": "Greybox", "color": None, "icon": None, "active": True, "isOptional": False,
        "rules": [], "usesWizard": False, "requiredBiomeValues": [], "biomeRequirementMode": 0,
    }
    for i, (v, _n, _c) in enumerate(CELLE):
        rules_group["rules"].append({
            "uid": uids(), "active": True, "size": 1, "tileRectsIds": [[i]], "alpha": 1, "chance": 1,
            "breakOnMatch": True, "pattern": [v], "flipX": False, "flipY": False, "xModulo": 1, "yModulo": 1,
            "xOffset": 0, "yOffset": 0, "tileXOffset": 0, "tileYOffset": 0, "tileRandomXMin": 0,
            "tileRandomXMax": 0, "tileRandomYMin": 0, "tileRandomYMax": 0, "checker": "None",
            "tileMode": "Single", "pivotX": 0, "pivotY": 0, "outOfBoundsValue": None, "invalidated": False,
            "perlinActive": False, "perlinSeed": 1, "perlinScale": 0.2, "perlinOctaves": 2,
        })
    layers = [
        layer_def("Zone", "Entities", zone_uid, tags=["zona"], opacity=1, inactive=0.6,
                  doc="Rettangoli: arene, zone tossiche, segreti, telecamera, meteo."),
        layer_def("Entita", "Entities", ent_uid, tags=["entita"], inactive=0.8,
                  doc="Tutto quello che ha un comportamento o un testo."),
        layer_def("Greybox", "AutoLayer", grey_uid, source=coll_uid, tileset=tileset_uid, rules=[rules_group],
                  doc="Generato da Collisioni: non si disegna a mano."),
        layer_def("Collisioni", "IntGrid", coll_uid, opacity=0.5,
                  values=[{"value": v, "identifier": n, "color": c, "tile": None, "groupUid": 0} for v, n, c in CELLE],
                  doc="Cosa tocca GIG. Tutto il resto è sfondo e si attraversa."),
    ]
    defs = {"layers": layers, "entities": entities, "tilesets": [tileset], "enums": list(enums.values()),
            "externalEnums": [], "levelFields": []}
    return defs, {"tileset": tileset, "rules": rules_group["rules"]}


# --- Mappa di testo ------------------------------------------------------------------------------

def read_txt(path: Path) -> tuple[list[str], list[str]]:
    """Le righe dei commenti in testa e le righe della mappa (come SolidGrid.load_file)."""
    lines = path.read_text(encoding="utf-8").replace("\r", "").split("\n")
    head = [l for l in lines if l.startswith(";")]
    rows = [l for l in lines if not l.startswith(";")]
    while rows and not rows[-1].strip():
        rows.pop()
    w = max(len(r) for r in rows)
    return head, [r.ljust(w, ".") for r in rows]


def prologue_signs() -> tuple[dict, list]:
    """Testi e ripartenze dei cartelli com'erano in prologue.gd prima di LDtk (servono solo alla prima
    conversione: ora i testi stanno nel .ldtk, e prologue.gd tiene solo CHECKPOINT_SIGNS)."""
    src = PROLOGUE_GD.read_text(encoding="utf-8")
    m = re.search(r"const PROLOGUE_SIGNS := \{(.*?)\n\}", src, re.S)
    signs = {}
    if m:
        for k, t, r in re.findall(r'"(\w)": \["([^"]*)", "([^"]*)"\]', m.group(1)):
            signs[k] = (t, r)
    m = re.search(r"const CHECKPOINT_SIGNS: Array\[String\] = \[(.*?)\]", src)
    cps = re.findall(r'"(\w)"', m.group(1)) if m else []
    return signs, cps


def project_signs(project: dict, livello: str | None) -> tuple[dict, list]:
    """Testi e ripartenze dei cartelli di un progetto LDtk già fatto: rifacendolo da capo (per esempio
    quando cambia la legenda) restano quelli scritti nell'editor."""
    signs, cps = {}, []
    for lv in project["levels"]:
        if livello and lv["identifier"] != livello:
            continue
        for li in lv["layerInstances"]:
            for e in li.get("entityInstances", []):
                if e["__identifier"] != "Cartello":
                    continue
                f = {fi["__identifier"]: fi["__value"] for fi in e["fieldInstances"]}
                signs[f["id"]] = (f.get("titolo") or "", f.get("riga") or "")
                if f.get("ripartenza", True):
                    cps.append((e["px"][0], f["id"]))
        break
    return signs, [k for _x, k in sorted(cps)]


def void_cells(rows: list[str]) -> set[tuple[int, int]]:
    """Le celle Vuoto: nelle colonne con l'ultima riga vuota, dal fondo fin dove arriva il terreno
    ai due lati della fossa."""
    h, w = len(rows), len(rows[0])
    solid = lambda x, y: rows[y][x] in "#="
    open_cols = [x for x in range(w) if not solid(x, h - 1)]
    out = set()
    x = 0
    while x < w:
        if x not in open_cols:
            x += 1
            continue
        a = x
        while x < w and x in open_cols:
            x += 1
        b = x - 1

        def top(c):
            if c < 0 or c >= w:
                return h
            y = h - 1
            while y >= 0 and solid(c, y):
                y -= 1
            return y + 1
        y0 = min(top(a - 1), top(b + 1))
        for c in range(a, b + 1):
            for y in range(y0, h):
                if not solid(c, y):
                    out.add((c, y))
    return out


# --- Greybox -------------------------------------------------------------------------------------

def make_greybox(path: Path) -> None:
    """Le 9 tessere del greybox, una per valore di Collisioni, coi segni della legenda §3."""
    from PIL import Image, ImageDraw

    im = Image.new("RGBA", (TILE * len(CELLE), TILE), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    dark = (28, 26, 32, 255)
    for i, (v, _n, col) in enumerate(CELLE):
        x0 = i * TILE
        rgb = tuple(int(col[k:k + 2], 16) for k in (1, 3, 5))
        light = tuple(min(255, c + 70) for c in rgb) + (255,)
        if v == 2:  # sottile: alto un terzo di cella, bordo chiaro, niente fianco
            d.rectangle([x0, 0, x0 + TILE - 1, 6], fill=rgb + (255,))
            d.line([x0, 0, x0 + TILE - 1, 0], fill=light)
            d.line([x0, 6, x0 + TILE - 1, 6], fill=dark)
            continue
        d.rectangle([x0, 0, x0 + TILE - 1, TILE - 1], fill=rgb + (255,))
        if v in (1, 3, 6, 7):  # pieni: filo di luce in cima e contorno scuro
            d.rectangle([x0, 0, x0 + TILE - 1, TILE - 1], outline=dark)
            d.line([x0 + 1, 1, x0 + TILE - 2, 1], fill=light)
        if v == 3:  # bagnato: riga azzurra
            d.line([x0 + 1, 3, x0 + TILE - 2, 3], fill=(120, 210, 255, 255))
        elif v == 6:  # muro finto: diagonale gialla
            d.line([x0 + 1, TILE - 2, x0 + TILE - 2, 1], fill=(240, 210, 60, 255))
        elif v == 7:  # rompibile: crepa a X
            d.line([x0 + 4, 4, x0 + TILE - 5, TILE - 5], fill=(225, 220, 210, 255))
            d.line([x0 + TILE - 5, 4, x0 + 4, TILE - 5], fill=(225, 220, 210, 255))
        elif v == 4:  # elastico: i panni, a onde
            for y in (5, 11, 17):
                d.line([x0, y, x0 + TILE - 1, y], fill=(190, 175, 140, 255))
        elif v == 5:  # crollo: crepe
            d.line([x0 + 3, 2, x0 + 8, 9, x0 + 6, 16], fill=(70, 30, 20, 255))
            d.line([x0 + 14, 4, x0 + 11, 12, x0 + 16, 18], fill=(70, 30, 20, 255))
        elif v == 8:  # vuoto: nero con le strisce rosse del nastro di cantiere
            for k in range(-TILE, TILE, 8):
                d.line([x0 + k, TILE - 1, x0 + k + TILE - 1, 0], fill=(150, 25, 30, 255), width=2)
        elif v == 9:  # elettrico: la scintilla
            d.line([x0 + 11, 2, x0 + 7, 10, x0 + 12, 10, x0 + 8, 18], fill=(60, 50, 10, 255), width=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, optimize=True)


# --- Progetto ------------------------------------------------------------------------------------

def field_instances(edef: dict, values: dict, refs: dict) -> list:
    out = []
    for fd in edef["fieldDefs"]:
        name = fd["identifier"]
        default = fd["defaultOverride"]["params"][0] if fd["defaultOverride"] else None
        if fd["isArray"]:
            val, rev = [], []
        elif name in values:
            v = values[name]
            if fd["type"] == "F_EntityRef":
                val = refs[v]
                rev = [{"id": "V_String", "params": [val["entityIid"]]}]
            else:
                vid = {"F_Int": "V_Int", "F_Float": "V_Float", "F_Bool": "V_Bool"}.get(fd["type"], "V_String")
                val, rev = v, [{"id": vid, "params": [v]}]
        else:
            if fd["type"] == "F_String":
                val = default if default is not None else ""
            elif fd["type"].startswith("F_Enum") and default is None:
                val = None
            else:
                val = default
            rev = [None]
        out.append({"__identifier": name, "__type": fd["__type"], "__value": val, "__tile": None,
                    "defUid": fd["uid"], "realEditorValues": rev})
    return out


def make_level(name: str, rows: list[str], signs: dict, cps: list, defs: dict, aux: dict,
               world_iid: str, uids: Uid) -> dict:
    h, w = len(rows), len(rows[0])
    lv_iid = iid(name)
    layer_by = {l["identifier"]: l for l in defs["layers"]}
    edefs = {e["identifier"]: e for e in defs["entities"]}
    voids = void_cells(rows)
    csv = []
    for y in range(h):
        for x in range(w):
            c = rows[y][x]
            csv.append(1 if c == "#" else 2 if c == "=" else VUOTO if (x, y) in voids else 0)

    # Le entità, nell'ordine dei segni della mappa (riga per riga, da sinistra).
    ents, zones = [], []
    door = []
    marks = {}
    for y in range(h):
        for x in range(w):
            c = rows[y][x]
            if c in "#=. ":
                continue
            if c == "/":
                door.append((x, y))
                continue
            marks.setdefault(c, []).append((x, y))
    li_ent, li_zone = iid(name, "Entita"), iid(name, "Zone")
    refs = {}

    def add(kind, px, size, values, key, layer="Entita"):
        e = edefs[kind]
        e_iid = iid(name, "entita", key)
        refs[key] = {"entityIid": e_iid, "layerIid": li_ent if layer == "Entita" else li_zone,
                     "levelIid": lv_iid, "worldIid": world_iid}
        inst = {"__identifier": kind, "__grid": [px[0] // TILE, (px[1] - (1 if e["pivotY"] == 1 else 0)) // TILE],
                "__pivot": [e["pivotX"], e["pivotY"]], "__tags": e["tags"], "__tile": None,
                "__smartColor": e["color"], "iid": e_iid, "width": size[0], "height": size[1],
                "defUid": e["uid"], "px": list(px), "fieldInstances": [], "_values": values}
        (ents if layer == "Entita" else zones).append(inst)
        return inst

    point = lambda x, y: (x * TILE + TILE // 2, (y + 1) * TILE)
    for c in sorted(marks):
        for i, (x, y) in enumerate(marks[c]):
            if len(marks[c]) > 1:
                raise SystemExit(f"il segno {c!r} compare {len(marks[c])} volte: la conversione non lo sa fare")
            if c == "G":
                add("Partenza", point(x, y), (25, 100), {"dopo_riavvio": False}, "G")
            elif c == "X":
                add("Partenza", point(x, y), (25, 100), {"dopo_riavvio": True}, "X")
            elif c == "Z":
                add("Uscita", point(x, y), (40, 100), {"prossima": "capitolo-1"}, "Z")
            elif c in SEGNI_SCENA.values():
                sid = next(k for k, v in SEGNI_SCENA.items() if v == c)
                add("Scena", point(x, y), (20, 40), {"id": sid, "modo": "su", "una_volta": True}, c)
            elif c.islower():
                t, r = signs.get(c, ("", ""))
                add("Cartello", point(x, y), (20, 40),
                    {"id": c, "titolo": t, "riga": r, "ripartenza": c in cps}, c)
            else:
                raise SystemExit(f"segno {c!r} senza entità")
    if door:
        xs, ys = [p[0] for p in door], [p[1] for p in door]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        if len(door) != (x1 - x0 + 1) * (y1 - y0 + 1):
            raise SystemExit("le celle della porta non sono un rettangolo")
        add("Porta", (x0 * TILE, y0 * TILE), ((x1 - x0 + 1) * TILE, (y1 - y0 + 1) * TILE),
            {"si_chiude_dopo": True}, "porta")
    # L'arena del pignoramento: lo stesso riquadro che il motore ricava dal cartello f (test_room.gd,
    # ARENA_CAM_FROM_SIGN e View.W), con il pavimento della mappa.
    if "f" in marks:
        fx, fy = point(*marks["f"][0])
        cam_x = max(0, min(fx - 170, w * TILE - 480))
        add("Arena", (cam_x, fy - 12 * TILE), (480, 12 * TILE),
            {"id": "pignoramento", "fine": "tutti_ko", "ripartenza": "f"}, "arena-f", layer="Zone")
    for inst in ents + zones:
        inst["fieldInstances"] = field_instances(edefs[inst["__identifier"]], inst.pop("_values"), refs)

    tiles = []
    rule_of = {r["pattern"][0]: r for r in aux["rules"]}
    for y in range(h):
        for x in range(w):
            v = csv[y * w + x]
            if v:
                r = rule_of[v]
                t = r["tileRectsIds"][0][0]
                tiles.append({"px": [x * TILE, y * TILE], "src": [t * TILE, 0], "f": 0, "t": t,
                              "d": [r["uid"], y * w + x], "a": 1})

    def inst(ident, extra):
        d = layer_by[ident]
        base = {"__identifier": ident, "__type": d["type"], "__cWid": w, "__cHei": h, "__gridSize": TILE,
                "__opacity": 1, "__pxTotalOffsetX": 0, "__pxTotalOffsetY": 0, "__tilesetDefUid": d["tilesetDefUid"],
                "__tilesetRelPath": aux["tileset"]["relPath"] if d["tilesetDefUid"] else None,
                "iid": iid(name, ident), "levelId": 0, "layerDefUid": d["uid"], "pxOffsetX": 0, "pxOffsetY": 0,
                "visible": True, "optionalRules": [], "intGridCsv": [], "autoLayerTiles": [],
                "seed": int(uuid.uuid5(NS, name + ident).int % 9_000_000), "overrideTilesetUid": None,
                "gridTiles": [], "entityInstances": []}
        base.update(extra)
        return base

    level = {
        "identifier": name, "iid": lv_iid, "uid": 0, "worldX": 0, "worldY": 0, "worldDepth": 0,
        "pxWid": w * TILE, "pxHei": h * TILE, "__bgColor": "#1E1A24", "bgColor": None, "useAutoIdentifier": False,
        "bgRelPath": None, "bgPos": None, "bgPivotX": 0.5, "bgPivotY": 0.5, "__smartColor": "#8E8C93",
        "__bgPos": None, "externalRelPath": None, "fieldInstances": [], "__neighbours": [],
        "layerInstances": [
            inst("Zone", {"entityInstances": zones}),
            inst("Entita", {"entityInstances": ents}),
            inst("Greybox", {"autoLayerTiles": tiles}),
            inst("Collisioni", {"intGridCsv": csv}),
        ],
    }
    return level


def write_project(path: Path, level_name: str, rows: list[str], signs: dict, cps: list) -> None:
    uids = Uid()
    defs, aux = build_defs(uids)
    aux["tileset"]["relPath"] = Path(os.path.relpath(GREYBOX_PNG, path.resolve().parent)).as_posix()
    world_iid = iid("mondo")
    level = make_level(level_name, rows, signs, cps, defs, aux, world_iid, uids)
    project = {
        "__header__": {"fileType": "LDtk Project JSON", "app": "LDtk", "doc": "https://ldtk.io/json",
                       "schema": "https://ldtk.io/files/JSON_SCHEMA.json",
                       "appAuthor": "Sebastien 'deepnight' Benard", "appVersion": "1.5.3", "url": "https://ldtk.io"},
        "iid": iid("progetto", path.stem), "jsonVersion": "1.5.3", "appBuildId": 473702,
        "nextUid": uids.n + 1, "identifierStyle": "Free", "toc": [], "worldLayout": "LinearHorizontal",
        "worldGridWidth": 256, "worldGridHeight": 256, "defaultLevelWidth": 480, "defaultLevelHeight": 500,
        "defaultPivotX": 0.5, "defaultPivotY": 1, "defaultGridSize": TILE, "defaultEntityWidth": TILE,
        "defaultEntityHeight": TILE, "bgColor": "#2B2633", "defaultLevelBgColor": "#1E1A24",
        "minifyJson": False, "externalLevels": False, "exportTiled": False, "simplifiedExport": False,
        "imageExportMode": "None", "exportLevelBg": False, "pngFilePattern": None, "backupOnSave": False,
        "backupLimit": 10, "backupRelPath": None, "levelNamePattern": "Livello_%idx",
        "tutorialDesc": "CTRL+ALT REVENGE: legenda in docs/ldtk.md. Collisioni a 20 px, entità con il perno "
                        "in basso al centro, zone in Zone.",
        "customCommands": [], "flags": ["ExportOldTableOfContentData", "UseMultilinesType"],
        "defs": defs, "levels": [level], "worlds": [], "dummyWorldIid": world_iid,
    }
    # Le tessere del greybox una per riga, compatte: sono generate e nessuno le legge a mano.
    tiles = {}
    for li in level["layerInstances"]:
        if li["autoLayerTiles"]:
            key = f"@@tiles:{li['iid']}@@"
            tiles[key] = li["autoLayerTiles"]
            li["autoLayerTiles"] = key
    text = json.dumps(project, ensure_ascii=False, indent="\t")
    for key, lst in tiles.items():
        body = ",\n".join("\t\t\t\t\t\t" + json.dumps(t, separators=(",", ":")) for t in lst)
        text = text.replace(json.dumps(key), "[\n" + body + "\n\t\t\t\t\t]")
    # Le liste di soli numeri su una riga: il file resta leggibile e piccolo.
    text = re.sub(r"\[\s*(-?[\d.]+(?:,\s*-?[\d.]+)*)\s*\]", lambda m: "[" + re.sub(r"\s+", "", m.group(1)) + "]", text)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


# --- Dal livello LDtk al testo -------------------------------------------------------------------

def level_to_rows(project: dict, level_name: str | None) -> list[str]:
    levels = project["levels"]
    lv = next((l for l in levels if l["identifier"] == level_name), None) if level_name else levels[0]
    if lv is None:
        raise SystemExit(f"livello {level_name!r} non trovato")
    layers = {li["__identifier"]: li for li in lv["layerInstances"]}
    coll = layers["Collisioni"]
    w, h = coll["__cWid"], coll["__cHei"]
    sym = {1: "#", 2: "=", 3: "#", 4: "=", 5: "#", 6: ".", 7: "#", 8: ".", 9: "#"}
    grid = [[sym.get(v, ".") for v in coll["intGridCsv"][y * w:(y + 1) * w]] for y in range(h)]

    def put(px, c):
        x, y = px[0] // TILE, (px[1] - 1) // TILE
        if grid[y][x] != ".":
            raise SystemExit(f"il segno {c!r} cade su una cella non vuota ({x},{y})")
        grid[y][x] = c
    for e in layers["Entita"]["entityInstances"]:
        f = {fi["__identifier"]: fi["__value"] for fi in e["fieldInstances"]}
        k = e["__identifier"]
        if k == "Partenza":
            put(e["px"], "X" if f.get("dopo_riavvio") else "G")
        elif k == "Uscita":
            put(e["px"], "Z")
        elif k == "Scena" and f.get("id") in SEGNI_SCENA:
            put(e["px"], SEGNI_SCENA[f["id"]])
        elif k == "Cartello" and f.get("id"):
            put(e["px"], f["id"])
        elif k == "Porta":
            x0, y0 = e["px"][0] // TILE, e["px"][1] // TILE
            for y in range(y0, y0 + e["height"] // TILE):
                for x in range(x0, x0 + e["width"] // TILE):
                    grid[y][x] = "/"
    return ["".join(r) for r in grid]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("crea", help="crea il progetto LDtk da una mappa di testo")
    c.add_argument("mappa", type=Path)
    c.add_argument("progetto", type=Path)
    c.add_argument("--livello", default="Prologo")
    c.add_argument("--sovrascrivi", action="store_true")
    t = sub.add_parser("txt", help="riscrive la mappa di testo da un livello LDtk")
    t.add_argument("progetto", type=Path)
    t.add_argument("mappa", type=Path)
    t.add_argument("--livello", default=None)
    a = ap.parse_args()
    if a.cmd == "crea":
        if a.progetto.exists() and not a.sovrascrivi:
            print(f"{a.progetto} c'è già: per rifarlo da capo usa --sovrascrivi (si perdono le modifiche fatte in LDtk)")
            return 1
        _head, rows = read_txt(a.mappa)
        if a.progetto.exists():
            signs, cps = project_signs(json.loads(a.progetto.read_text(encoding="utf-8")), a.livello)
        else:
            signs, cps = prologue_signs() if a.livello == "Prologo" else ({}, [])
        if not GREYBOX_PNG.exists():
            make_greybox(GREYBOX_PNG)
        write_project(a.progetto, a.livello, rows, signs, cps)
        print(f"scritto {a.progetto}: {len(rows[0])} x {len(rows)} celle")
    else:
        project = json.loads(a.progetto.read_text(encoding="utf-8"))
        rows = level_to_rows(project, a.livello)
        head = read_txt(a.mappa)[0] if a.mappa.exists() else []
        a.mappa.write_text("\n".join(head + rows) + "\n", encoding="utf-8", newline="\n")
        print(f"scritto {a.mappa}: {len(rows[0])} x {len(rows)} celle")
    return 0


if __name__ == "__main__":
    sys.exit(main())
