class_name Favors
extends RefCounted
## Le persone da aiutare e quello che c'è intorno (legenda LDtk, §4): i ristori, gli oggetti da
## portare, le Persone che chiedono e ringraziano, e le battute in gioco, che non fermano l'azione.
##
## - Ristoro: GIG ci passa sopra e se lo prende; ridà energia. Quelli che sono il premio di una
##   Persona restano nascosti finché lei non ringrazia.
## - Oggetto: SU accanto, coi piedi a terra, lo prende (uno alla volta); SU accanto all'entità del
##   suo `per` lo posa lì.
## - Persona: con GIG vicino dice `chiede`; quando quello che le `serve` è fatto (un Oggetto posato
##   lì, o il drone con quell'iid rotto) e GIG è vicino, dice `ringrazia` e apre i suoi `premio`:
##   i ristori compaiono, i cancelli si aprono (li apre chi usa `opened`).
## - Firma: la tag REVENGE di Totò sul muro (gameplay, «le firme di Totò»): GIG ci passa sopra e
##   la prende, per il punteggio, come le gemme di Jazz Jackrabbit. Presa resta grigia sul muro, e
##   resta presa anche alla ripartenza.
## - Battuta: `vista` quando GIG ci arriva vicino, `passaggio` quando la supera, `dopo_arena` appena
##   finisce l'arena della stanza. Una volta sola.
## - Il caffè dà anche uno scatto: per COFFEE_TICKS GIG corre al COFFEE_PCT per cento. La bombola di
##   ARIA+ non ridà energia: ricarica la Scarica (l'evento «scarica», che la stanza passa a Game).
##
## I fumetti non entrano nell'impronta e non cambiano niente: il testo sta nei file privati
## (SceneLines) e senza quei file il gioco va uguale, solo senza fumetti. Lo stesso per le voci
## (SceneVoices): se ci sono, il fumetto resta finché la voce finisce e la stanza la suona.

const TILE := SolidGrid.TILE
## SU per prendere o posare: come le leve.
const USE_REACH := 40
## La Persona parla con GIG entro 6 celle, alla sua altezza (±3 celle).
const TALK_REACH := 120
const TALK_HEIGHT := 60
## Se GIG si allontana oltre il doppio, alla volta dopo lo richiede.
const TALK_AGAIN := 240
## La battuta «vista»: GIG entro 10 celle in orizzontale e 7 in verticale.
const SEE_REACH := Vector2i(200, 140)
## Quanta energia ridà ogni ristoro; la scarcella va oltre il massimo, fino a OVER_MAX.
const RISTORO := {"taralli": 20, "caffe": 30, "panzerotto": 60, "scarcella": 150, "bombola": 0}
const OVER_MAX := 150
## Lo scatto del caffè: due secondi e mezzo al 125 per cento.
const COFFEE_TICKS := 150
const COFFEE_PCT := 125
## Una firma vale mille punti; dopo la presa il lampo dura mezzo secondo e il contatore resta in alto
## due secondi e mezzo.
const FIRMA_POINTS := 1000
const FIRMA_FLASH := 30
const FIRMA_HUD := 150
## Il file e la scena delle battute in gioco (SceneLines).
const LINES_SCENE := "in_gioco"
## I fumetti: larghezza del testo, e quanto restano (in base alla lunghezza).
const BUBBLE_W := 168
const BUBBLE_MIN := 120
const BUBBLE_PER_CHAR := 3
const BUBBLE_MAX := 420

const C_PERSON := Color8(150, 132, 170)
const C_PERSON_DARK := Color8(92, 80, 108)
const C_SKIN := Color8(214, 170, 140)
const C_CYAN := Color8(72, 220, 232)
const C_INK := Color8(24, 20, 30)
const C_PAPER := Color8(244, 238, 222)
const C_TEXT := Color8(36, 30, 40)
const C_WOOD := Color8(140, 96, 56)
const C_GOLD := Color8(214, 160, 72)
const C_BROWN := Color8(120, 76, 40)
const C_GREEN := Color8(84, 150, 72)


class Item:
	var iid: String
	var tipo: String
	## In basso al centro, come le entità LDtk.
	var px: Vector2i
	var home: Vector2i
	var hidden: bool = false
	var taken: bool = false
	## Solo gli oggetti: dove vanno posati, e lo stato (0 a terra, 1 in mano, 2 posato).
	var per: String = ""
	var state: int = 0

	func rect() -> Rect2i:
		return Rect2i(px.x - 10, px.y - 20, 20, 20)


