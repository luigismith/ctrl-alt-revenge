class_name AnimFrame
extends RefCounted
## Un fotogramma di un'animazione (formato §4 della specifica).
## Box [x, y, w, h] relativi all'ancora, personaggio rivolto a destra, y negativo = sopra il suolo.

const TAG_ACTIVE := 1
const TAG_CANCEL := 2
const TAG_INVULN := 4
const TAG_ARMOR := 8
const TAG_HOLD := 16
const TAG_AIR := 32
## La luce del fotogramma, per gli aloni dei droni: in ronda, in avviso, spenta.
const TAG_LIGHT_PATROL := 64
const TAG_LIGHT_ALERT := 128
const TAG_LIGHT_OFF := 256

const TAG_NAMES: Dictionary[String, int] = {
	"active": TAG_ACTIVE,
	"cancel": TAG_CANCEL,
	"invuln": TAG_INVULN,
	"armor": TAG_ARMOR,
	"hold": TAG_HOLD,
	"air": TAG_AIR,
	"ronda": TAG_LIGHT_PATROL,
	"avviso": TAG_LIGHT_ALERT,
	"spento": TAG_LIGHT_OFF,
}

var rect: Rect2i = Rect2i()
var anchor: Vector2i = Vector2i.ZERO
var ticks: int = 1
var hurt: Array[Rect2i] = []
var hit: Array[Rect2i] = []
var events: PackedStringArray = []
var tags: int = 0
var dx: int = 0
## Mosse a coppie: per id di nemico, [dx, dy, animazione, fotogramma] della vittima.
var victim: Dictionary = {}
var victim_behind: bool = false
## Punti del fotogramma relativi all'ancora (§4): "fist_l", "fist_r", "foot_l", "foot_r", "head", "grip".
## Servono agli effetti agganciati (fx:<nome>@<punto>) e, nelle mosse platform, ad allineare le mani.
var points: Dictionary[String, Vector2i] = {}
## Spostamento verticale in px all'inizio del fotogramma (root motion, positivo = in alto), opzionale.
var dy: int = 0
## Di quanti px si è alzato il disegno perché la suola tocchi la collisione (data/sprites/suole.json):
## l'ancora e i punti lo comprendono già, hurt e hit no. Solo per i controlli.
var lift: int = 0


func has_tag(tag: int) -> bool:
	return (tags & tag) != 0


func copy() -> AnimFrame:
	var f := AnimFrame.new()
	f.rect = rect
	f.anchor = anchor
	f.ticks = ticks
	f.hurt = hurt.duplicate()
	f.hit = hit.duplicate()
	f.events = events.duplicate()
	f.tags = tags
	f.dx = dx
	f.victim = victim.duplicate(true)
	f.victim_behind = victim_behind
	f.points = points.duplicate()
	f.dy = dy
	f.lift = lift
	return f


## Voce della vittima per questo tipo di nemico: [dx, dy, anim, frame], oppure [] se manca.
func victim_entry(enemy_id: StringName) -> Array:
	var v: Variant = victim.get(String(enemy_id), null)
	if v is Array and (v as Array).size() >= 2:
		return v
	return []


static func tags_from_names(names: Array) -> int:
	var t := 0
	for n: Variant in names:
		t |= TAG_NAMES.get(str(n), 0)
	return t
