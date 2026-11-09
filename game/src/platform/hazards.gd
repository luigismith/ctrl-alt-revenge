class_name Hazards
extends RefCounted
## Le zone tossiche e i power-up di un tratto platform (catalogo di car-mappe, 8 novembre 2026).
##
## Le zone vengono dai segni della mappa di testo (ogni gruppo di celle vicine con lo stesso segno è
## un rettangolo) o dalle zone LDtk `Tossica`; i power-up dai segni o dalle entità `PowerUp`. I tipi
## stanno in data/tossiche/ e data/powerup/; i campi LDtk maggiori di zero (`danno_s`, `ritardo_s`,
## `ciclo_s`, `attiva_s`) cambiano quelli del tipo. Con `attiva_s` pari a `ciclo_s` la zona è sempre
## accesa.
##
## Le regole:
## - il ritardo conta la permanenza continua dentro una zona accesa, e si azzera uscendo o quando la
##   zona si spegne: chi passa svelto non paga;
## - il danno è in punti interi di energia (2/s = un punto ogni 30 tick), senza spinta;
## - 0,5 s prima di accendersi la zona dà il preavviso;
## - un power-up alla volta: il nuovo sostituisce il vecchio. Quelli che agiscono subito (l'abbonamento)
##   non toccano quello che si ha.
##
## Tutto a tick fissi, nell'impronta dei test solo nei tratti che hanno zone o power-up.

const POWERUP_PATH := "res://data/powerup/%s.tres"
const HAZARD_PATH := "res://data/tossiche/%s.tres"
## Il preavviso prima che una zona a cicli si accenda: 0,5 s.
const WARN_TICKS := 30
## La tosse: all'inizio del danno, poi ogni tanto finché si resta dentro.
const COUGH_EVERY := 90
## Quanto resta sullo schermo il nome del power-up preso.
const TOAST_TICKS := 90
const TILE := SolidGrid.TILE


class Zone:
	var rect: Rect2i
	var def: HazardDef
	## Decimi di energia al secondo, per contare a interi.
	var damage10: int
	var delay_t: int
	var cycle_t: int
	var active_t: int

	func is_active(t: int) -> bool:
		return cycle_t <= 0 or active_t >= cycle_t or t % cycle_t < active_t

	## Il preavviso: mancano meno di WARN_TICKS all'accensione.
	func warning(t: int) -> bool:
		return not is_active(t) and t % cycle_t >= cycle_t - WARN_TICKS


class Pickup:
	var rect: Rect2i
	var def: PowerUpDef
	## Torna a ogni ripartenza (il campo LDtk `ricompare`).
	var respawns: bool = false
	var taken: bool = false


var zones: Array[Zone] = []
var pickups: Array[Pickup] = []
## Il power-up che GIG ha addosso, e il suo contatore (tick, usi o colpi) su quello iniziale.
var held: PowerUpDef
var left: int = 0
var total: int = 0
## I tick di fila dentro una zona accesa, e i decimi di energia accumulati verso il prossimo punto.
var inside_t: int = 0
var _acc: int = 0
## La zona accesa in cui sta GIG (null fuori), per la vignetta rossa.
var zone_now: Zone
var hurt_t: int = 0
var toast: String = ""
var toast_t: int = 0
var events: PackedStringArray = []

static var _cache: Dictionary = {}


static func powerup(id: String) -> PowerUpDef:
	return _load(POWERUP_PATH % id) as PowerUpDef


static func hazard(id: String) -> HazardDef:
	return _load(HAZARD_PATH % id) as HazardDef


static func _load(path: String) -> Resource:
	if not _cache.has(path):
		_cache[path] = load(path) if ResourceLoader.exists(path) else null
		if _cache[path] == null:
			push_error("Tipo mancante: %s" % path)
	return _cache[path]


func is_empty() -> bool:
	return zones.is_empty() and pickups.is_empty()