class Firma:
	var iid: String
	var numero: int = 0
	## In basso al centro, come le entità LDtk (la tag sta un po' sopra il piano).
	var px: Vector2i
	var taken: bool = false
	## Tick che restano del lampo della presa (solo per il disegno).
	var flash: int = 0

	## La tag: 44×18 sopra il perno.
	func rect() -> Rect2i:
		return Rect2i(px.x - 22, px.y - 18, 44, 18)


class Person:
	var iid: String
	var id: String
	var chiede: String
	var serve: String
	var premio: Array = []
	var ringrazia: String
	var px: Vector2i
	var asked: bool = false
	var thanked: bool = false
	## Da quanti tick ha chiesto (finché GIG resta vicino) e da quanti ha ringraziato: servono solo alle
	## pose dello sprite, fuori dall'impronta.
	var asked_t: int = 0
	var thanked_t: int = 0


class Line:
	var iid: String
	var chi: String
	var id: String
	var quando: String
	var px: Vector2i
	var said: bool = false


class Bubble:
	var lines: PackedStringArray
	## Dove punta: la testa di chi parla (fissa), o GIG se `on_player`.
	var at: Vector2
	var on_player: bool = false
	var tag: String = ""
	var t: int = 0
	var life: int = 0


var ristori: Array[Item] = []
var oggetti: Array[Item] = []
var persone: Array[Person] = []
var battute: Array[Line] = []
var firme: Array[Firma] = []
## Tick che restano del contatore delle firme in alto (solo per il disegno).
var firme_hud: int = 0
var held: Item = null
## I premi aperti dalle Persone (iid di cancelli e ristori).
var opened: PackedStringArray = []
## Gli eventi del passo: [nome, x, y].
var events: Array = []
## Un premio si è aperto in questo passo: chi ha i cancelli li riapplica.
var changed: bool = false
var bubbles: Array[Bubble] = []
## Le voci da far partire in questo passo (AudioStream): le suona la stanza. Fuori dall'impronta.
var voices: Array = []
var lines_file: String = "prologo"
## Tick che restano dello scatto del caffè.
var coffee_t: int = 0
## L'arena della stanza è finita: le battute `dopo_arena` partono. Lo aggiorna la stanza.
var arena_done: bool = false
var _where: Dictionary = {}
## Gli sprite veri delle Persone, per id (null se non c'è): vedi person_pose().
var _sheets: Dictionary = {}
## Il fotogramma della posa «botola» del fruttivendolo in cui l'anta è su, sopra la testa: da lì la
## serranda della cantina si disegna aperta.
const BOTOLA_UP_FRAME := 6


func is_empty() -> bool:
	return ristori.is_empty() and oggetti.is_empty() and persone.is_empty() and battute.is_empty() and firme.is_empty()


## Legge Ristoro, Oggetto, Persona, Battuta e Firma dalle entità della griglia.
func build(g: SolidGrid) -> void:
	ristori.clear()
	oggetti.clear()
	persone.clear()
	battute.clear()
	firme.clear()
	_where.clear()
	var prizes := {}
	for e: Dictionary in g.entities:
		_where[String(e["iid"])] = e["px"]
		var c: Dictionary = e["campi"]
		match String(e["tipo"]):
			"Ristoro", "Oggetto":
				var it := Item.new()
				it.iid = e["iid"]
				it.tipo = str(c.get("tipo", ""))
				it.home = e["px"]
				it.per = c.get("per") if c.get("per") is String else ""
				(ristori if e["tipo"] == "Ristoro" else oggetti).append(it)
			"Persona":
				var p := Person.new()
				p.iid = e["iid"]
				p.id = str(c.get("id", ""))
				p.chiede = c.get("chiede") if c.get("chiede") is String else ""
				p.serve = c.get("serve") if c.get("serve") is String else ""
				p.premio = c.get("premio") if c.get("premio") is Array else []
				p.ringrazia = c.get("ringrazia") if c.get("ringrazia") is String else ""
				p.px = e["px"]
				persone.append(p)
				for r: Variant in p.premio:
					prizes[str(r)] = true
			"Battuta":
				var l := Line.new()
				l.iid = e["iid"]
				l.chi = str(c.get("chi", ""))
				l.id = c.get("id_testo") if c.get("id_testo") is String else ""
				l.quando = str(c.get("quando", "vista"))
				l.px = e["px"]
				battute.append(l)
			"Firma":
				var f := Firma.new()
				f.iid = e["iid"]
				f.numero = int(c.get("numero", 0)) if c.get("numero") != null else 0
				f.px = e["px"]
				firme.append(f)
	for it in ristori:
		it.hidden = prizes.has(it.iid)
	reset(true)


