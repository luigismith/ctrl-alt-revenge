class_name Drones
extends RefCounted
## I droni dei tratti platform (legenda §4b): la Colomba di ARIA+, la Vedetta e il Segugio del
## Recupero Crediti di SIDERA. Sono ostacoli da platform, non avversari: niente barra di vita, un
## colpo solo li rompe (un salto in testa, un jab o il calcio in aria al momento giusto) e avvisano
## sempre prima di colpire, con una luce e un suono.
##
## Vengono dalle entità LDtk `Nemico` senza arena coi tipi di TIPI. Il perno è in basso al centro;
## una cella del `percorso` (cx, cy) diventa il punto (cx*20+10, (cy+1)*20), in basso al centro
## della cella. Quelli rotti restano rotti finché non si cambia livello o non si ricomincia.
##
## Per ora in greybox, disegnati dal codice con le misure e i colori della strada A delle bozze di
## car-grafica: la grafica vera arriva dopo. Tutto a tick fissi e in sottopixel interi (SUB), così i
## replay con hash tornano.

const TILE := SolidGrid.TILE
const SUB := PlatformPlayer.SUB
const TIPI: Array[String] = ["colomba", "vedetta", "segugio"]
## Le misure (larghezza, altezza) in pixel.
const SIZE := {"colomba": Vector2i(36, 20), "vedetta": Vector2i(60, 22), "segugio": Vector2i(60, 40)}

enum Phase { PATROL, PERCH, AIM, DIVE, SPRAY, RISE, SPOT, LOW, TURN, SNIFF, BARK, DASH, PANT, BROKEN, HALT }

# --- Colomba
const COLOMBA_SPEED := 0.75
## GIG sotto di lei entro 4 celle: la lente si accende (0,5 s), scende e spruzza.
const COLOMBA_REACH := 4 * TILE
const COLOMBA_AIM := 30
const COLOMBA_DIVE := 36
const COLOMBA_DIVE_T := 12
const COLOMBA_SPRAY := 24
const COLOMBA_REST := 90
## Lo spruzzo acceca per 1,5 s, senza danno.
const BLIND_TICKS := 90

# --- Vedetta
const VEDETTA_SPEED := 1.0
## Il cono del faro, in avanti e in basso: largo come `CONE_NEAR`..`CONE_FAR` volte la profondità,
## fino a `CONE_DEPTH` (a 9 celle sotto, cioè sulla strada, è largo circa 6 celle).
const CONE_NEAR := 0.05
const CONE_FAR := 0.65
const CONE_DEPTH := 14 * TILE
## GIG nel cono per 1 s: la luce rossa subito, la sirena a metà, il sigillo alla fine.
const SPOT_TICKS := 60
const SIREN_AT := 30
const LOW_DROP := 50
const LOW_MOVE := 25
const LOW_HOLD := 60
const SPOT_COOLDOWN := 60
const SEAL_SPEED := 2.0
const SEAL_LIFE := 240
const SEAL_SIZE := Vector2i(14, 10)
const SEAL_DAMAGE := 6
## Le pressioni di tasti per staccare il sigillo.
const SEAL_PRESSES := 8
## Davanti alla processione (legenda §4c): il faro si ferma prima dei cappucci, la Vedetta resta
## ferma e cieca per HALT_TICKS («SOGGETTO NON IDENTIFICABILE»), poi gira al largo e per SHY_TICKS
## non si ferma e non vede.
const HALT_TICKS := 120
const SHY_TICKS := 150
## Lo spintone alla processione (Processions.pushed): la Vedetta entro ALERT_REACH px si gira su GIG,
## lo tiene nel faro rosso per ALERT_TICKS tick, dove che sia, e spara il sigillo.
const ALERT_REACH := 400
const ALERT_TICKS := 20

# --- Segugio
const SEGUGIO_SPEED := 0.8
const SNIFF_REACH := 3 * TILE
const SNIFF_TICKS := 30
const SEE_REACH := 6 * TILE
const SEE_HEIGHT := 2 * TILE
const TURN_TICKS := 30
## Abbaia 0,6 s, poi scatta per 5 celle in 0,4 s; dopo ansima 1 s.
const BARK_TICKS := 36
const DASH_DIST := 5 * TILE
const DASH_TICKS := 24
const PANT_TICKS := 60
const DASH_DAMAGE := 8
const DASH_KNOCK := 2 * TILE

## Il contatto col corpo di una Vedetta bassa o di un Segugio che non scatta.
const TOUCH_DAMAGE := 3
const TOUCH_KNOCK := 24
const BROKEN_GRAVITY := 0.35

# --- Colori del greybox (strada A): bianco e menta la Colomba, arancio SIDERA gli altri due, e il
# bordo rosso di chi fa male (la regola di leggibilità).
const C_WHITE := Color8(236, 240, 244)
const C_MINT := Color8(120, 226, 188)
const C_ORANGE := Color8(236, 118, 40)
const C_ORANGE_DARK := Color8(150, 66, 24)
const C_RED := Color8(226, 52, 52)
const C_INK := Color8(20, 18, 26)
const C_STEEL := Color8(84, 88, 100)
const C_BEAM := Color8(255, 232, 150)
const C_WRECK := Color8(70, 70, 78)


class Drone:
	var iid: String
	var tipo: String
	var size: Vector2i
	## Il punto di partenza e quello di adesso, in sottopixel (in basso al centro).
	var home: Vector2i
	var x: int
	var y: int
	## La quota della ronda, in sottopixel, e gli estremi del percorso in pixel.
	var y0: int
	var x_min: int
	var x_max: int
	var still: bool = false
	var dir: int = 1
	var phase: int = Phase.PATROL
	var t: int = 0
	## La Vedetta: da quanto vede GIG; il Segugio: dove finisce lo scatto (in sottopixel).
	var spot: int = 0
	var target: int = 0
	var cooldown: int = 0
	## La Vedetta che ha appena girato al largo dalla processione: i tick che restano.
	var shy: int = 0
	## Dopo lo spintone: i tick che restano col faro puntato su GIG, e dove è GIG (per il disegno).
	var lock: int = 0
	var lock_at: Vector2 = Vector2.ZERO
	var vy: int = 0
	var broken: bool = false
	## Le celle sottili che una Colomba posata mette sulla sua schiena.
	var perch_cells: Array[Vector2i] = []

	func px() -> int:
		return x / SUB

	func py() -> int:
		return y / SUB

	func rect() -> Rect2i:
		return Rect2i(px() - size.x / 2, py() - size.y, size.x, size.y)


