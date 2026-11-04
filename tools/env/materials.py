# SPDX-FileCopyrightText: 2026 Luigi Massari
# SPDX-License-Identifier: MIT
"""CTRL+ALT REVENGE - pipeline degli sfondi: materiali e palette di "Sotto la Linea".

Ogni materiale ha un id (scritto nel G-buffer), una rampa di colori dal più scuro al più chiaro
(presa dalla palette principale) e i parametri della luce a bande. La palette segue la locandina:
notte blu-viola, asfalto viola, neon rossi e arancioni, un solo punto cyan (la torre lontana).
"""

# ------------------------------------------------------------------ rampe (scuro -> chiaro)
RAMPS = {
    "night": ["#06061a", "#0a0b24", "#0f1131", "#15183f", "#1c1f4e", "#262760", "#322f6c", "#43356f"],
    "wall_blue": ["#0f1022", "#171a32", "#212743", "#2d3557", "#3b466c", "#4e5b84", "#6a76a0"],
    "wall_mauve": ["#150f22", "#1f162f", "#2b1f3e", "#3a2a4f", "#4b3762", "#5e4675", "#77598b"],
    "wall_grey": ["#121119", "#1b1a25", "#262433", "#333043", "#423e55", "#555069", "#6d6883"],
    "brick": ["#170c16", "#241220", "#33192a", "#451f33", "#5a283c", "#713446", "#8c4350"],
    "stone": ["#1a1520", "#261f2c", "#342b3a", "#443a4a", "#574b5c", "#6d5f71", "#887a8c"],
    "metal": ["#0e1019", "#161a26", "#212736", "#2e3649", "#3e4a60", "#55647c", "#7686a0", "#a3b2c8"],
    "rust": ["#1b0f12", "#2c1716", "#43221c", "#5c3023", "#77402b", "#93553a"],
    "glass": ["#070914", "#0c1122", "#141c34", "#1f2b4a", "#2f4166", "#4a5f88"],
    "wood": ["#170e12", "#22141a", "#301c22", "#40262a", "#533233", "#6a4140"],
    "asphalt": ["#0b0812", "#110c1b", "#171124", "#1e162e", "#261c39", "#302345", "#3c2b53"],
    "sidewalk": ["#120e19", "#1a1424", "#231b30", "#2d233c", "#382c4a", "#45375a", "#56466c"],
    "kerb": ["#1c1a24", "#292633", "#383444", "#4a4557", "#5f5a6e", "#7a7489"],
    "dirt": ["#110c12", "#1a1219", "#241921", "#30212a", "#3d2a33", "#4c353d"],
    "plant": ["#0b130f", "#121d17", "#1a2a20", "#24392b", "#304b37"],
    "awning_red": ["#22081a", "#360d20", "#4e1226", "#6a182e", "#8a2238", "#a83046"],
    "awning_blue": ["#0a1122", "#101a30", "#182640", "#223352", "#2e4466"],
    "paper": ["#29252f", "#433d4c", "#625a6c", "#857d90", "#aaa1b4", "#cdc4d4"],
    "trash": ["#09080e", "#110f18", "#1a1724", "#252132", "#322c42"],
    "rubber": ["#09080c", "#121016", "#1b1820", "#26222c"],
    "neon_red": ["#3d0a1a", "#6e1024", "#a8182e", "#e02a3a", "#ff5a5a", "#ffa29a", "#ffe0d8"],
    # croce delle farmacie italiane: verde, mai rossa (la croce rossa è un emblema protetto; coerenza-slice M12)
    "neon_green": ["#06240f", "#0b3f1b", "#13662c", "#1d9442", "#35c262", "#8ce8a8", "#dcffe6"],
    "neon_orange": ["#4a1a0c", "#85300f", "#c04a14", "#f06a1e", "#ff9440", "#ffc27a", "#ffe6c0"],
    "warm": ["#2e1a18", "#55301f", "#86482a", "#b8663a", "#e08c4c", "#ffb86a", "#ffdca0"],
    "cyan": ["#0b3a4a", "#138aa6", "#2fd0f0", "#9af4ff"],
    "red_lit": ["#1e0c1c", "#2c1024", "#3e142c", "#561a36", "#722240", "#8f2c4a"],
    "orange_lit": ["#22121a", "#33181c", "#4a221f", "#643023", "#834028", "#a3542f"],
    "white": ["#c9c0d6", "#f4eef8"],
    "graffiti": ["#c8c0d8", "#d8b040", "#7a3a9a", "#b8303f", "#e06a2a", "#3b5fa0"],
    "outline": ["#0d0a16", "#140e1e"],
}


def master_palette():
    seen, out = set(), []
    for r in RAMPS.values():
        for c in r:
            if c not in seen:
                seen.add(c)
                out.append(c)
    return out