## Alla ripartenza i favori fatti restano fatti e i ristori presi restano presi; l'oggetto in mano
## torna al suo posto. `all` rimette tutto com'era.
func reset(all: bool = false) -> void:
	events.clear()
	bubbles.clear()
	changed = false
	coffee_t = 0
	if held != null:
		held.state = 0
		held.px = held.home
		held = null
	if all:
		opened.clear()
	for it in ristori:
		it.px = it.home
		if all:
			it.taken = false
	for it in oggetti:
		if all or it.state != 2:
			it.state = 0
			it.px = it.home
	for p in persone:
		p.asked = false
		p.asked_t = 0
		if all:
			p.thanked = false
			p.thanked_t = 0
	for l in battute:
		if all:
			l.said = false
	firme_hud = 0
	for f in firme:
		f.flash = 0
		if all:
			f.taken = false
	if all:
		var prizes := {}
		for p in persone:
			for r: Variant in p.premio:
				prizes[str(r)] = true
		for it in ristori:
			it.hidden = prizes.has(it.iid)


## Un passo, dopo quello di GIG: `up` è SU appena premuto. Torna l'energia dopo i ristori.
func step(p: PlatformPlayer, up: bool, dr: Drones, energy: int) -> int:
	events.clear()
	voices.clear()
	changed = false
	for i in range(bubbles.size() - 1, -1, -1):
		bubbles[i].t += 1
		if bubbles[i].t >= bubbles[i].life:
			bubbles.remove_at(i)
	var body := Rect2i(p.left(), p.top(), p.right() - p.left(), p.py - p.top())
	for it in ristori:
		if it.hidden or it.taken or not body.intersects(it.rect()):
			continue
		it.taken = true
		var gain: int = RISTORO.get(it.tipo, 0)
		if it.tipo == "scarcella":
			energy = maxi(energy, mini(energy + gain, OVER_MAX))
		else:
			energy = maxi(energy, mini(energy + gain, Game.ENERGY_MAX))
		events.append(["ristoro", it.px.x, it.px.y - 10])
		if it.tipo == "caffe":
			coffee_t = COFFEE_TICKS + 1
		elif it.tipo == "bombola":
			events.append(["scarica", it.px.x, it.px.y - 10])
	firme_hud = maxi(firme_hud - 1, 0)
	for f in firme:
		f.flash = maxi(f.flash - 1, 0)
		if f.taken or not body.intersects(f.rect()):
			continue
		f.taken = true
		f.flash = FIRMA_FLASH
		firme_hud = FIRMA_HUD
		events.append(["firma", f.px.x, f.px.y - 9])
	coffee_t = maxi(coffee_t - 1, 0)
	p.boost_pct = COFFEE_PCT if coffee_t > 0 else 100
	var grounded := p.state == PlatformPlayer.State.GROUND
	if held != null:
		held.px = Vector2i(p.px + 10 * p.facing, p.top() + 40)
	if up and grounded:
		_use(p)
	for q in persone:
		_person(q, p, dr)
	for l in battute:
		if l.said:
			continue
		var d := Vector2i(absi(p.px - l.px.x), absi(p.py - l.px.y))
		if (l.quando == "vista" and d.x <= SEE_REACH.x and d.y <= SEE_REACH.y) or (l.quando == "passaggio" and p.px >= l.px.x) \
				or (l.quando == "dopo_arena" and arena_done):
			l.said = true
			_line_bubble(l, p)
			events.append(["battuta", l.px.x, l.px.y])
	return energy


## SU: posa l'oggetto in mano dove va, oppure prende quello a portata.
func _use(p: PlatformPlayer) -> void:
	if held != null:
		var to: Variant = _where.get(held.per)
		if to is Vector2i and absi(p.px - (to as Vector2i).x) <= USE_REACH and (to as Vector2i).y >= p.top() - 20 \
				and (to as Vector2i).y <= p.py + 10:
			held.state = 2
			held.px = to
			events.append(["posato", held.px.x, held.px.y - 10])
			held = null
		return
	for it in oggetti:
		if it.state == 0 and absi(p.px - it.px.x) <= USE_REACH and absi(p.py - it.px.y) <= 10:
			it.state = 1
			held = it
			held.px = Vector2i(p.px + 10 * p.facing, p.top() + 40)
			events.append(["preso", it.home.x, it.home.y - 10])
			return