class Seal:
	var x: int
	var y: int
	var vx: int
	var vy: int
	var life: int

	func rect() -> Rect2i:
		return Rect2i(x / SUB - SEAL_SIZE.x / 2, y / SUB - SEAL_SIZE.y / 2, SEAL_SIZE.x, SEAL_SIZE.y)


var drones: Array[Drone] = []
var seals: Array[Seal] = []
## Lo spruzzo della Colomba: tick di schermo menta che restano.
var blind_t: int = 0
## Gli eventi del tick, con dove sono successi: [nome, x, y]. La stanza li suona e ci fa le scintille.
var events: Array = []
var grid: SolidGrid
## Le sagome delle processioni, che il faro non tocca: le passa la stanza a ogni tick.
var shields: Array[Rect2i] = []
## GIG ha spintonato la processione: al prossimo passo le Vedette vicine lo prendono.
var alert_pending: bool = false
## Gli sprite veri, per tipo; null se il tipo non ce l'ha (allora si disegna il greybox).
var _sheets: Dictionary = {}
var _last_py: int = 0


func is_empty() -> bool:
	return drones.is_empty()


func build(g: SolidGrid) -> void:
	grid = g
	drones.clear()
	seals.clear()
	blind_t = 0
	for e: Dictionary in g.entities:
		if e["tipo"] != "Nemico":
			continue
		var c: Dictionary = e["campi"]
		var tipo := str(c.get("tipo", ""))
		if tipo not in TIPI or c.get("arena") is String:
			continue
		var d := Drone.new()
		d.iid = str(e["iid"])
		d.tipo = tipo
		d.size = SIZE[tipo]
		var p: Vector2i = e["px"]
		d.home = Vector2i(p.x * SUB, p.y * SUB)
		d.still = str(c.get("stato", "fermo")) == "fermo"
		d.x_min = p.x
		d.x_max = p.x
		var path: Array = c.get("percorso", []) if c.get("percorso") is Array else []
		for q: Variant in path:
			if q is Vector2i:
				var qx: int = (q as Vector2i).x * TILE + TILE / 2
				d.x_min = mini(d.x_min, qx)
				d.x_max = maxi(d.x_max, qx)
		if d.still:
			d.x_min = p.x
			d.x_max = p.x
		drones.append(d)
	reset(true)


## Alla ripartenza tornano tutti al loro posto; quelli rotti restano rotti, se non `all`.
func reset(all: bool = false) -> void:
	seals.clear()
	blind_t = 0
	events.clear()
	alert_pending = false
	for d in drones:
		if all:
			d.broken = false
		if d.broken:
			continue
		d.x = d.home.x
		d.y = d.home.y
		d.y0 = d.home.y
		d.dir = -1 if d.still else 1
		d.t = 0
		d.spot = 0
		d.cooldown = 0
		d.shy = 0
		d.lock = 0
		d.vy = 0
		d.phase = Phase.PATROL
		if d.tipo == "colomba" and d.still:
			d.phase = Phase.PERCH
			_set_perch(d, true)


func is_broken(iid: String) -> bool:
	for d in drones:
		if d.iid == iid:
			return d.broken
	return false


## Un tick, dopo il passo di GIG. Restituisce l'energia persa (le spinte le dà già a GIG).
func step(p: PlatformPlayer) -> int:
	events.clear()
	blind_t = maxi(blind_t - 1, 0)
	if alert_pending:
		alert_pending = false
		_alert(p)
	var dmg := 0
	var jab := p.jab_box()
	var body := p.body()
	for d in drones:
		if d.broken:
			_tick_wreck(d)
			continue
		match d.tipo:
			"colomba":
				_tick_colomba(d, p)
			"vedetta":
				_tick_vedetta(d, p)
			"segugio":
				dmg += _tick_segugio(d, p, body)
		var r := d.rect()
		# Il salto in testa: GIG che scende e passa il dorso in questo tick (la Colomba posata no,
		# perché fa da gradino e GIG ci atterra sopra).
		if d.phase != Phase.PERCH and p.vy > 0 and _last_py <= r.position.y + 2 and p.py >= r.position.y - 2 \
				and body.position.x < r.end.x and body.end.x > r.position.x:
			_break(d)
			p.bounce()
			continue
		if jab.has_area() and jab.intersects(r):
			p.jab_hit = true
			if d.tipo == "segugio" and d.phase != Phase.PANT:
				events.append(["corazza", d.px(), d.py() - d.size.y / 2])
			else:
				_break(d)
				continue
		# Il contatto: la Vedetta bassa e il Segugio fuori dallo scatto spingono via, piano.
		if p.inv_t == 0 and d.tipo != "colomba" and d.phase != Phase.DASH and body.intersects(r):
			dmg += TOUCH_DAMAGE
			p.knock(1 if p.px >= d.px() else -1, TOUCH_KNOCK)
	dmg += _tick_seals(p)
	_last_py = p.py
	return dmg


func _break(d: Drone) -> void:
	d.broken = true
	d.phase = Phase.BROKEN
	d.t = 0
	d.vy = 0
	if not d.perch_cells.is_empty():
		_set_perch(d, false)
	events.append(["drone_rotto", d.px(), d.py() - d.size.y / 2])