## Legge zone e power-up della griglia. `zone_marks`: segno → campi della zona ({"tipo": "polvere",
## ...}); `pickup_marks`: segno → tipo di power-up. Quelli dei segni ricompaiono a ogni ripartenza.
func build(grid: SolidGrid, zone_marks: Dictionary = {}, pickup_marks: Dictionary = {}) -> void:
	zones.clear()
	pickups.clear()
	reset(true)
	for c: String in zone_marks:
		if grid.marks.has(c):
			for r: Rect2i in _components(grid.marks[c]):
				_add_zone(r, zone_marks[c])
	for c: String in pickup_marks:
		if grid.marks.has(c):
			for m: Vector2i in grid.marks[c]:
				_add_pickup(Rect2i(m.x - TILE / 2, m.y - TILE, TILE, TILE), str(pickup_marks[c]), true)
	for e: Dictionary in grid.entities:
		match str(e["tipo"]):
			"Tossica":
				_add_zone(Rect2i(e["pos"], e["size"]), e["campi"])
			"PowerUp":
				var campi: Dictionary = e["campi"]
				_add_pickup(Rect2i(e["pos"], e["size"]), str(campi.get("tipo", "")), bool(campi.get("ricompare", false)))


func _add_zone(r: Rect2i, campi: Dictionary) -> void:
	var def := hazard(str(campi.get("tipo", "")))
	if def == null:
		return
	var z := Zone.new()
	z.rect = r
	z.def = def
	z.damage10 = roundi(_field(campi, "danno_s", def.damage_s) * 10.0)
	z.delay_t = roundi(_field(campi, "ritardo_s", def.delay_s) * 60.0)
	z.cycle_t = roundi(_field(campi, "ciclo_s", def.cycle_s) * 60.0)
	z.active_t = roundi(_field(campi, "attiva_s", def.active_s) * 60.0)
	zones.append(z)


## Un campo della zona cambia il tipo solo se c'è ed è maggiore di zero (LDtk lascia 0 per "come il tipo").
static func _field(campi: Dictionary, k: String, fallback: float) -> float:
	var v: Variant = campi.get(k)
	if (v is float or v is int) and float(v) > 0.0:
		return float(v)
	return fallback


func _add_pickup(r: Rect2i, tipo: String, respawns: bool) -> void:
	var def := powerup(tipo)
	if def == null:
		return
	var k := Pickup.new()
	k.rect = r
	k.def = def
	k.respawns = respawns
	pickups.append(k)


## I gruppi di celle vicine (in orizzontale e in verticale) con lo stesso segno, come rettangoli che
## le contengono. I segni sono al centro in basso della loro cella.
static func _components(marks: Array) -> Array[Rect2i]:
	var cells := {}
	for m: Vector2i in marks:
		cells[Vector2i((m.x - TILE / 2) / TILE, m.y / TILE - 1)] = true
	var out: Array[Rect2i] = []
	var seen := {}
	var keys := cells.keys()
	keys.sort()
	for start: Vector2i in keys:
		if seen.has(start):
			continue
		var lo := start
		var hi := start
		var todo: Array[Vector2i] = [start]
		seen[start] = true
		while not todo.is_empty():
			var c: Vector2i = todo.pop_back()
			lo = Vector2i(mini(lo.x, c.x), mini(lo.y, c.y))
			hi = Vector2i(maxi(hi.x, c.x), maxi(hi.y, c.y))
			for d: Vector2i in [Vector2i.LEFT, Vector2i.RIGHT, Vector2i.UP, Vector2i.DOWN]:
				var n := c + d
				if cells.has(n) and not seen.has(n):
					seen[n] = true
					todo.append(n)
		out.append(Rect2i(lo * TILE, (hi - lo + Vector2i.ONE) * TILE))
	return out


## Alla ripartenza: il power-up si perde, il ritardo e il danno a metà si azzerano, ricompaiono i
## power-up che ricompaiono. `all`: anche quelli già presi una volta per sempre (il livello da capo).
func reset(all: bool = false) -> void:
	held = null
	left = 0
	total = 0
	inside_t = 0
	_acc = 0
	zone_now = null
	hurt_t = 0
	toast_t = 0
	for k in pickups:
		if all or k.respawns:
			k.taken = false