func _person(q: Person, p: PlatformPlayer, dr: Drones) -> void:
	q.asked_t = q.asked_t + 1 if q.asked else 0
	if q.thanked:
		q.thanked_t += 1
		return
	var dx := absi(p.px - q.px.x)
	if dx > TALK_AGAIN:
		q.asked = false
	if dx > TALK_REACH or absi(p.py - q.px.y) > TALK_HEIGHT:
		return
	if served(q, dr):
		q.thanked = true
		for r: Variant in q.premio:
			opened.append(str(r))
		for it in ristori:
			if it.iid in opened:
				it.hidden = false
		changed = true
		_say(q.ringrazia, Vector2(q.px.x, q.px.y - 100))
		events.append(["grazie", q.px.x, q.px.y - 60])
	elif not q.asked and q.chiede != "":
		q.asked = true
		_say(q.chiede, Vector2(q.px.x, q.px.y - 100))
		events.append(["chiede", q.px.x, q.px.y - 60])


## Quello che serve alla Persona è fatto: un oggetto posato lì, o il drone con quell'iid rotto.
func served(q: Person, dr: Drones) -> bool:
	if q.serve == "":
		return true
	for it in oggetti:
		if it.per == q.serve and it.state == 2:
			return true
	return dr != null and dr.is_broken(q.serve)


func is_open(iid: String) -> bool:
	return iid in opened


## Le battute «persona» le dice la Persona più vicina; GIG, Tere e Totò parlano sopra GIG.
func _line_bubble(l: Line, p: PlatformPlayer) -> void:
	if l.chi == "persona":
		var best: Person = null
		for q in persone:
			if best == null or absi(q.px.x - l.px.x) < absi(best.px.x - l.px.x):
				best = q
		var at := Vector2(l.px.x, l.px.y - 30)
		if best != null and absi(best.px.x - l.px.x) <= 600 and absi(best.px.x - p.px) <= 400:
			at = Vector2(best.px.x, best.px.y - 100)
		_say(l.id, at)
	else:
		_say(l.id, Vector2.ZERO, true, "" if l.chi == "gig" else l.chi.to_upper())


func _say(id: String, at: Vector2, on_player: bool = false, tag: String = "") -> void:
	if id == "":
		return
	var text := SceneLines.find(lines_file, LINES_SCENE, id)
	if text == "":
		return
	var b := Bubble.new()
	b.lines = wrap_text(text, BUBBLE_W)
	b.at = at
	b.on_player = on_player
	b.tag = tag
	b.life = clampi(BUBBLE_MIN + text.length() * BUBBLE_PER_CHAR, BUBBLE_MIN, BUBBLE_MAX)
	var voice := SceneVoices.voice(lines_file, LINES_SCENE, id, text)
	if not voice.is_empty():
		b.life = maxi(b.life, int(voice["ticks"]) + 30)
		voices.append(voice["stream"])
	# Un fumetto nuovo dallo stesso punto prende il posto del vecchio.
	for i in range(bubbles.size() - 1, -1, -1):
		if bubbles[i].on_player == on_player and bubbles[i].at.distance_to(at) < 40.0:
			bubbles.remove_at(i)
	bubbles.append(b)


## Il testo a capo sulle parole, entro `w` px col font piccolo.
static func wrap_text(text: String, w: int) -> PackedStringArray:
	var out := PackedStringArray()
	var line := ""
	for word in text.split(" ", false):
		var t := word if line == "" else line + " " + word
		if line != "" and UiFont.text_width(t, 1, true) > w:
			out.append(line)
			line = word
		else:
			line = t
	if line != "":
		out.append(line)
	return out


func state_hash() -> Array:
	var h: Array = [held.iid if held != null else "", ",".join(opened)]
	for it in ristori:
		h.append(it.taken)
	for it in oggetti:
		h.append_array([it.state, it.px])
	for q in persone:
		h.append_array([q.asked, q.thanked])
	for l in battute:
		h.append(l.said)
	for f in firme:
		h.append(f.taken)
	if coffee_t > 0:
		h.append(coffee_t)
	return h