## Il relitto cade fino al primo appoggio e resta lì.
func _tick_wreck(d: Drone) -> void:
	if d.t < 0:
		return
	d.t += 1
	if grid.floor_at(d.px() - d.size.x / 4, d.px() + d.size.x / 4, d.py(), true) or d.py() > grid.pixel_height():
		d.t = -1
		return
	d.vy += PlatformPlayer.to_sub(BROKEN_GRAVITY)
	var steps := d.vy / SUB
	for i in maxi(steps, 1):
		if grid.floor_at(d.px() - d.size.x / 4, d.px() + d.size.x / 4, d.py(), true):
			break
		d.y += SUB


# ---------------------------------------------------------------- Colomba

func _tick_colomba(d: Drone, p: PlatformPlayer) -> void:
	d.t += 1
	match d.phase:
		Phase.PERCH:
			pass
		Phase.PATROL:
			_patrol(d, COLOMBA_SPEED)
			d.cooldown = maxi(d.cooldown - 1, 0)
			if d.cooldown == 0 and _under(d, p):
				_go(d, Phase.AIM)
				events.append(["colomba_lente", d.px(), d.py()])
		Phase.AIM:
			if d.t >= COLOMBA_AIM:
				_go(d, Phase.DIVE)
		Phase.DIVE:
			var stop := d.t >= COLOMBA_DIVE_T or grid.rect_hits_solid(d.rect().position.x, d.py(), d.rect().end.x, d.py() + 4)
			if not stop:
				d.y += COLOMBA_DIVE * SUB / COLOMBA_DIVE_T
			else:
				_go(d, Phase.SPRAY)
				events.append(["spruzzo", d.px(), d.py()])
				var dx := absi(p.px - d.px())
				var dy := p.top() - d.py()
				if dx < 40 and dy > -30 and dy < 110:
					blind_t = BLIND_TICKS
					events.append(["accecato", p.px, p.top()])
		Phase.SPRAY:
			if d.t >= COLOMBA_SPRAY:
				_go(d, Phase.RISE)
		Phase.RISE:
			d.y = maxi(d.y - SUB, d.y0)
			if d.y == d.y0:
				_go(d, Phase.PATROL)
				d.cooldown = COLOMBA_REST


## GIG sotto la Colomba, entro 4 celle e senza muri in mezzo.
func _under(d: Drone, p: PlatformPlayer) -> bool:
	var dy := p.top() - d.py()
	if absi(p.px - d.px()) > d.size.x / 2 + 6 or dy < 0 or dy > COLOMBA_REACH:
		return false
	return _clear(Vector2(d.px(), d.py() + 2), Vector2(p.px, p.top() + 4))


## Le celle sottili sulla schiena di una Colomba posata: ci si sale sopra.
func _set_perch(d: Drone, on: bool) -> void:
	if on:
		if not d.perch_cells.is_empty():
			return  # già posata (alla ripartenza)
		var r := d.rect()
		var cy := (r.end.y - 1) / TILE
		for cx in range(r.position.x / TILE, (r.end.x - 1) / TILE + 1):
			if grid.cell(cx, cy) == SolidGrid.Cell.EMPTY:
				grid.set_cell(cx, cy, SolidGrid.Cell.THIN)
				d.perch_cells.append(Vector2i(cx, cy))
	else:
		for c in d.perch_cells:
			grid.set_cell(c.x, c.y, SolidGrid.Cell.EMPTY)
		d.perch_cells.clear()


# ---------------------------------------------------------------- Vedetta

func _tick_vedetta(d: Drone, p: PlatformPlayer) -> void:
	d.t += 1
	match d.phase:
		Phase.PATROL, Phase.SPOT:
			d.cooldown = maxi(d.cooldown - 1, 0)
			d.shy = maxi(d.shy - 1, 0)
			var locked := d.lock > 0
			if locked:
				d.lock -= 1
				d.lock_at = Vector2(p.px, p.py - p.height / 2)
			var hood := _hood_in_cone(d) if d.shy == 0 and not locked else -1
			if hood >= 0:
				# I cappucci nel cono: il faro si ferma lì sopra e la Vedetta non vede più niente.
				d.target = hood
				d.spot = 0
				_go(d, Phase.HALT)
				events.append(["non_identificabile", d.px(), d.py()])
				return
			# Mentre gira al largo, il faro si ricalibra: è la finestra di GIG.
			var seen := locked or (d.cooldown == 0 and d.shy == 0 and _in_cone(d, p))
			if seen:
				if d.spot == 0:
					events.append(["faro_rosso", d.px(), d.py()])
				d.spot += 1
				d.phase = Phase.SPOT
				if d.spot == SIREN_AT:
					events.append(["sirena", d.px(), d.py()])
				if d.spot >= SPOT_TICKS:
					_fire(d, p)
					_go(d, Phase.LOW)
					d.target = mini(d.y0 + LOW_DROP * SUB, _floor_below(d) - 2 * SUB)
			else:
				d.spot = maxi(d.spot - 2, 0)
				if d.spot == 0:
					d.phase = Phase.PATROL
					_patrol(d, VEDETTA_SPEED)
		Phase.LOW:
			# Scende, resta bassa a ricaricare, poi risale.
			if d.t <= LOW_MOVE:
				d.y = mini(d.y + maxi((d.target - d.y0) / LOW_MOVE, 0), d.target)
			elif d.t > LOW_MOVE + LOW_HOLD:
				d.y = maxi(d.y - LOW_DROP * SUB / LOW_MOVE, d.y0)
				if d.y == d.y0:
					_go(d, Phase.PATROL)
					d.spot = 0
					d.cooldown = SPOT_COOLDOWN
		Phase.HALT:
			if d.t >= HALT_TICKS:
				d.dir = -d.dir
				d.shy = SHY_TICKS
				_go(d, Phase.PATROL)


