class_name FrameAnim
extends RefCounted
## Riproduce un'animazione un tick alla volta.
##
## Tempi esatti: play() nel tick P mostra il fotogramma 0 già nel tick P; un fotogramma
## con ticks = n resta visibile per n tick; un'animazione non in loop di T tick totali
## diventa `finished` nel tick P + T (dopo T chiamate ad advance()) e resta sull'ultimo
## fotogramma. Gli eventi e il dx di un fotogramma scattano nel tick in cui inizia.
## Un fotogramma con il tag "hold" resta fermo finché il codice non chiama release_hold().

var sheet: SpriteSheet
var clip: AnimClip
var name: StringName = &""
var index: int = 0
## Tick già trascorsi nel fotogramma corrente (0 nel suo primo tick).
var frame_tick: int = 0
## Tick trascorsi dall'inizio dell'animazione.
var elapsed: int = 0
var finished: bool = false

var _events: PackedStringArray = []
var _dx: int = 0


func _init(s: SpriteSheet = null) -> void:
	sheet = s


## Avvia l'animazione `anim_name` dello sheet (o `c` se data) dal primo fotogramma.
func play(anim_name: StringName, c: AnimClip = null) -> void:
	clip = c if c != null else sheet.clip(anim_name)
	name = anim_name
	index = 0
	frame_tick = 0
	elapsed = 0
	finished = false
	_enter_frame()


## Come play(), ma non fa nulla se questa animazione è già in corso.
func ensure(anim_name: StringName) -> void:
	if name != anim_name or clip == null:
		play(anim_name)


func advance() -> void:
	if clip == null or clip.frames.is_empty():
		return
	elapsed += 1
	var f := clip.frames[index]
	if f.has_tag(AnimFrame.TAG_HOLD):
		frame_tick = mini(frame_tick + 1, f.ticks)
		return
	frame_tick += 1
	if frame_tick < f.ticks:
		return
	if index + 1 < clip.frames.size():
		index += 1
		frame_tick = 0
		_enter_frame()
	elif clip.loop:
		index = 0
		frame_tick = 0
		_enter_frame()
	else:
		frame_tick = f.ticks
		finished = true


## Lascia proseguire un fotogramma "hold".
func release_hold() -> void:
	if clip == null:
		return
	if index + 1 < clip.frames.size():
		index += 1
		frame_tick = 0
		_enter_frame()
	else:
		finished = true


func is_holding() -> bool:
	return clip != null and not clip.frames.is_empty() and clip.frames[index].has_tag(AnimFrame.TAG_HOLD)


## Mostra il fotogramma i senza far scattare eventi (vittime delle prese).
func show_frame(anim_name: StringName, i: int) -> void:
	if name != anim_name or clip == null:
		clip = sheet.clip(anim_name)
		name = anim_name
	index = clampi(i, 0, clip.frames.size() - 1)
	frame_tick = 0
	finished = false


func frame() -> AnimFrame:
	return clip.frames[index]


func has_tag(tag: int) -> bool:
	return clip != null and clip.frames[index].has_tag(tag)


func is_last_frame() -> bool:
	return clip != null and index == clip.frames.size() - 1


## Eventi scattati dall'ultima chiamata (play o advance).
func take_events() -> PackedStringArray:
	var e := _events
	_events = PackedStringArray()
	return e


## Spostamento in avanti accumulato dall'ultima chiamata.
func take_dx() -> int:
	var d := _dx
	_dx = 0
	return d


func _enter_frame() -> void:
	var f := clip.frames[index]
	_events.append_array(f.events)
	_dx += f.dx