## Quante firme del livello sono prese.
func firme_prese() -> int:
	var n := 0
	for f in firme:
		if f.taken:
			n += 1
	return n


# ------------------------------------------------------------------ disegno

var _tag_sheet: SpriteSheet = null
var _tag_tried: bool = false


## Lo sprite delle tag REVENGE (assets/props/tag_revenge), o null se manca.
func tag_sheet() -> SpriteSheet:
	if not _tag_tried:
		_tag_tried = true
		if FileAccess.file_exists("res://assets/props/tag_revenge.json"):
			var s := SpriteSheet.get_sheet(&"tag_revenge", "props")
			if s.source == SpriteSheet.Source.REAL:
				_tag_sheet = s
	return _tag_sheet


func _tag_frame(s: SpriteSheet, anim: StringName) -> AnimFrame:
	return s.clip(anim).frames[0]


## Le firme sul muro, dietro a GIG: accese finché non le prende, poi grigie. Alla presa la tag accesa
## schiarisce e sfuma sopra quella grigia.
func draw_tags(v: CanvasItem, t: int, vis: Rect2) -> void:
	var s := tag_sheet()
	for f in firme:
		if not vis.grow(40).has_point(Vector2(f.px)):
			continue
		if s == null:
			var r := Rect2(f.rect())
			v.draw_rect(r, Color8(120, 120, 120) if f.taken else Color8(236, 96, 150))
			continue
		var on := _tag_frame(s, &"accesa")
		var at := Vector2(f.px)
		if f.taken:
			var off := _tag_frame(s, &"presa")
			v.draw_texture_rect_region(s.texture, Rect2(at - Vector2(off.anchor), off.rect.size), Rect2(off.rect))
			if f.flash > 0:
				var k := float(f.flash) / FIRMA_FLASH
				v.draw_texture_rect_region(s.texture, Rect2(at - Vector2(on.anchor), on.rect.size), Rect2(on.rect),
					Color(1.0 + k, 1.0 + k, 1.0 + k, k))
			continue
		# Accesa: un respiro lento, sfasato fra le tag, che la fa notare senza farla lampeggiare.
		var b := 1.0 + 0.12 * maxf(sin(t * 0.06 + f.px.x * 0.01), 0.0)
		v.draw_texture_rect_region(s.texture, Rect2(at - Vector2(on.anchor), on.rect.size), Rect2(on.rect), Color(b, b, b))


## Il contatore delle firme, in alto a destra sotto la barra, per un po' dopo ogni presa.
func draw_tags_hud(h: CanvasItem) -> void:
	if firme_hud <= 0 or firme.is_empty():
		return
	var a := minf(float(firme_hud) / 20.0, 1.0)
	var txt := "%d/%d" % [firme_prese(), firme.size()]
	var w := UiFont.text_width(txt)
	var x := View.W - 4 - w
	var s := tag_sheet()
	if s != null:
		var on := _tag_frame(s, &"accesa")
		h.draw_texture_rect_region(s.texture, Rect2(x - 4 - on.rect.size.x, 17, on.rect.size.x, on.rect.size.y), Rect2(on.rect), Color(1, 1, 1, a))
	UiFont.draw_text(h, Vector2(x, 20), txt, Color(C_PAPER, a))


# ------------------------------------------------------------------ disegno (greybox)

