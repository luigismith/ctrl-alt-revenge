class_name Registri
extends RefCounted
## Le basi di ricarica di SIDERA che tengono i registri delle braccia (storia, decisione 100; la scheda
## è docs/lore/registro-base.md). Vengono dalle entità `Registro` di LDtk (`atto`, `numero`, `id_testo`;
## il punto è il piede della base, al centro).
##
## - **Nascosta:** è un oggetto fra gli altri, con la spia spenta. Con la Vista ha il contorno cyan che
##   pulsa e ne escono onde corte di segnale, disegnate sopra al velo (passano anche i muri finti).
## - **La copia:** SU accanto, coi piedi alla sua altezza e il braccio vivo. GIG si china e appoggia il
##   polso nella culla per un secondo (COPY_TICKS): il clic, la culla cyan, il lampo, le righe di dati che
##   salgono, la spia dal rosso al cyan. Il gioco non si ferma; GIG sta fermo finché copia.
## - **Letta:** spia cyan fissa e fioca, niente contorno. Resta letta per tutta la sessione (Game.registri),
##   anche quando il capitolo si rigioca.
##
## Lo stato della simulazione (copia, letture) entra nell'impronta; il disegno no.

## I registri di tutto il gioco: cinque per atto (gameplay, «Segreti»).
const TOTALE := 15
## Entro questa distanza orizzontale SU funziona (come alla lapide).
const REACH := 40
const COPY_TICKS := 60
## I momenti della copia: la culla si accende, il lampo, la fine.
const GLOW_AT := 6
const FLASH_AT := 34
## Tere al lampo: «Questo lo teniamo.» (battuta in_gioco, con la voce).
const LINE_TERE := "tere_registro"
## Quanto resta la scritta REGISTRO COPIATO.
const TEXT_TICKS := 150
## Quanto sta sopra il piede della base.
const TEXT_UP := 72
## La base: 36×24 cm, cioè 22×14 px a 60 px/m (scheda, «Misure»).
const SIZE := Vector2i(22, 14)
## Gli sprite della base (car-grafica, registro.py): nascosta, al colmo della copia, letta, e il contorno
## bianco di 1 px (24×16) che la Vista tinge e fa pulsare.
const SPRITE_DIR := "res://assets/sprites/registro/"
## La spia, nello sprite: rossa per un istante durante la copia, prima del cyan.
const LED := Rect2i(18, 7, 2, 1)

const C_LED_RED := Color8(255, 64, 56)
const C_CYAN := Color8(64, 232, 255)


class Base:
	var iid: String = ""
	var id: String = ""
	var atto: int = 0
	var numero: int = 0
	## Il piede della base, al centro.
	var px: Vector2i = Vector2i.ZERO
	var read: bool = false


var basi: Array[Base] = []
## La base in copia (indice in `basi`), o -1.
var copying: int = -1
var copy_t: int = 0
## I tick che restano della scritta, e la base a cui sta sopra.
var text_t: int = 0
var text_at: int = -1
## Gli eventi del tick, per i suoni e le scintille della stanza.
var events: PackedStringArray = []

var _tex_hidden: Texture2D = null
var _tex_copy: Texture2D = null
var _tex_read: Texture2D = null
var _tex_outline: Texture2D = null


func setup(entities: Array) -> void:
	basi.clear()
	for e: Dictionary in entities:
		if String(e["tipo"]) != "Registro":
			continue
		var b := Base.new()
		b.iid = String(e.get("iid", ""))
		b.id = str(e["campi"].get("id_testo", ""))
		b.atto = int(e["campi"].get("atto", 0))
		b.numero = int(e["campi"].get("numero", 0))
		b.px = e["px"]
		basi.append(b)
	if not basi.is_empty() and _tex_hidden == null:
		_tex_hidden = load(SPRITE_DIR + "registro.png")
		_tex_copy = load(SPRITE_DIR + "registro_copia.png")
		_tex_read = load(SPRITE_DIR + "registro_letta.png")
		_tex_outline = load(SPRITE_DIR + "registro_contorno.png")
	reset()


## Alla ripartenza: la copia a metà si perde, le basi lette restano lette.
func reset() -> void:
	copying = -1
	copy_t = 0
	text_t = 0
	text_at = -1
	events.clear()
	for b in basi:
		b.read = Game.registri.has(b.id)


func is_empty() -> bool:
	return basi.is_empty()


## La base non ancora letta a portata di SU, o -1.
func near(p: PlatformPlayer) -> int:
	if p.state != PlatformPlayer.State.GROUND:
		return -1
	for i in basi.size():
		var b := basi[i]
		if not b.read and absi(p.px - b.px.x) <= REACH and p.py == b.px.y:
			return i
	return -1


## GIG sta copiando: i comandi sono fermi.
func busy() -> bool:
	return copying >= 0


## Quanti registri sono stati copiati in tutto.
static func count() -> int:
	return Game.registri.size()