## Lo spintone: ogni Vedetta vicina e in ronda si gira verso GIG, faro rosso e sirena subito, e dopo
## ALERT_TICKS il sigillo (lo spara il passo normale, quando `spot` arriva a SPOT_TICKS).
func _alert(p: PlatformPlayer) -> void:
	for d in drones:
		if d.broken or d.tipo != "vedetta" or absi(d.px() - p.px) > ALERT_REACH:
			continue
		if not d.phase in [Phase.PATROL, Phase.SPOT, Phase.HALT]:
			continue
		if p.px != d.px():
			d.dir = signi(p.px - d.px())
		_go(d, Phase.SPOT)
		d.shy = 0
		d.cooldown = 0
		d.lock = ALERT_TICKS
		d.lock_at = Vector2(p.px, p.py - p.height / 2)
		d.spot = SPOT_TICKS - ALERT_TICKS
		events.append(["faro_rosso", d.px(), d.py()])
		events.append(["sirena", d.px(), d.py()])


## Il faro: dove si accende, davanti e sotto la Vedetta.
func _lamp(d: Drone) -> Vector2:
	return Vector2(d.px() + d.dir * (d.size.x / 2 - 6), d.py() - 2)


## GIG nel cono del faro: la testa, il petto o i piedi, senza tetti o muri in mezzo.
func _in_cone(d: Drone, p: PlatformPlayer) -> bool:
	for k: int in [p.height - 12, p.height / 2, 8]:
		if _lit(d, Vector2(p.px, p.py - k)):
			return true
	return false


## Il punto `q` nel cono del faro, senza tetti o muri in mezzo.
func _lit(d: Drone, q: Vector2) -> bool:
	var lamp := _lamp(d)
	var dy := q.y - lamp.y
	var fwd := (q.x - lamp.x) * d.dir
	if dy <= 0 or dy > CONE_DEPTH:
		return false
	if fwd < dy * CONE_NEAR - 8 or fwd > dy * CONE_FAR + 10:
		return false
	return _clear(lamp, q)


## La processione nel cono: la profondità (in pixel, dal faro) dove la luce si ferma, sopra i
## cappucci; -1 se non c'è.
func _hood_in_cone(d: Drone) -> int:
	var lamp := _lamp(d)
	var best := -1
	for r in shields:
		for i in 5:
			var q := Vector2(r.position.x + r.size.x * i / 4.0, r.position.y + 4)
			if _lit(d, q):
				var depth := maxi(int(q.y - lamp.y) - 10, 8)
				best = depth if best < 0 else mini(best, depth)
	return best


## Il sigillo parte dal faro, lento, verso il petto di GIG.
func _fire(d: Drone, p: PlatformPlayer) -> void:
	var from := _lamp(d)
	var to := Vector2(p.px, p.py - p.height / 2)
	var v := (to - from).normalized() * SEAL_SPEED
	var s := Seal.new()
	s.x = roundi(from.x) * SUB
	s.y = roundi(from.y) * SUB
	s.vx = PlatformPlayer.to_sub(v.x)
	s.vy = PlatformPlayer.to_sub(v.y)
	s.life = SEAL_LIFE
	seals.append(s)
	events.append(["sigillo_sparato", d.px(), d.py()])


func _tick_seals(p: PlatformPlayer) -> int:
	var dmg := 0
	var keep: Array[Seal] = []
	var body := p.body()
	for s in seals:
		s.x += s.vx
		s.y += s.vy
		s.life -= 1
		var r := s.rect()
		if p.inv_t == 0 and p.stuck_left == 0 and r.intersects(body):
			dmg += SEAL_DAMAGE
			p.stick(SEAL_PRESSES)
			p.inv_t = PlatformPlayer.INV_TICKS
			events.append(["pignorato", p.px, p.py - p.height / 2])
			continue
		var cx := floori(float(s.x / SUB) / TILE)
		var cy := floori(float(s.y / SUB) / TILE)
		if s.life <= 0 or grid.cell(cx, cy) != SolidGrid.Cell.EMPTY:
			events.append(["sigillo_muro", s.x / SUB, s.y / SUB])
			continue
		keep.append(s)
	seals = keep
	return dmg


# ---------------------------------------------------------------- Segugio

func _tick_segugio(d: Drone, p: PlatformPlayer, body: Rect2i) -> int:
	d.t += 1
	var dmg := 0
	var dx := p.px - d.px()
	var same_height := absi(p.py - d.py()) <= SEE_HEIGHT
	match d.phase:
		Phase.PATROL:
			if same_height and dx * d.dir > 0 and absi(dx) - d.size.x / 2 <= SEE_REACH and _clear(_muzzle(d), Vector2(p.px, p.py - 20)):
				_go(d, Phase.BARK)
				events.append(["abbaio", d.px(), d.py()])
			elif same_height and dx * d.dir < 0 and absi(dx) - d.size.x / 2 <= SNIFF_REACH:
				_go(d, Phase.SNIFF)
			elif not _walk(d, SEGUGIO_SPEED):
				_go(d, Phase.TURN)
		Phase.TURN:
			if d.t >= TURN_TICKS:
				d.dir = -d.dir
				_go(d, Phase.PATROL)
		Phase.SNIFF:
			if d.t >= SNIFF_TICKS:
				d.dir = -d.dir
				_go(d, Phase.PATROL)
		Phase.BARK:
			if d.t >= BARK_TICKS:
				_go(d, Phase.DASH)
				d.target = d.x + d.dir * DASH_DIST * SUB
				events.append(["scatto_segugio", d.px(), d.py()])
		Phase.DASH:
			var moved := _walk(d, float(DASH_DIST) / DASH_TICKS)
			if p.inv_t == 0 and body.intersects(d.rect()):
				dmg += DASH_DAMAGE
				p.knock(d.dir, DASH_KNOCK)
				events.append(["morso", p.px, p.py - 40])
			if not moved or d.t >= DASH_TICKS or (d.target - d.x) * d.dir <= 0:
				_go(d, Phase.PANT)
		Phase.PANT:
			if d.t >= PANT_TICKS:
				_go(d, Phase.PATROL)
	return dmg