# ------------------------------------------------------------------ materiali
# id: (nome, rampa, soglie delle bande su n·L, riceve la luce dei neon, retinatura, rampe di riflesso)
MATERIALS = {}


def _m(mid, name, ramp, bands=(0.12, 0.5), spill=1.0, dither=True, tint=("red_lit", "orange_lit"),
       pattern=None, base=None):
    MATERIALS[mid] = dict(id=mid, name=name, ramp=ramp, bands=bands, spill=spill, dither=dither, tint=tint,
                          pattern=pattern, base=base)
    return mid


M_PLASTER_BLUE = _m(1, "plaster_blue", "wall_blue", pattern="plaster")
M_PLASTER_MAUVE = _m(2, "plaster_mauve", "wall_mauve", pattern="plaster")
M_PLASTER_GREY = _m(3, "plaster_grey", "wall_grey", pattern="plaster")
M_BRICK = _m(4, "brick", "brick", pattern="brick")
M_STONE = _m(5, "stone", "stone", pattern="stone")
M_CONCRETE = _m(6, "concrete", "wall_grey", pattern="concrete")
M_METAL = _m(7, "metal", "metal", bands=(0.1, 0.45, 0.8))
M_SHUTTER = _m(8, "shutter", "metal", pattern="shutter")
M_GLASS = _m(9, "glass", "glass", bands=(0.3,), spill=0.6, dither=False)
M_WOOD = _m(10, "wood", "wood", pattern="wood")
M_ASPHALT = _m(11, "asphalt", "asphalt", bands=(0.3,), pattern="asphalt")
M_SIDEWALK = _m(12, "sidewalk", "sidewalk", bands=(0.3,), pattern="sidewalk")
M_KERB = _m(13, "kerb", "kerb", bands=(0.2, 0.6), pattern="kerb")
M_DIRT = _m(14, "dirt", "dirt", bands=(0.3,), pattern="dirt")
M_AWNING_RED = _m(15, "awning_red", "awning_red", pattern="awning")
M_AWNING_BLUE = _m(16, "awning_blue", "awning_blue", pattern="awning")
M_SIGNBOX = _m(17, "signbox", "metal", bands=(0.2, 0.6), dither=False)
M_NEON = _m(18, "neon", "neon_red", spill=0.0, dither=False)
M_LAMP = _m(19, "lamp", "warm", spill=0.0, dither=False)
M_WINDOW_LIT = _m(20, "window_lit", "warm", spill=0.0, dither=False)
M_TRASH = _m(21, "trash", "trash", bands=(0.25, 0.7), dither=False)
M_PLANT = _m(22, "plant", "plant", bands=(0.3,), pattern="plant")
M_RUBBER = _m(23, "rubber", "rubber", bands=(0.4,), dither=False)
M_RUST = _m(24, "rust", "rust", pattern="rust")
M_PAPER = _m(25, "paper", "paper", dither=False)
M_CONCRETE_PILLAR = _m(26, "concrete_pillar", "wall_grey", bands=(0.05, 0.4, 0.75), pattern="pillar")
M_STEEL = _m(27, "steel", "metal", bands=(0.1, 0.45, 0.8), pattern="rivets")
M_GLASS_DOOR = _m(28, "glass_door", "glass", bands=(0.3,), spill=0.6, dither=False)
M_DARK = _m(29, "dark", "trash", bands=(0.5,), dither=False, spill=0.3)
M_CABINET = _m(30, "cabinet", "metal", bands=(0.15, 0.55), pattern="cabinet")
M_TILE = _m(31, "tile", "stone", bands=(0.2, 0.6), pattern="tile")
M_HOARDING = _m(32, "hoarding", "wood", pattern="hoarding")
M_POLE = _m(33, "pole", "wall_grey", bands=(0.1, 0.5))
M_CABLE = _m(34, "cable", "trash", bands=(0.6,), dither=False, spill=0.5)
M_BIN = _m(35, "bin", "metal", bands=(0.05, 0.4, 0.75), pattern="bin_ribs")
M_BIN_LID = _m(36, "bin_lid", "metal", bands=(0.05, 0.4, 0.75))
M_APPLE = _m(37, "apple", "neon_red", bands=(0.0, 0.45, 0.8), spill=0.0, dither=False)
M_LEAF = _m(38, "leaf", "plant", bands=(0.3, 0.7), spill=0.0, dither=False)
M_PUDDLE = _m(39, "puddle", "asphalt", bands=(0.3,), spill=0.0, dither=False)
M_SLAB = _m(40, "slab", "sidewalk", bands=(0.3,), pattern="slab")


def material_by_name(name):
    for m in MATERIALS.values():
        if m["name"] == name:
            return m
    raise KeyError(name)