## Un tick. `armed`: il braccio è vivo (nel prologo, dopo il riavvio). Vero se ha preso i comandi.
func step(frame: InputFrame, p: PlatformPlayer, armed: bool) -> bool:
	events.clear()
	if text_t > 0:
		text_t -= 1
	if copying >= 0:
		copy_t += 1
		if copy_t == GLOW_AT:
			events.append("registro_ronzio")
		elif copy_t == FLASH_AT:
			events.append("registro_lampo")
		elif copy_t >= COPY_TICKS:
			var b := basi[copying]
			b.read = true
			Game.registri[b.id] = true
			text_at = copying
			text_t = TEXT_TICKS
			copying = -1
			copy_t = 0
			events.append("registro_copiato")
			return false
		return true
	if not armed or not frame.was_pressed(InputFrame.UP):
		return false
	var i := near(p)
	if i < 0:
		return false
	copying = i
	copy_t = 0
	p.facing = 1 if basi[i].px.x >= p.px else -1
	events.append("registro_clic")
	return true


func state_hash() -> Array:
	var h: Array = [copying, copy_t, text_t, text_at]
	for b in basi:
		h.append(b.read)
	return h


# ------------------------------------------------------------------ disegno

## Le basi, nel mondo (dietro a GIG): il corpo, la culla, la spia e, durante la copia, la culla cyan.
func draw_bodies(v: CanvasItem, view: Rect2) -> void:
	for i in basi.size():
		var b := basi[i]
		if not view.grow(40).has_point(Vector2(b.px)):
			continue
		_draw_base(v, b, i == copying)


func _draw_base(v: CanvasItem, b: Base, live: bool) -> void:
	var at := Vector2(b.px.x - SIZE.x / 2, b.px.y - SIZE.y)
	if not live:
		v.draw_texture(_tex_read if b.read else _tex_hidden, at)
		return
	# La copia: dalla base spenta la sella e i contatti si accendono di cyan (lo sprite del colmo, che
	# entra piano e pulsa), la spia è rossa fino al lampo e poi cyan.
	v.draw_texture(_tex_hidden, at)
	if copy_t >= GLOW_AT:
		var k := clampf(float(copy_t - GLOW_AT) / 10.0, 0.0, 1.0)
		var pulse := 1.0 if copy_t >= FLASH_AT else 0.75 + 0.25 * sin(copy_t * 0.6)
		v.draw_texture(_tex_copy, at, Color(1, 1, 1, k * pulse))
	if copy_t < FLASH_AT:
		v.draw_rect(Rect2(at + Vector2(LED.position), LED.size), C_LED_RED)


## Sopra al velo della Vista: il contorno che pulsa e le onde di segnale delle basi ancora da leggere
## (`k` è quanto è accesa la Vista, da 0 a 1), le righe di dati della copia e la scritta.
func draw_overlay(v: CanvasItem, view: Rect2, k: float, frame: int, arm: Vector2) -> void:
	for i in basi.size():
		var b := basi[i]
		if not view.grow(60).has_point(Vector2(b.px)):
			continue
		var x := b.px.x - SIZE.x / 2
		var y := b.px.y - SIZE.y
		if k > 0.0 and not b.read and i != copying:
			var c := C_CYAN
			c.a = k * (0.6 + 0.4 * sin(frame * 0.09))
			v.draw_texture(_tex_outline, Vector2(x - 1, y - 1), c)
			# Le onde: tre anelli che si allargano dalla culla e si spengono.
			for w in 3:
				var t := float((frame + w * 30) % 90) / 90.0
				var oc := C_CYAN
				oc.a = k * (1.0 - t) * 0.7
				v.draw_arc(Vector2(b.px.x, y + 2), 8.0 + t * 34.0, PI * 1.08, PI * 1.92, 14, oc, 1.0)
		if i == copying and copy_t >= GLOW_AT + 8:
			# Le righe di dati: trattini che salgono dalla culla al polso.
			var from := Vector2(b.px.x, y)
			for d in 3:
				var t := fmod(float(copy_t + d * 7) / 18.0, 1.0)
				var q := from.lerp(arm, t)
				var dc := C_CYAN
				dc.a = 1.0 - t * 0.6
				v.draw_rect(Rect2(roundf(q.x) - 2, roundf(q.y), 4, 1), dc)
		if i == copying and absi(copy_t - FLASH_AT) <= 3:
			# Il lampo, piccolo come quello della Spinta.
			var fc := Color(0.85, 1.0, 1.0, 1.0 - absf(copy_t - FLASH_AT) / 4.0)
			v.draw_circle(Vector2(b.px.x, y + 1), 6.0 - absf(copy_t - FLASH_AT), fc)
	if text_t > 0 and text_at >= 0 and text_at < basi.size():
		var b := basi[text_at]
		var c := C_CYAN
		c.a = clampf(text_t / 30.0, 0.0, 1.0)
		var s := "REGISTRO COPIATO · %d/%d" % [count(), TOTALE]
		# Sopra al cartello di B4, che sta poco sopra la base.
		UiFont.draw_text(v, Vector2(b.px.x, b.px.y - TEXT_UP), s, c, 1, 1)