func _muzzle(d: Drone) -> Vector2:
	return Vector2(d.px() + d.dir * d.size.x / 2, d.py() - 22)


## Un passo del Segugio, che non cade, non sale e non esce dal percorso: false se non può.
func _walk(d: Drone, speed: float) -> bool:
	var nx := d.x + d.dir * PlatformPlayer.to_sub(speed)
	var npx := nx / SUB
	var front := npx + d.dir * d.size.x / 2
	if npx < d.x_min or npx > d.x_max:
		return false
	if grid.rect_hits_solid(front - (1 if d.dir > 0 else 0), d.py() - d.size.y, front + (1 if d.dir < 0 else 0), d.py()):
		return false
	if not grid.floor_at(front - 2, front + 2, d.py(), true):
		return false
	d.x = nx
	return true


# ---------------------------------------------------------------- comuni

func _go(d: Drone, ph: int) -> void:
	d.phase = ph
	d.t = 0


## La ronda in aria, avanti e indietro fra gli estremi del percorso (fermo, se non ne ha).
func _patrol(d: Drone, speed: float) -> void:
	if d.still or d.x_max <= d.x_min:
		return
	d.x += d.dir * PlatformPlayer.to_sub(speed)
	if d.px() >= d.x_max:
		d.x = d.x_max * SUB
		d.dir = -1
	elif d.px() <= d.x_min:
		d.x = d.x_min * SUB
		d.dir = 1


## La prima superficie sotto il drone, in sottopixel.
func _floor_below(d: Drone) -> int:
	var y := d.py()
	var limit := y + CONE_DEPTH
	while y < limit:
		if grid.floor_at(d.px() - d.size.x / 2, d.px() + d.size.x / 2, y, true):
			return y * SUB
		y += 1
	return limit * SUB


## Niente pieni né sottili fra `a` e `b` (si controlla ogni 6 px).
func _clear(a: Vector2, b: Vector2) -> bool:
	var n := maxi(ceili(a.distance_to(b) / 6.0), 1)
	for i in range(1, n):
		var q := a.lerp(b, float(i) / n)
		var c := grid.cell(floori(q.x / TILE), floori(q.y / TILE))
		if c == SolidGrid.Cell.SOLID or c == SolidGrid.Cell.THIN:
			return false
	return true


func state_hash() -> Array:
	var h: Array = [blind_t, _last_py]
	for d in drones:
		h.append_array([d.x, d.y, d.dir, d.phase, d.t, d.spot, d.target, d.cooldown, d.vy, d.broken])
		if d.shy > 0:
			h.append(d.shy)
		if d.lock > 0:
			h.append(d.lock)
	for s in seals:
		h.append_array([s.x, s.y, s.life])
	return h


# ---------------------------------------------------------------- disegno (solo grafica)

func draw(v: CanvasItem, t: int, vis: Rect2, glow: Glow) -> void:
	for d in drones:
		var r := Rect2(d.rect())
		if not r.grow(160).intersects(vis):
			continue
		var f := _sprite_frame(d, t)
		if d.broken:
			if f == null:
				_draw_wreck(v, d)
			continue
		match d.tipo:
			"colomba":
				_draw_colomba(v, d, t, glow)
			"vedetta":
				_draw_vedetta(v, d, t, glow, f)
			"segugio":
				if f != null:
					_draw_segugio_lights(v, d, t, glow, f)
				else:
					_draw_segugio(v, d, t, glow)
	for s in seals:
		var r := Rect2(s.rect())
		v.draw_rect(r.grow(1), C_INK)
		v.draw_rect(r, C_WHITE)
		v.draw_rect(Rect2(r.position.x + 2, r.position.y + 3, r.size.x - 4, 3), C_RED)
		if glow != null:
			glow.halo(r.get_center(), 6, Color(C_RED, 0.35))


## Lo schermo menta ai bordi dopo lo spruzzo.
func draw_hud(h: CanvasItem) -> void:
	if blind_t <= 0:
		return
	var a := clampf(float(blind_t) / 30.0, 0.0, 1.0)
	a = ceilf(a * 4.0) / 4.0
	for i in 4:
		var s := float(10 * (i + 1))
		var col := Color(C_MINT, a * [0.45, 0.30, 0.18, 0.08][i])
		h.draw_rect(Rect2(0, 0, View.W, s), col)
		h.draw_rect(Rect2(0, View.H - s, View.W, s), col)
		h.draw_rect(Rect2(0, s, s, View.H - 2 * s), col)
		h.draw_rect(Rect2(View.W - s, s, s, View.H - 2 * s), col)


func _outline(v: CanvasItem, r: Rect2, fill: Color, edge: Color) -> void:
	v.draw_rect(r.grow(1), edge)
	v.draw_rect(r, fill)


