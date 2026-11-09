class_name Processions
extends RefCounted
## Le processioni (legenda LDtk, §4c): una posta di perdoni che avanza piano lungo il suo
## `percorso`, col passo della nazzicata, e alla fine gira nel portone di `sparisce_a`.
##
## - Non si tocca, non si attraversa e non si colpisce: è un muro morbido. GIG che la raggiunge
##   si ferma da solo, senza danno; se GIG le sta davanti, lei aspetta. Vicino a lei il jab non parte.
## - Si passa sopra, sui `Sottile` della strada: sopra i cappucci GIG non viene fermato.
## - I droni la rispettano: la stanza passa i suoi rettangoli ai droni (`shields`), e il faro della
##   Vedetta si ferma prima dei cappucci.
## - `nascosta`: solo sfondo, cammina ma non ferma niente.
## - Lo spintone (Luigi, 8 novembre 2026, variante «La Vedetta lo nota»): SCATTO a terra, attaccato
##   al confratello di coda. Lui barcolla, la fila si ferma e si apre per PUSH_OPEN tick e GIG ci passa
##   in mezzo; ma uscendo dai cappucci col trambusto la Vedetta lo vede subito (`pushed`, che la stanza
##   passa a `Drones.alert`).

const TILE := SolidGrid.TILE
## Le posizioni e la velocità in centesimi di pixel: 0,6 celle al secondo sono 20 centesimi a tick.
const CENT := 100
## Quanto vicino a lei il jab non parte, in pixel.
const JAB_REACH := 40
## Il giro nel portone: sfuma in un secondo e mezzo.
const ENTER_TICKS := 90
## Sopra i cappucci: GIG coi piedi più in alto di così non viene fermato.
const OVER := 6
## Lo spintone: quanto resta aperta la fila, e quanto vicino al confratello di coda si spinge.
const PUSH_OPEN := 45
const PUSH_REACH := 4

const C_LILAC := Color8(170, 150, 210)
const C_ROBE := Color8(238, 236, 230)
const C_ROBE_SHADE := Color8(190, 186, 182)
const C_INK := Color8(24, 20, 30)


class Walk:
	var iid: String
	var size: Vector2i
	## In basso al centro: x in centesimi di pixel, y in pixel.
	var home: int
	var x: int
	var y: int
	var speed: int
	## Le x (in pixel) dove va, in ordine; l'ultima è il portone, se c'è.
	var stops: Array[int] = []
	var door: bool = false
	var leg: int = 0
	var dir: int = 1
	var hidden: bool = false
	## 0 mentre cammina; poi i tick del giro nel portone.
	var enter_t: int = 0
	var gone: bool = false
	## I tick che restano della fila aperta dallo spintone (0 = chiusa).
	var open_t: int = 0
	## In questo passo è andata avanti (solo per il disegno: nazzicata o fermi).
	var moving: bool = false

	func px() -> int:
		return x / CENT

	func rect() -> Rect2i:
		return Rect2i(px() - size.x / 2, y - size.y, size.x, size.y)

	func solid() -> bool:
		return not hidden and not gone and enter_t == 0


var walks: Array[Walk] = []
## Gli eventi del passo: [nome, x, y].
var events: Array = []
## In questo passo GIG ha spintonato un confratello.
var pushed: bool = false
## Lo sprite vero dei perdoni (assets/sprites/perdono/); null finché non si carica o se manca.
var _sheet_cache: SpriteSheet = null
var _sheet_tried: bool = false
## La nazzicata: i due della coppia sono sfasati di mezzo ciclo.
const NAZZICA_PHASE := 64


func is_empty() -> bool:
	return walks.is_empty()


func build(g: SolidGrid) -> void:
	walks.clear()
	for e: Dictionary in g.entities:
		if e["tipo"] != "Processione":
			continue
		var c: Dictionary = e["campi"]
		var w := Walk.new()
		w.iid = str(e["iid"])
		w.size = e["size"]
		var p: Vector2i = e["px"]
		w.home = p.x * CENT
		w.y = p.y
		var v: Variant = c.get("velocita", 0.6)
		w.speed = maxi(roundi(float(v if v is float or v is int else 0.6) * TILE * CENT / 60.0), 1)
		w.hidden = c.get("nascosta", false) == true
		var path: Array = c.get("percorso", []) if c.get("percorso") is Array else []
		for q: Variant in path:
			if q is Vector2i:
				w.stops.append((q as Vector2i).x * TILE + TILE / 2)
		# Dal punto di partenza si va verso la fine del percorso: le tappe alle spalle si saltano.
		if not w.stops.is_empty():
			var ahead := signi(w.stops[-1] - p.x)
			while w.stops.size() > 1 and (w.stops[0] - p.x) * ahead <= 0:
				w.stops.pop_front()
		var door: Variant = c.get("sparisce_a")
		if door is Vector2i:
			w.stops.append((door as Vector2i).x * TILE + TILE / 2)
			w.door = true
		walks.append(w)
	reset()