## Persone, oggetti e ristori, nel mondo. Quello che si usa pulsa; vicino c'è il triangolo del SU.
func draw(v: CanvasItem, t: int, vis: Rect2, p: PlatformPlayer) -> void:
	var pulse := 0.5 + 0.5 * sin(t * 0.12)
	for q in persone:
		if vis.grow(60).has_point(Vector2(q.px)) and person_sheet(q.id) == null:
			_draw_person(v, q, pulse)
	for it in ristori:
		if not it.hidden and not it.taken and vis.grow(30).has_point(Vector2(it.px)):
			_draw_ristoro(v, it, t)
	for it in oggetti:
		if vis.grow(30).has_point(Vector2(it.px)) and not in_hands(it):
			_draw_object(v, it, it.state == 0, pulse)
	# Lo scatto del caffè: due righe di vento dietro GIG che corre, e un filo di vapore che sale.
	if coffee_t > 0:
		var fade := minf(float(coffee_t) / 30.0, 1.0)
		if absi(p.vx) > 0:
			var back := -signi(p.vx)
			for i in 2:
				var len := 8.0 + float((t + i * 5) % 9)
				var x0 := float(p.left() if back < 0 else p.right()) + back * (3.0 + i * 4)
				v.draw_rect(Rect2(x0 if back > 0 else x0 - len, p.py - 18 - i * 14, len, 1), Color(C_PAPER, 0.45 * fade))
		var s := float(t % 40) / 40.0
		v.draw_rect(Rect2(p.px - 1 + roundf(sin(t * 0.2) * 2.0), p.top() - 4 - s * 10.0, 2, 2), Color(C_PAPER, 0.5 * (1.0 - s) * fade))
	# Dove va posato quello che GIG ha in mano.
	if held != null and _where.get(held.per) is Vector2i:
		var to: Vector2i = _where[held.per]
		v.draw_rect(Rect2(to.x - 12, to.y - 22, 24, 24), Color(C_CYAN, 0.25 + 0.5 * pulse), false, 2.0)
		_draw_up(v, Vector2(to.x, to.y - 30), pulse)
	# Il SU accanto a un oggetto da prendere.
	if held == null and p.state == PlatformPlayer.State.GROUND:
		for it in oggetti:
			if it.state == 0 and absi(p.px - it.px.x) <= USE_REACH and absi(p.py - it.px.y) <= 10:
				_draw_up(v, Vector2(it.px.x, it.px.y - 30), pulse)


# ------------------------------------------------------------------ sprite delle Persone

## Lo sprite vero di una Persona (assets/sprites/<id>/), o null: senza, resta il greybox.
func person_sheet(id: String) -> SpriteSheet:
	if not _sheets.has(id):
		var sh: SpriteSheet = null
		if id != "" and FileAccess.file_exists("res://assets/sprites/%s/%s.json" % [id, id]):
			sh = SpriteSheet.get_sheet(StringName(id))
			if sh != null and sh.source != SpriteSheet.Source.REAL:
				sh = null
		_sheets[id] = sh
	return _sheets[id]


## L'oggetto ce l'ha in mano la Persona che lo dà (i fiori della signora): non si disegna per terra.
func in_hands(it: Item) -> bool:
	if it.state != 0:
		return false
	for q in persone:
		if q.serve == it.per and not q.thanked and q.id == "signora" and person_sheet(q.id) != null:
			return true
	return false


## La posa della Persona al tick `t`, con GIG a `gig_x`: [foglio, animazione, tick dentro
## l'animazione, verso (1 a destra)], o [] se non ha lo sprite. Solo disegno, da quello che la logica
## sa già:
## - la signora tiene fiori e lumino; quando chiede li porge; quando GIG li prende (signora_dopo)
##   guarda su verso la quinta fila; quando ringrazia fruga nella borsa e porge i taralli;
## - il fruttivendolo è in ansia; quando ringrazia fa il «grazie», poi alza la botola della cantina
##   (il suo premio) e fa segno di venire.
func person_pose(q: Person, gig_x: int, t: int) -> Array:
	var face := 1 if gig_x >= q.px.x else -1
	match q.id:
		"signora":
			var prima := person_sheet("signora")
			var dopo := person_sheet("signora_dopo")
			if prima == null or dopo == null:
				return []
			if q.thanked:
				if q.thanked_t < dopo.clip(&"taralli").total_ticks():
					return [dopo, &"taralli", q.thanked_t, face]
				return [dopo, &"idle", t, face]
			for it in oggetti:
				if it.per == q.serve and it.state != 0:
					return [dopo, &"guarda_su", t, _toward(q, q.serve, face)]
			if q.asked:
				return [prima, &"porge", q.asked_t, face]
			return [prima, &"idle", t, face]
		"fruttivendolo":
			var sh := person_sheet("fruttivendolo")
			if sh == null:
				return []
			if not q.thanked:
				return [sh, &"idle", t, face]
			var k := q.thanked_t
			var thanks := sh.clip(&"sollievo").total_ticks()
			if k < thanks:
				return [sh, &"sollievo", k, face]
			# La botola e il «di qua» guardano la cantina.
			var hatch := _toward(q, "" if q.premio.is_empty() else str(q.premio[0]), face)
			k -= thanks
			if k < sh.clip(&"botola").total_ticks():
				return [sh, &"botola", k, hatch]
			return [sh, &"diqua", t, hatch]
	var own := person_sheet(q.id)
	return [] if own == null else [own, &"idle", t, face]