func _draw_colomba(v: CanvasItem, d: Drone, t: int, glow: Glow) -> void:
	var r := Rect2(d.rect())
	var x := r.position.x
	var y := r.position.y
	var f := float(d.dir)
	# I rotori sopra (fermi se posata), il corpo bianco con la fascia menta, la lente sotto.
	if d.phase != Phase.PERCH:
		var spin := (t / 2) % 2 == 0
		v.draw_rect(Rect2(x + 2, y - 3, 12 if spin else 8, 1), C_STEEL)
		v.draw_rect(Rect2(r.end.x - 14, y - 3, 12 if not spin else 8, 1), C_STEEL)
		v.draw_rect(Rect2(x + 7, y - 2, 1, 2), C_STEEL)
		v.draw_rect(Rect2(r.end.x - 8, y - 2, 1, 2), C_STEEL)
	_outline(v, Rect2(x + 2, y + 3, r.size.x - 4, r.size.y - 8), C_WHITE, C_RED)
	v.draw_rect(Rect2(x + 2, y + 9, r.size.x - 4, 3), C_MINT)
	# La testa, dal lato dove guarda.
	var hx := r.get_center().x + f * (r.size.x / 2 - 6) - 3
	v.draw_rect(Rect2(hx, y, 6, 5), C_WHITE)
	v.draw_rect(Rect2(hx + (4 if f > 0 else 0), y + 2, 2, 1), C_INK)
	var lens := Vector2(r.get_center().x, r.end.y - 4)
	var lit := d.phase in [Phase.AIM, Phase.DIVE, Phase.SPRAY]
	var lc := C_RED if d.phase == Phase.AIM and (t / 4) % 2 == 0 else (C_MINT if lit else C_STEEL)
	v.draw_rect(Rect2(lens.x - 2, lens.y, 4, 3), lc)
	if lit and glow != null:
		glow.halo(lens + Vector2(0, 1), 7, Color(lc, 0.5))
	if d.phase == Phase.PERCH:
		v.draw_rect(Rect2(x + 9, r.end.y - 5, 1, 5), C_STEEL)
		v.draw_rect(Rect2(r.end.x - 10, r.end.y - 5, 1, 5), C_STEEL)
	if d.phase == Phase.SPRAY:
		# La nube di profumo che scende.
		var k := float(d.t) / COLOMBA_SPRAY
		for i in 7:
			var a := float(i) / 6.0 - 0.5
			var p := lens + Vector2(a * 60.0 * k, 10.0 + 70.0 * k * (1.0 - absf(a)))
			v.draw_rect(Rect2(p.round(), Vector2(3, 3)), Color(C_MINT, 0.7 * (1.0 - k)))


func _draw_vedetta(v: CanvasItem, d: Drone, t: int, glow: Glow, sf: AnimFrame = null) -> void:
	var r := Rect2(d.rect())
	var lamp := _lamp(d)
	# Con lo sprite il fascio parte dal faro disegnato; la luce a terra resta quella del gioco.
	var src := _point(d, sf, "lamp", lamp)
	# Il cono del faro, fino alla prima superficie sotto: giallo, rosso quando ha visto GIG.
	var depth := float(_floor_below(d) / SUB) - lamp.y
	depth = minf(depth, CONE_DEPTH)
	var f := float(d.dir)
	var cone := C_RED if d.phase == Phase.SPOT else C_BEAM
	var a := 0.10 if d.phase != Phase.SPOT else 0.10 + 0.12 * float(d.spot) / SPOT_TICKS
	if d.phase == Phase.HALT:
		# Il faro si ferma prima dei cappucci, e trema.
		depth = minf(depth, float(d.target))
		cone = C_WHITE
		a = 0.14 if (t / 3) % 2 == 0 else 0.22
	if d.lock > 0:
		# Dopo lo spintone il faro non spazza più: un fascio rosso stretto, puntato su GIG.
		var to := d.lock_at - src
		var side := Vector2(-to.y, to.x).normalized() * 9.0
		v.draw_colored_polygon(PackedVector2Array([src, d.lock_at + side, d.lock_at - side]),
			Color(C_RED, 0.22 if (t / 3) % 2 == 0 else 0.3))
		v.draw_arc(d.lock_at, 12.0, 0.0, TAU, 16, Color(C_RED, 0.7), 1.0)
	elif d.phase != Phase.LOW:
		v.draw_colored_polygon(PackedVector2Array([src, lamp + Vector2(f * depth * CONE_NEAR, depth),
			lamp + Vector2(f * depth * CONE_FAR, depth)]), Color(cone, a))
		v.draw_rect(Rect2(lamp.x + f * depth * CONE_NEAR - 1 if f > 0 else lamp.x + f * depth * CONE_FAR, lamp.y + depth - 1,
			absf(f * depth * (CONE_FAR - CONE_NEAR)), 2), Color(cone, a * 2.0))
	if sf != null:
		_draw_vedetta_lights(v, d, t, glow, sf, lamp)
		return
	# I quattro rotori, il corpo arancio col bordo rosso, il lampeggiante sopra.
	var spin := (t / 2) % 2 == 0
	for i in 2:
		var rx: float = r.position.x + (4.0 if i == 0 else r.size.x - 20.0)
		v.draw_rect(Rect2(rx, r.position.y - 3, 16 if spin else 10, 1), C_STEEL)
		v.draw_rect(Rect2(rx + 7, r.position.y - 2, 2, 3), C_STEEL)
	_outline(v, Rect2(r.position.x + 4, r.position.y + 2, r.size.x - 8, r.size.y - 6), C_ORANGE, C_RED)
	v.draw_rect(Rect2(r.position.x + 4, r.end.y - 8, r.size.x - 8, 2), C_ORANGE_DARK)
	# La stampante di sigilli, sotto, e la scritta.
	v.draw_rect(Rect2(r.get_center().x - 6, r.end.y - 4, 12, 4), C_STEEL)
	var blink := (t / (6 if d.phase == Phase.SPOT else 20)) % 2 == 0
	var bc := C_RED if blink else Color8(60, 120, 255)
	v.draw_rect(Rect2(r.get_center().x - 2, r.position.y - 1, 4, 3), bc)
	v.draw_rect(Rect2(lamp.x - 2, lamp.y - 2, 4, 4), C_RED if d.phase == Phase.SPOT else C_BEAM)
	if glow != null:
		glow.halo(Vector2(r.get_center().x, r.position.y), 6 if d.phase == Phase.SPOT else 4, Color(bc, 0.5))
		glow.halo(lamp, 5, Color(C_RED if d.phase == Phase.SPOT else C_BEAM, 0.45))
	_draw_halt_text(v, d, t, lamp)