## Alla ripartenza ogni processione torna dove comincia.
func reset() -> void:
	events.clear()
	pushed = false
	for w in walks:
		w.x = w.home
		w.leg = 0
		w.enter_t = 0
		w.gone = false
		w.open_t = 0
		w.dir = 1 if w.stops.is_empty() or w.stops[0] * CENT >= w.home else -1


## Un passo, dopo quello di GIG: avanza, ferma GIG che ci va contro e decide se il jab può partire.
## `push` è SCATTO appena premuto: attaccato alla coda, a terra, è lo spintone.
func step(p: PlatformPlayer, push: bool = false) -> void:
	events.clear()
	pushed = false
	for w in walks:
		w.moving = false
		if w.gone:
			continue
		if w.open_t > 0:
			# La fila aperta si ferma: il confratello spinto ritrova l'equilibrio.
			w.open_t -= 1
			continue
		if w.enter_t > 0:
			w.enter_t += 1
			if w.enter_t >= ENTER_TICKS:
				w.gone = true
			continue
		if w.leg >= w.stops.size():
			continue
		var target := w.stops[w.leg] * CENT
		var dir := signi(target - w.x)
		var nx := w.x + dir * mini(w.speed, absi(target - w.x))
		# GIG davanti, a terra: aspetta che si tolga. Se le spinge da dietro, lei va avanti lo stesso.
		var ahead := (p.px - w.px()) * dir > 0
		if not w.hidden and ahead and _against(p, Rect2i(nx / CENT - w.size.x / 2, w.y - w.size.y, w.size.x, w.size.y)):
			continue
		w.moving = nx != w.x
		w.x = nx
		if dir != 0:
			w.dir = dir
		if w.x == target:
			w.leg += 1
			if w.leg >= w.stops.size() and w.door:
				w.enter_t = 1
				events.append(["portone", w.px(), w.y - w.size.y / 2])
	p.jab_block = false
	for w in walks:
		if not w.solid():
			continue
		var r := w.rect()
		var body := _body(p)
		if r.grow_individual(JAB_REACH, 0, JAB_REACH, 0).intersects(body):
			p.jab_block = true
		if w.open_t > 0:
			continue
		var behind := (p.px - w.px()) * w.dir < 0
		if push and behind and p.state == PlatformPlayer.State.GROUND and p.py > r.position.y + OVER \
				and r.grow_individual(PUSH_REACH, 0, PUSH_REACH, 0).intersects(body):
			w.open_t = PUSH_OPEN
			pushed = true
			events.append(["spintone", r.position.x if w.dir > 0 else r.end.x, w.y - w.size.y / 2])
			continue
		if _against(p, r):
			# Il muro morbido: GIG torna al bordo dalla sua parte e si ferma.
			if p.px < r.get_center().x:
				p.px -= p.right() - r.position.x
			else:
				p.px += r.end.x - p.left()
			p.rx = 0
			p.vx = 0


## Le sagome che il faro dei droni non tocca.
func shields() -> Array[Rect2i]:
	var out: Array[Rect2i] = []
	for w in walks:
		if w.solid():
			out.append(w.rect())
	return out


func _body(p: PlatformPlayer) -> Rect2i:
	return Rect2i(p.left(), p.top(), p.right() - p.left(), p.py - p.top())


## GIG dentro il rettangolo, e non sopra i cappucci.
func _against(p: PlatformPlayer, r: Rect2i) -> bool:
	return _body(p).intersects(r) and p.py > r.position.y + OVER


func state_hash() -> Array:
	var h: Array = []
	for w in walks:
		h.append_array([w.x, w.leg, w.enter_t, w.gone])
		if w.open_t > 0:
			h.append(w.open_t)
	return h


# ------------------------------------------------------------------ disegno

## Lo sprite dei perdoni, se c'è quello vero.
func _sheet() -> SpriteSheet:
	if not _sheet_tried:
		_sheet_tried = true
		if FileAccess.file_exists("res://assets/sprites/perdono/perdono.json"):
			var s := SpriteSheet.get_sheet(&"perdono")
			if s.source == SpriteSheet.Source.REAL:
				_sheet_cache = s
	return _sheet_cache


## Il confratello `i` della coppia (0 a sinistra) è quello di coda?
static func is_tail(w: Walk, i: int) -> bool:
	return (i == 0) == (w.dir > 0)


## L'animazione del confratello: dopo lo spintone quello di coda barcolla e quello davanti si
## scansa; poi la nazzicata se la fila avanza, fermi se aspetta.
static func anim_name(w: Walk, i: int) -> StringName:
	if w.open_t > 0:
		return &"barcollo" if is_tail(w, i) else &"scansa"
	return &"nazzica" if w.moving else &"idle"


## Il fotogramma del confratello `i` al tick `t` della stanza, o null senza lo sprite.
func brother_frame(w: Walk, i: int, t: int) -> AnimFrame:
	var s := _sheet()
	if s == null:
		return null
	var c := s.clip(anim_name(w, i))
	var total := maxi(c.total_ticks(), 1)
	var k: int
	if c.loop:
		var shift := NAZZICA_PHASE if c.total_ticks() == 2 * NAZZICA_PHASE else total / 2
		k = (t + i * shift) % total
	else:
		k = mini(PUSH_OPEN - w.open_t, total - 1)
	for f in c.frames:
		k -= maxi(f.ticks, 1)
		if k < 0:
			return f
	return c.frames[c.frames.size() - 1]