## Un tick, dopo il passo di GIG: power-up presi e consumati, zone. Restituisce l'energia persa,
## che non porta l'energia sotto `energy` meno quanto la zona permette (i fanghi si fermano a 1).
func step(t: int, p: PlatformPlayer, energy: int) -> int:
	events = PackedStringArray()
	toast_t = maxi(toast_t - 1, 0)
	hurt_t = maxi(hurt_t - 1, 0)
	var body := Rect2i(p.left(), p.top(), p.right() - p.left(), p.height)
	for k in pickups:
		if not k.taken and body.intersects(k.rect):
			k.taken = true
			_take(k.def)
	if held != null and held.durata == PowerUpDef.Durata.TEMPO and (not held.only_while_used or p.gliding):
		left -= 1
		if left <= 0:
			_drop()
	p.glide_fall = held.glide_fall if held != null else 0.0
	var z := zone_at(body, t)
	zone_now = z
	p.speed_pct = z.def.speed_pct if z != null else 100
	if z == null or immune():
		inside_t = 0
		_acc = 0
		return 0
	inside_t += 1
	if inside_t <= z.delay_t:
		return 0
	if (inside_t - z.delay_t) % COUGH_EVERY == 1:
		events.append("tosse")
	_acc += z.damage10
	var dmg := 0
	while _acc >= 600:
		_acc -= 600
		dmg += 1
	dmg = mini(dmg, maxi(energy - z.def.min_energy, 0))
	if dmg > 0:
		hurt_t = 20
	return dmg


## La prima zona accesa che tocca il rettangolo.
func zone_at(body: Rect2i, t: int) -> Zone:
	for z in zones:
		if z.is_active(t) and body.intersects(z.rect):
			return z
	return null


func _take(def: PowerUpDef) -> void:
	events.append("powerup")
	toast = def.pickup_text if def.pickup_text != "" else def.label
	toast_t = TOAST_TICKS
	if def.durata == PowerUpDef.Durata.SUBITO:
		if def.extra_life > 0:
			Game.add_life(def.extra_life, def.max_lives)
		return
	held = def
	left = def.start_amount()
	total = left


func _drop() -> void:
	held = null
	left = 0
	total = 0
	events.append("powerup_fine")


# ---------------------------------------------------------------- effetti, per chi li usa

func immune() -> bool:
	return held != null and held.immune_toxic


func damage_mult() -> int:
	return held.damage_mult if held != null else 1


func breaks_guard() -> bool:
	return held != null and held.breaks_guard


func invisible() -> bool:
	return held != null and held.invisible


## Un colpo preso: il giubbotto lo assorbe (true) e perde una banda.
func absorb_hit() -> bool:
	if held == null or not held.absorbs_hits:
		return false
	left -= 1
	if left <= 0:
		_drop()
	return true


## Un uso (la bomboletta): true se c'era.
func use() -> bool:
	if held == null or held.durata != PowerUpDef.Durata.USI:
		return false
	left -= 1
	if left <= 0:
		_drop()
	return true


## GIG attacca: il badge smette di nasconderlo.
func on_attack() -> void:
	if invisible():
		_drop()


func state_hash() -> Array:
	var taken: Array = []
	for k in pickups:
		taken.append(k.taken)
	return [held.id if held != null else &"", left, inside_t, _acc, taken]


# ---------------------------------------------------------------- disegno (solo grafica)