## Il segno sul drone che una Persona chiede di rompere, quando GIG è a portata di jab (girato verso di
## lui, nella fascia del colpo): quattro angoli del colore del faro intorno al corpo, che lampeggiano
## piano. Dice «adesso sì» senza scritte. Solo disegno, fuori dall'impronta.
func draw_reach(v: CanvasItem, t: int, p: PlatformPlayer, wanted: Array[String]) -> void:
	if wanted.is_empty() or p == null:
		return
	var reach := jab_reach(p)
	for d in drones:
		if d.broken or not (d.iid in wanted) or not reach.intersects(d.rect()):
			continue
		if (t / 8) % 3 == 2:
			continue
		var r := Rect2(d.rect()).grow(3)
		var arm := 5.0
		for c in [r.position, Vector2(r.end.x, r.position.y), Vector2(r.position.x, r.end.y), r.end]:
			var q: Vector2 = c
			var sx := 1.0 if q.x <= r.position.x else -1.0
			var sy := 1.0 if q.y <= r.position.y else -1.0
			var ox := q.x if sx > 0 else q.x - 1.0
			var oy := q.y if sy > 0 else q.y - 1.0
			# Il bordo scuro sotto, poi il tratto chiaro: si legge sul cielo e sulle facciate.
			for k in 2:
				var col := C_INK if k == 0 else C_BEAM
				var g := 1.0 if k == 0 else 0.0
				v.draw_rect(Rect2(minf(ox, ox + sx * (arm - 1.0)) - g, oy - g, arm + 2.0 * g, 1.0 + 2.0 * g), col)
				v.draw_rect(Rect2(ox - g, minf(oy, oy + sy * (arm - 1.0)) - g, 1.0 + 2.0 * g, arm + 2.0 * g), col)


## Dove arriverebbe il jab se GIG lo tirasse adesso (lo stesso riquadro di PlatformPlayer.jab_box).
static func jab_reach(p: PlatformPlayer) -> Rect2i:
	var x0 := p.right() if p.facing > 0 else p.left() - PlatformPlayer.JAB_REACH
	return Rect2i(x0, p.py - PlatformPlayer.JAB_BAND.y, PlatformPlayer.JAB_REACH,
		PlatformPlayer.JAB_BAND.y - PlatformPlayer.JAB_BAND.x)


func _draw_halt_text(v: CanvasItem, d: Drone, t: int, lamp: Vector2) -> void:
	if d.phase == Phase.HALT and (t / 10) % 4 != 3:
		# La scritta della Vedetta, a lampi, dove si ferma la luce: sopra i cappucci, che si vede anche
		# quando il drone vola più su dello schermo.
		var at := Vector2(lamp.x + d.dir * (CONE_NEAR + CONE_FAR) * 0.5 * d.target, lamp.y + d.target - 6)
		UiFont.draw_text(v, at, "SOGGETTO NON IDENTIFICABILE", C_WHITE, 1, 1, C_INK, Color(0, 0, 0, 0), true)


func _draw_segugio(v: CanvasItem, d: Drone, t: int, glow: Glow) -> void:
	var r := Rect2(d.rect())
	var f := float(d.dir)
	var x := r.position.x
	var y := r.position.y
	# Le quattro zampe, che si muovono quando cammina o scatta.
	var walking := d.phase in [Phase.PATROL, Phase.DASH]
	var step := (t / (3 if d.phase == Phase.DASH else 8)) % 2
	for i in 4:
		var lx := x + 6 + i * 15
		var lift := 2 if walking and (i + step) % 2 == 0 else 0
		v.draw_rect(Rect2(lx, y + 22, 4, 18 - lift), C_STEEL)
		v.draw_rect(Rect2(lx - 1, r.end.y - 2 - lift, 6, 2), C_INK)
	# Il corpo basso e lungo, col bordo rosso.
	var body_y := y + 8 + (2 if d.phase == Phase.PATROL and step == 0 else 0)
	_outline(v, Rect2(x + 4, body_y, r.size.x - 8, 16), C_ORANGE, C_RED)
	v.draw_rect(Rect2(x + 4, body_y + 12, r.size.x - 8, 2), C_ORANGE_DARK)
	# Il collare-schermo e il muso a griglia: a terra a fiutare, alzato quando abbaia.
	var hx := r.get_center().x + f * (r.size.x / 2 - 4)
	var head_y := body_y + (8 if d.phase in [Phase.PATROL, Phase.SNIFF] else -6)
	var head := Rect2(hx - (0.0 if f > 0 else 12.0), head_y, 12, 10)
	_outline(v, head, C_ORANGE, C_RED)
	for i in 3:
		v.draw_rect(Rect2(head.position.x + 2 + i * 3, head.position.y + 3, 1, 5), C_INK)
	var eye := Vector2(head.position.x + (9 if f > 0 else 1), head.position.y + 1)
	var alarm := d.phase in [Phase.BARK, Phase.DASH]
	v.draw_rect(Rect2(eye, Vector2(2, 2)), C_RED if alarm else C_MINT)
	v.draw_rect(Rect2(hx - f * 10 - 5, body_y + 2, 10, 5), Color8(30, 40, 52))
	v.draw_rect(Rect2(hx - f * 10 - 4, body_y + 3, 8, 1), C_RED if alarm else C_MINT)
	# Il lampeggiante sul dorso: fisso in ronda, rosso e veloce quando abbaia.
	var bc := C_RED if alarm and (t / 4) % 2 == 0 else C_ORANGE_DARK
	v.draw_rect(Rect2(r.get_center().x - 2, body_y - 3, 4, 3), bc)
	if glow != null:
		if alarm:
			glow.halo(Vector2(r.get_center().x, body_y - 2), 8, Color(C_RED, 0.55))
			glow.halo(eye, 5, Color(C_RED, 0.5))
		else:
			glow.halo(eye, 3, Color(C_MINT, 0.35))
	if d.phase == Phase.PANT:
		# Il vapore dalle ventole.
		for i in 3:
			var k := float((t + i * 9) % 27) / 27.0
			v.draw_rect(Rect2(x + 14 + i * 14, body_y - 4 - 14 * k, 3, 3), Color(C_WHITE, 0.6 * (1.0 - k)))


# ------------------------------------------------- gli sprite veri (Segugio e Vedetta di SIDERA)