## Dove stanno i piedi del confratello `i`: ai due quarti della sagoma, allargati dallo spintone.
func _brother_x(w: Walk, i: int, r: Rect2) -> float:
	var k := sin(PI * float(w.open_t) / PUSH_OPEN) if w.open_t > 0 else 0.0
	return r.get_center().x + (i * 2 - 1) * r.size.x / 4.0 + (i * 2 - 1) * roundf(14.0 * k)


## I perdoni veri: li disegna il nodo coi corpi, con la normal map e le luci, sopra GIG.
func draw_bodies(v: CanvasItem, t: int, vis: Rect2) -> void:
	var s := _sheet()
	if s == null:
		return
	for w in walks:
		if w.gone:
			continue
		var r := Rect2(w.rect())
		if not r.grow(60).intersects(vis):
			continue
		var a := 1.0 - float(w.enter_t) / ENTER_TICKS
		if w.hidden:
			a *= 0.35
		for i in 2:
			var f := brother_frame(w, i, t)
			v.draw_set_transform(Vector2(roundf(_brother_x(w, i, r)), r.end.y), 0.0, Vector2(w.dir, 1))
			v.draw_texture_rect_region(s.texture, Rect2(-f.anchor, f.rect.size), Rect2(f.rect), Color(1, 1, 1, a))
	v.draw_set_transform(Vector2.ZERO)


## Senza lo sprite, il greybox: il rettangolo lilla con la freccia del verso e, dentro, due confratelli
## bianchi incappucciati che dondolano piano. Niente bordo rosso e niente luce che pulsa: non è un
## pericolo e non si usa.
func draw(v: CanvasItem, t: int, vis: Rect2) -> void:
	if _sheet() != null:
		return
	for w in walks:
		if w.gone:
			continue
		var r := Rect2(w.rect())
		if not r.grow(40).intersects(vis):
			continue
		var a := 1.0 - float(w.enter_t) / ENTER_TICKS
		if w.hidden:
			a *= 0.35
		v.draw_rect(r, Color(C_LILAC, 0.16 * a))
		v.draw_rect(Rect2(r.position.x, r.position.y, r.size.x, 1), Color(C_LILAC, 0.5 * a))
		# La freccia del verso, sopra.
		var ax := r.get_center().x
		var ay := r.position.y - 8
		var f := float(w.dir)
		v.draw_colored_polygon(PackedVector2Array([Vector2(ax + 5 * f, ay), Vector2(ax - 3 * f, ay - 4),
			Vector2(ax - 3 * f, ay + 4)]), Color(C_LILAC, 0.8 * a))
		# Lo spintone: la fila si apre (i due si allargano) e quello di coda barcolla avanti e indietro.
		var k := sin(PI * float(w.open_t) / PUSH_OPEN) if w.open_t > 0 else 0.0
		for i in 2:
			# La nazzicata: un dondolio lento di lato, sfasato fra i due.
			var sway := roundf(sin(float(t) * 0.045 + i * 1.7) * 2.0)
			var tail := is_tail(w, i)
			var cx := _brother_x(w, i, r) + sway
			var lean := roundf(sin(float(w.open_t) * 0.45) * 6.0 * k) if tail else 0.0
			_draw_brother(v, Vector2(cx, r.end.y), r.size.y - 6, f, a, lean)


## `lean`: di quanti pixel pende in cima (lo spintone), coi piedi fermi.
func _draw_brother(v: CanvasItem, feet: Vector2, h: float, f: float, a: float, lean: float = 0.0) -> void:
	var top := feet.y - h
	var hx := feet.x + lean
	# La tonaca lunga fino ai piedi scalzi, più larga in basso; il cappuccio a punta tonda.
	v.draw_colored_polygon(PackedVector2Array([Vector2(hx - 7, top + 22), Vector2(hx + 7, top + 22),
		Vector2(feet.x + 11, feet.y - 4), Vector2(feet.x - 11, feet.y - 4)]), Color(C_ROBE, a))
	var mx := feet.x + lean * 0.5
	v.draw_rect(Rect2(mx - 11 if f < 0 else mx + 3, top + 30, 8, h - 36), Color(C_ROBE_SHADE, a))
	v.draw_rect(Rect2(hx - 6, top + 2, 12, 22), Color(C_ROBE, a))
	v.draw_rect(Rect2(hx - 4, top - 2, 8, 4), Color(C_ROBE, a))
	# I due fori degli occhi, dal lato dove va.
	v.draw_rect(Rect2(hx + f * 2 - 1, top + 9, 2, 2), Color(C_INK, a))
	v.draw_rect(Rect2(hx + f * 5 - 1, top + 9, 2, 2), Color(C_INK, a))
	# I piedi scalzi.
	v.draw_rect(Rect2(feet.x - 6, feet.y - 3, 5, 3), Color(Color8(214, 170, 140), a))
	v.draw_rect(Rect2(feet.x + 2, feet.y - 3, 5, 3), Color(Color8(214, 170, 140), a))