## Le zone, in grigio ma leggibili: accese, una nube che rotola coi granelli che brillano; nel
## preavviso il bordo che lampeggia e i primi granelli; spente, una macchia a terra.
func draw_zones(v: CanvasItem, t: int, vis: Rect2) -> void:
	for z in zones:
		var r := Rect2(z.rect)
		if not r.intersects(vis):
			continue
		var c := z.def.color
		if z.is_active(t):
			v.draw_rect(r, Color(c, 0.30))
			# Le fasce che rotolano piano verso destra, più fitte in basso.
			var band := 8
			for y in range(int(r.position.y), int(r.end.y), band):
				var dy := (y - int(r.position.y)) / band
				var off := (t / 3 + dy * 7) % 24
				for x in range(int(r.position.x) - 24 + off, int(r.end.x), 24):
					var x0 := maxf(x, r.position.x)
					var x1 := minf(x + 12, r.end.x)
					if x1 > x0:
						v.draw_rect(Rect2(x0, y, x1 - x0, 2), Color(c.lightened(0.25), 0.35))
			_draw_grains(v, z, t, 1.0)
		elif z.warning(t):
			v.draw_rect(r, Color(c, 0.10))
			if (t / 4) % 2 == 0:
				v.draw_rect(Rect2(r.position, Vector2(r.size.x, 1)), Color(c, 0.8))
			_draw_grains(v, z, t, 0.35)
		else:
			v.draw_rect(Rect2(r.position.x, r.end.y - 3, r.size.x, 3), Color(c, 0.18))
			for x in range(int(r.position.x), int(r.end.x), 6):
				v.draw_rect(Rect2(x, r.position.y, 2, 1), Color(c, 0.25))


func _draw_grains(v: CanvasItem, z: Zone, t: int, amount: float) -> void:
	var r := z.rect
	var n := int(float(r.size.x * r.size.y) / 220.0 * amount)
	for i in n:
		var h := hash([i, z.rect.position, (t + i * 13) / 20])
		var gx := r.position.x + posmod(h, r.size.x)
		var gy := r.position.y + posmod(h >> 8, r.size.y)
		var bright := posmod(h >> 16, 4) == 0
		v.draw_rect(Rect2(gx, gy, 1, 1), Color(z.def.color.lightened(0.6 if bright else 0.2), 0.9 if bright else 0.6))


## I power-up ancora da prendere: l'icona che galleggia sopra una base, con la luce che pulsa.
func draw_pickups(n: CanvasItem, t: int, vis: Rect2, glow: Glow) -> void:
	for k in pickups:
		if k.taken or not Rect2(k.rect).intersects(vis):
			continue
		var bob: int = [0, -1, -2, -1][(t / 10) % 4]
		var at := Vector2(k.rect.position.x + k.rect.size.x / 2 - 6, k.rect.end.y - 22 + bob)
		n.draw_rect(Rect2(k.rect.position.x + k.rect.size.x / 2 - 5, k.rect.end.y - 2, 10, 2), Color(0, 0, 0, 0.35))
		draw_icon(n, at, k.def.id, k.def.color)
		var pulse := 0.35 + 0.25 * float((t / 8) % 4) / 3.0
		if glow != null:
			glow.halo(at + Vector2(6, 6), 9, Color(k.def.color, pulse))