## Il verso dalla Persona verso la cosa `iid` del livello, o `fallback` se non si sa dov'è.
func _toward(q: Person, iid: String, fallback: int) -> int:
	var to: Variant = _where.get(iid)
	if not (to is Vector2i):
		return fallback
	return 1 if (to as Vector2i).x >= q.px.x else -1


## I droni che una Persona chiede di rompere e non ha ancora avuto: per il segno a portata di jab.
func wanted_drones() -> Array[String]:
	var out: Array[String] = []
	for q in persone:
		if not q.thanked and q.serve != "":
			out.append(q.serve)
	return out


## Il cancello `iid` è il premio del fruttivendolo, che alza la botola a mano: si disegna aperto solo
## da quando l'anta è su. Gli altri sì, appena aperti.
func lifted(iid: String) -> bool:
	for q in persone:
		if q.thanked and iid in q.premio and q.id == "fruttivendolo":
			var sh := person_sheet(q.id)
			if sh == null:
				return true
			var k := sh.clip(&"sollievo").total_ticks()
			var bot := sh.clip(&"botola")
			for i in mini(BOTOLA_UP_FRAME, bot.frames.size()):
				k += bot.frames[i].ticks
			return q.thanked_t >= k
	return true


## Il fotogramma di `c` al tick `k`: in giro se va in loop, fermo sull'ultimo se no.
static func clip_frame(c: AnimClip, k: int) -> AnimFrame:
	var total := maxi(c.total_ticks(), 1)
	k = posmod(k, total) if c.loop else clampi(k, 0, total - 1)
	for f in c.frames:
		k -= maxi(f.ticks, 1)
		if k < 0:
			return f
	return c.frames[c.frames.size() - 1]


## Le Persone con lo sprite vero: le disegna il nodo coi corpi, con la normal map e le luci, come GIG.
func draw_bodies(v: CanvasItem, t: int, vis: Rect2, p: PlatformPlayer) -> void:
	for q in persone:
		if not vis.grow(80).has_point(Vector2(q.px)):
			continue
		var pose := person_pose(q, p.px, t)
		if pose.is_empty():
			continue
		var sh: SpriteSheet = pose[0]
		var f := clip_frame(sh.clip(pose[1]), pose[2])
		v.draw_set_transform(Vector2(q.px), 0.0, Vector2(pose[3], 1))
		v.draw_texture_rect_region(sh.texture, Rect2(-Vector2(f.anchor), Vector2(f.rect.size)), Rect2(f.rect))
	v.draw_set_transform(Vector2.ZERO)


func _draw_up(v: CanvasItem, at: Vector2, pulse: float) -> void:
	var c := Color(C_CYAN, 0.6 + 0.4 * pulse)
	v.draw_colored_polygon(PackedVector2Array([at + Vector2(-5, 3), at + Vector2(5, 3), at + Vector2(0, -4)]), c)


func _draw_person(v: CanvasItem, q: Person, pulse: float) -> void:
	var x := float(q.px.x)
	var y := float(q.px.y)
	if not q.thanked:
		v.draw_rect(Rect2(x - 16, y - 92, 32, 92), Color(C_CYAN, 0.08 + 0.12 * pulse))
	v.draw_rect(Rect2(x - 9, y - 60, 18, 60), C_PERSON_DARK)
	v.draw_rect(Rect2(x - 11, y - 74, 22, 34), C_PERSON)
	v.draw_rect(Rect2(x - 7, y - 88, 14, 14), C_SKIN)
	v.draw_rect(Rect2(x - 7, y - 90, 14, 4), C_PERSON_DARK)


func _draw_object(v: CanvasItem, it: Item, glow: bool, pulse: float) -> void:
	var x := float(it.px.x)
	var y := float(it.px.y)
	if glow:
		v.draw_rect(Rect2(x - 12, y - 22, 24, 22), Color(C_CYAN, 0.1 + 0.15 * pulse))
	match it.tipo:
		"fiori":
			for i in 3:
				v.draw_rect(Rect2(x - 4 + i * 3, y - 12, 1, 12), C_GREEN)
			v.draw_rect(Rect2(x - 6, y - 17, 4, 4), Color8(220, 60, 70))
			v.draw_rect(Rect2(x - 1, y - 19, 4, 4), Color8(240, 200, 70))
			v.draw_rect(Rect2(x + 3, y - 16, 4, 4), Color8(230, 120, 170))
			v.draw_rect(Rect2(x - 4, y - 7, 9, 3), C_PAPER)
		_:
			v.draw_rect(Rect2(x - 4, y - 10, 8, 10), C_GOLD)