## Il foglio del tipo, se c'è quello vero in assets/sprites/<tipo>/.
func _sheet(tipo: String) -> SpriteSheet:
	if not _sheets.has(tipo):
		var s: SpriteSheet = null
		if FileAccess.file_exists("res://assets/sprites/%s/%s.json" % [tipo, tipo]):
			s = SpriteSheet.get_sheet(StringName(tipo))
			if s.source != SpriteSheet.Source.REAL:
				s = null
		_sheets[tipo] = s
	return _sheets[tipo]


## L'animazione della fase: i nomi sono quelli delle fasi; le fasi senza animazione usano la più vicina.
func anim_name(d: Drone) -> StringName:
	if d.broken:
		return &"broken"
	if d.tipo == "vedetta":
		return &"spot" if d.phase in [Phase.SPOT, Phase.LOW] or d.lock > 0 else &"patrol"
	match d.phase:
		Phase.SNIFF:
			return &"sniff"
		Phase.BARK:
			return &"bark"
		Phase.DASH:
			return &"dash"
		Phase.PANT:
			return &"pant"
		Phase.PATROL:
			return &"idle" if d.still else &"patrol"
	return &"idle"


## Il fotogramma da disegnare, o null se il tipo non ha lo sprite. Le animazioni in ciclo seguono
## l'orologio della stanza, quelle che finiscono il tempo della fase.
func _sprite_frame(d: Drone, t: int) -> AnimFrame:
	var s := _sheet(d.tipo)
	if s == null:
		return null
	var c := s.clip(anim_name(d))
	var total := maxi(c.total_ticks(), 1)
	var k := t % total if c.loop else mini(d.t, total - 1)
	for f in c.frames:
		k -= maxi(f.ticks, 1)
		if k < 0:
			return f
	return c.frames[c.frames.size() - 1]


## Un punto del fotogramma nel mondo (lo sprite guarda a destra: a sinistra si specchia).
func _point(d: Drone, f: AnimFrame, key: String, fallback: Vector2) -> Vector2:
	if f == null or not f.points.has(key):
		return fallback
	var q := f.points[key]
	return Vector2(d.px() + d.dir * q.x, d.py() + q.y)


## I corpi dei droni con lo sprite: li disegna il loro nodo, che ha la normal map e le luci.
func draw_bodies(v: CanvasItem, t: int, vis: Rect2) -> void:
	for d in drones:
		var f := _sprite_frame(d, t)
		if f == null or not Rect2(d.rect()).grow(160).intersects(vis):
			continue
		v.draw_set_transform(Vector2(d.px(), d.py()), 0.0, Vector2(d.dir, 1))
		v.draw_texture_rect_region(_sheet(d.tipo).texture, Rect2(-f.anchor, f.rect.size), Rect2(f.rect))
	v.draw_set_transform(Vector2.ZERO)


## Gli aloni della Vedetta vera: il lampeggiante e il faro, con la luce del fotogramma.
func _draw_vedetta_lights(v: CanvasItem, d: Drone, t: int, glow: Glow, f: AnimFrame, lamp: Vector2) -> void:
	_draw_halt_text(v, d, t, lamp)
	if glow == null or f.has_tag(AnimFrame.TAG_LIGHT_OFF):
		return
	var alert := f.has_tag(AnimFrame.TAG_LIGHT_ALERT)
	var blink := (t / (6 if alert else 20)) % 2 == 0
	var bc := C_RED if blink else Color8(60, 120, 255)
	glow.halo(_point(d, f, "beacon", lamp), 6 if alert else 4, Color(bc, 0.5))
	glow.halo(_point(d, f, "lamp", lamp), 6 if alert else 5, Color(C_RED if alert else C_BEAM, 0.5))


## Gli aloni del Segugio vero: l'occhio, il lampeggiante, il collare e la bocca quando abbaia; il vapore
## dalle ventole quando ansima.
func _draw_segugio_lights(v: CanvasItem, d: Drone, t: int, glow: Glow, f: AnimFrame) -> void:
	var feet := Vector2(d.px(), d.py())
	if d.phase == Phase.PANT:
		var vent := _point(d, f, "vent", feet + Vector2(-d.dir * 20, -20))
		for i in 3:
			var k := float((t + i * 9) % 27) / 27.0
			var q := vent + Vector2(-d.dir * (2.0 + i * 3.0) * k + (i - 1) * 3, -16.0 * k)
			v.draw_rect(Rect2(q.round(), Vector2(3, 3)), Color(C_WHITE, 0.6 * (1.0 - k)))
	if glow == null or f.has_tag(AnimFrame.TAG_LIGHT_OFF):
		return
	var eye := _point(d, f, "eye", feet + Vector2(d.dir * 26, -30))
	if f.has_tag(AnimFrame.TAG_LIGHT_ALERT):
		glow.halo(eye, 5, Color(C_RED, 0.5))
		if (t / 4) % 2 == 0:
			glow.halo(_point(d, f, "beacon", eye), 8, Color(C_RED, 0.55))
		glow.halo(_point(d, f, "collar", eye), 4, Color(C_RED, 0.3))
		if f.points.has("mouth"):
			glow.halo(_point(d, f, "mouth", eye), 5, Color(C_RED, 0.45))
	else:
		glow.halo(eye, 3, Color(C_RED, 0.3))


func _draw_wreck(v: CanvasItem, d: Drone) -> void:
	var r := Rect2(d.rect())
	var h := maxf(r.size.y * 0.45, 6.0)
	var w := Rect2(r.position.x + 2, r.end.y - h, r.size.x - 4, h)
	v.draw_rect(w.grow(1), C_INK)
	v.draw_rect(w, C_WRECK)
	var accent := C_MINT if d.tipo == "colomba" else C_ORANGE_DARK
	v.draw_rect(Rect2(w.position.x + 3, w.position.y + 2, w.size.x * 0.4, 2), accent)
	v.draw_rect(Rect2(w.end.x - 8, w.position.y - 3, 5, 3), C_WRECK)
