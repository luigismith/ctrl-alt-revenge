class_name InputFrame
extends RefCounted
## Gli ingressi del giocatore in un tick: i tasti tenuti e quelli appena premuti.
##
## Il gameplay legge solo questa struttura, mai il singleton Input: così i replay
## e il pilota automatico producono esattamente gli stessi tick del gioco dal vivo.

const LEFT := 1
const RIGHT := 2
const UP := 4
const DOWN := 8
const ATTACK := 16
const JUMP := 32

## Lettere usate nei file di replay, nello stesso ordine dei bit.
const LETTERS := "LRUDAJ"

var held: int = 0
var pressed: int = 0


func _init(held_bits: int = 0, pressed_bits: int = 0) -> void:
	# Un tasto appena premuto conta anche come tenuto in quel tick.
	held = held_bits | pressed_bits
	pressed = pressed_bits


func is_held(bit: int) -> bool:
	return (held & bit) != 0


func was_pressed(bit: int) -> bool:
	return (pressed & bit) != 0


## -1 sinistra, 0 nessuna, 1 destra (le due direzioni insieme si annullano).
func axis_x() -> int:
	return int(is_held(RIGHT)) - int(is_held(LEFT))


## -1 in alto (lontano), 1 in basso (vicino).
func axis_y() -> int:
	return int(is_held(DOWN)) - int(is_held(UP))


static func bits_to_letters(bits: int) -> String:
	var s := ""
	for i in LETTERS.length():
		if bits & (1 << i):
			s += LETTERS[i]
	return s


static func letters_to_bits(s: String) -> int:
	var bits := 0
	for c in s:
		var i := LETTERS.find(c)
		if i >= 0:
			bits |= 1 << i
	return bits