func _draw_ristoro(v: CanvasItem, it: Item, t: int) -> void:
	var x := float(it.px.x)
	var y := float(it.px.y) - roundf(1.5 + 1.5 * sin(t * 0.08))
	match it.tipo:
		"taralli":
			v.draw_rect(Rect2(x - 9, y - 8, 18, 8), C_WOOD)
			for i in 3:
				v.draw_arc(Vector2(x - 5 + i * 5, y - 11), 3.0, 0.0, TAU, 10, C_GOLD, 2.0)
		"caffe":
			v.draw_rect(Rect2(x - 5, y - 10, 10, 9), C_PAPER)
			v.draw_rect(Rect2(x - 4, y - 9, 8, 2), C_BROWN)
			v.draw_arc(Vector2(x + 6, y - 6), 2.5, -PI / 2, PI / 2, 6, C_PAPER, 1.5)
			v.draw_rect(Rect2(x - 7, y - 1, 14, 1), C_PAPER)
		"panzerotto":
			v.draw_arc(Vector2(x, y - 2), 8.0, PI, TAU, 12, C_GOLD, 6.0)
			v.draw_rect(Rect2(x - 8, y - 2, 16, 2), C_BROWN)
		"scarcella":
			v.draw_rect(Rect2(x - 7, y - 14, 14, 14), C_GOLD)
			v.draw_rect(Rect2(x - 3, y - 10, 6, 6), C_PAPER)
			v.draw_rect(Rect2(x - 2, y - 9, 4, 4), Color8(220, 60, 70))
		"bombola":
			v.draw_rect(Rect2(x - 4, y - 16, 8, 16), C_CYAN)
			v.draw_rect(Rect2(x - 2, y - 19, 4, 3), C_PAPER)
		_:
			v.draw_rect(Rect2(x - 5, y - 10, 10, 10), C_GOLD)


## I fumetti, sopra tutto il resto del mondo: riquadro chiaro col bordo scuro, la punta verso chi
## parla, il testo su più righe. Restano dentro lo schermo.
func draw_bubbles(v: CanvasItem, vis: Rect2, p: PlatformPlayer) -> void:
	var lh := 11.0
	for b in bubbles:
		var at := Vector2(p.px, p.top() - 8) if b.on_player else b.at
		var lines := b.lines
		var w := 0
		for l in lines:
			w = maxi(w, UiFont.text_width(l, 1, true))
		if b.tag != "":
			w = maxi(w, UiFont.text_width(b.tag))
		var rows := lines.size() + (1 if b.tag != "" else 0)
		var a := minf(1.0, minf(b.t / 8.0, (b.life - b.t) / 12.0))
		var bw := float(w + 12)
		var bh := rows * lh + 6.0
		var x := clampf(roundf(at.x - bw / 2.0), vis.position.x + 4.0, vis.end.x - 4.0 - bw)
		var y := maxf(vis.position.y + 20.0, roundf(at.y - bh - 8.0 + (1.0 - a) * 4.0))
		var r := Rect2(x, y, bw, bh)
		v.draw_rect(r.grow(1.0), Color(C_INK, a))
		v.draw_rect(r, Color(C_PAPER, 0.95 * a))
		var tip := clampf(at.x, r.position.x + 6.0, r.end.x - 6.0)
		v.draw_colored_polygon(PackedVector2Array([Vector2(tip - 4.0, r.end.y + 1.0), Vector2(tip + 4.0, r.end.y + 1.0),
			Vector2(tip, r.end.y + 7.0)]), Color(C_INK, a))
		var ty := r.position.y + 3.0
		if b.tag != "":
			UiFont.draw_text(v, Vector2(r.position.x + 6.0, ty), b.tag, Color(C_PERSON_DARK, a))
			ty += lh
		for l in lines:
			UiFont.draw_text(v, Vector2(r.position.x + 6.0, ty), l, Color(C_TEXT, a), 1, 0, Color(0, 0, 0, 0),
				Color(0, 0, 0, 0), true)
			ty += lh