## L'icona del power-up in 12×12, disegnata col codice (la grafica vera arriverà da car-grafica).
static func draw_icon(ci: CanvasItem, at: Vector2, id: StringName, c: Color) -> void:
	var ink := Color8(18, 16, 24)
	var dark := c.darkened(0.45)
	match id:
		&"mascherina":
			ci.draw_rect(Rect2(at + Vector2(2, 3), Vector2(8, 6)), c)
			ci.draw_rect(Rect2(at + Vector2(3, 5), Vector2(6, 1)), dark)
			ci.draw_rect(Rect2(at + Vector2(3, 7), Vector2(6, 1)), dark)
			ci.draw_rect(Rect2(at + Vector2(0, 4), Vector2(2, 1)), c)
			ci.draw_rect(Rect2(at + Vector2(10, 4), Vector2(2, 1)), c)
		&"abbonamento":
			ci.draw_rect(Rect2(at + Vector2(0, 3), Vector2(12, 7)), c)
			ci.draw_rect(Rect2(at + Vector2(0, 5), Vector2(12, 1)), dark)
			ci.draw_rect(Rect2(at + Vector2(8, 7), Vector2(3, 2)), Color8(240, 244, 248))
		&"bomboletta":
			ci.draw_rect(Rect2(at + Vector2(4, 3), Vector2(5, 9)), c)
			ci.draw_rect(Rect2(at + Vector2(5, 1), Vector2(3, 2)), Color8(240, 244, 248))
			ci.draw_rect(Rect2(at + Vector2(4, 6), Vector2(5, 1)), dark)
			ci.draw_rect(Rect2(at + Vector2(1, 1), Vector2(2, 1)), c)
		&"sovraccarico":
			for p: Vector2 in [Vector2(6, 0), Vector2(5, 2), Vector2(4, 4), Vector2(3, 6), Vector2(5, 6), Vector2(7, 6), Vector2(6, 8), Vector2(5, 10)]:
				ci.draw_rect(Rect2(at + p, Vector2(2, 2)), c)
		&"giubbotto":
			ci.draw_rect(Rect2(at + Vector2(1, 2), Vector2(10, 10)), c)
			ci.draw_rect(Rect2(at + Vector2(5, 2), Vector2(2, 4)), ink)
			ci.draw_rect(Rect2(at + Vector2(1, 7), Vector2(10, 1)), Color8(240, 244, 248))
			ci.draw_rect(Rect2(at + Vector2(1, 9), Vector2(10, 1)), Color8(240, 244, 248))
		&"badge":
			ci.draw_rect(Rect2(at + Vector2(5, 0), Vector2(1, 4)), Color8(220, 52, 52))
			ci.draw_rect(Rect2(at + Vector2(3, 4), Vector2(6, 8)), c)
			ci.draw_rect(Rect2(at + Vector2(4, 6), Vector2(4, 3)), dark)
		&"ombrello":
			ci.draw_rect(Rect2(at + Vector2(1, 3), Vector2(10, 2)), c)
			ci.draw_rect(Rect2(at + Vector2(3, 1), Vector2(6, 2)), c)
			ci.draw_rect(Rect2(at + Vector2(6, 5), Vector2(1, 6)), dark)
			ci.draw_rect(Rect2(at + Vector2(4, 10), Vector2(2, 1)), dark)
		_:
			ci.draw_rect(Rect2(at + Vector2(2, 2), Vector2(8, 8)), c)


## Sull'interfaccia: la vignetta della zona ai bordi, il power-up con la sua barra a destra di `x`,
## e il nome di quello appena preso.
func draw_hud(h: CanvasItem, x: float, t: int) -> void:
	if zone_now != null and not immune() and inside_t > 0:
		var a := ceilf(clampf(float(inside_t) / 40.0, 0.0, 1.0) * 4.0) / 4.0
		if hurt_t > 0:
			a = minf(a + 0.25, 1.0)
		var c := zone_now.def.color
		var w := View.W
		var hh := View.H
		for i in 3:
			var s := float(6 * (i + 1))
			var col := Color(c, a * [0.30, 0.18, 0.08][i])
			h.draw_rect(Rect2(0, 0, w, s), col)
			h.draw_rect(Rect2(0, hh - s, w, s), col)
			h.draw_rect(Rect2(0, s, s, hh - 2 * s), col)
			h.draw_rect(Rect2(w - s, s, s, hh - 2 * s), col)
	if held != null:
		draw_icon(h, Vector2(x, 1), held.id, held.color)
		var bw := 30
		h.draw_rect(Rect2(x + 15, 5, bw, 4), Color(0, 0, 0, 0.6))
		var fill := roundi(float(bw) * float(left) / float(maxi(total, 1)))
		var last := held.durata == PowerUpDef.Durata.TEMPO and left < 180 and (t / 8) % 2 == 0
		if not last:
			h.draw_rect(Rect2(x + 15, 5, fill, 4), held.color)
	if toast_t > 0:
		UiFont.draw_text(h, Vector2(View.CX, 30), toast, Color8(255, 200, 64) if toast == "RINNOVATO" else Color8(64, 232, 255), 1, 1)
