extends Node
## Ambienti in loop (autoload "Ambience"): vento, pioggia, gocce, ronzii, i passi lontani dei rider.
##
## Interfaccia usata dal gameplay:
##   Ambience.play(strati, fade_s = 1.5)   strati = {nome: dB}, per esempio {&"amb_cimitero": 0.0,
##                                         &"amb_pioggia_prime": -2.0}. Gli strati che c'erano e non ci
##                                         sono più sfumano e si fermano; quelli nuovi entrano in
##                                         dissolvenza; quelli che restano non ripartono, cambia solo
##                                         il volume. {} = silenzio.
##   Ambience.stop(fade_s = 1.5)           come play({}).
##   Ambience.duck(on)                     abbassa tutto di DUCK_DB (scene, conto alla rovescia).
##   Ambience.silence()                    ferma tutto e ignora le richieste dopo (chiusura del gioco).
##   Ambience.active()                     {nome: dB} degli strati accesi (per i test).
##   Ambience.has_layer(nome)              il file c'è.
##
## Dettagli:
## - I file: res://assets/sfx/amb/<nome>.ogg, se no res://assets/sfx/<nome>.wav (i loop della Vedetta e
##   dei rider). Il loop sta nell'import (ogg: loop=true; wav: loop_mode=2). Se un file manca, lo strato
##   non suona e c'è un avviso una volta sola.
## - Il livello degli strati è già nei file (car-musica, `effetti-nel-gioco.md` §2): il bus "AMB" ha
##   un volume suo, BUS_DB, e manda a "SFX", così un'opzione del volume degli effetti vale anche qui.
##   Il bus va creato dopo "SFX": in Godot un bus manda solo a bus con indice più basso.
## - Non tocca la simulazione: niente numeri casuali, niente stato che entra nell'hash.

const BUS := &"AMB"
## Gli ambienti sono a -28/-32 LUFS nei file, pensati per una musica a -16; nel gioco la musica è a
## circa -26 (bus Music -6 e trim): -10 dB tengono lo stesso rapporto.
const BUS_DB := -10.0
const SEND := &"SFX"
const DIRS: Array[String] = ["res://assets/sfx/amb/%s.ogg", "res://assets/sfx/%s.wav"]
const MIN_AMP := 0.0001
const DUCK_DB := -10.0
const DUCK_FADE_S := 0.25

var _silenced := false
var _streams: Dictionary = {}     # StringName -> AudioStream (null se manca)
var _on: Dictionary = {}          # StringName -> AudioStreamPlayer degli strati accesi
var _db: Dictionary = {}          # StringName -> dB chiesti per lo strato acceso
var _amp: Dictionary = {}         # AudioStreamPlayer -> ampiezza della dissolvenza (0..1)
var _gain: Dictionary = {}        # AudioStreamPlayer -> dB dello strato
var _fades: Dictionary = {}       # AudioStreamPlayer -> Tween della dissolvenza
var _gain_tweens: Dictionary = {}  # AudioStreamPlayer -> Tween del volume
var _free: Array[AudioStreamPlayer] = []
var _duck_db := 0.0
var _duck_tween: Tween
var _warned: Dictionary = {}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_ensure_bus()


# ------------------------------------------------------------------ interfaccia

func play(layers: Dictionary, fade_s: float = 1.5) -> void:
	if _silenced:
		return
	_ensure_bus()
	for key: StringName in _on.keys():
		if not layers.has(key) and not layers.has(String(key)):
			_release(key, fade_s)
	for k: Variant in layers:
		var key := StringName(str(k))
		var db := float(layers[k])
		if _on.has(key):
			var p: AudioStreamPlayer = _on[key]
			_db[key] = db
			_tween_gain(p, db, fade_s)
			if float(_amp[p]) < 1.0:
				_fade(p, 1.0, fade_s, false)
			continue
		var stream := _stream_for(key)
		if stream == null:
			continue
		var p := _take_player()
		p.stream = stream
		_tween_gain(p, db, 0.0)
		_set_amp(0.0 if fade_s > 0.0 else 1.0, p)
		p.play()
		_fade(p, 1.0, fade_s, false)
		_on[key] = p
		_db[key] = db


func stop(fade_s: float = 1.5) -> void:
	play({}, fade_s)


func duck(on: bool) -> void:
	if _duck_tween != null and _duck_tween.is_valid():
		_duck_tween.kill()
	_duck_tween = create_tween()
	_duck_tween.tween_method(_set_duck, _duck_db, DUCK_DB if on else 0.0, DUCK_FADE_S)


func silence() -> void:
	_silenced = true
	if _duck_tween != null and _duck_tween.is_valid():
		_duck_tween.kill()
	for p: Node in get_children():
		if p is AudioStreamPlayer:
			_kill_fade(p)
			(p as AudioStreamPlayer).stop()
			(p as AudioStreamPlayer).stream = null
	_on.clear()
	_db.clear()


func active() -> Dictionary:
	return _db.duplicate()


func has_layer(layer: StringName) -> bool:
	return _path_for(layer) != ""


# Come in Music e Sfx: l'AudioServer libera i playback solo nei cicli di mix successivi.
func _exit_tree() -> void:
	for p: Node in get_children():
		if p is AudioStreamPlayer:
			(p as AudioStreamPlayer).stop()
	var deadline := Time.get_ticks_msec() + 200
	var mixes := 0
	var last := AudioServer.get_time_since_last_mix()
	while mixes < 3 and Time.get_ticks_msec() < deadline:
		OS.delay_usec(2000)
		var now := AudioServer.get_time_since_last_mix()
		if now < last:
			mixes += 1
		last = now


# ------------------------------------------------------------------ interni

func _path_for(layer: StringName) -> String:
	for pattern in DIRS:
		var path := pattern % String(layer)
		if ResourceLoader.exists(path):
			return path
	return ""


func _stream_for(layer: StringName) -> AudioStream:
	if _streams.has(layer):
		return _streams[layer]
	var path := _path_for(layer)
	var stream: AudioStream = load(path) as AudioStream if path != "" else null
	if stream == null and not _warned.has(layer):
		_warned[layer] = true
		push_warning("Ambience: manca lo strato %s" % layer)
	_streams[layer] = stream
	return stream


func _take_player() -> AudioStreamPlayer:
	while not _free.is_empty():
		var p: AudioStreamPlayer = _free.pop_back()
		if not p.playing:
			return p
	var q := AudioStreamPlayer.new()
	q.name = "Strato%d" % get_child_count()
	q.bus = BUS
	q.playback_type = AudioServer.PLAYBACK_TYPE_STREAM
	add_child(q)
	_amp[q] = 0.0
	_gain[q] = 0.0
	return q


func _release(key: StringName, fade_s: float) -> void:
	var p: AudioStreamPlayer = _on[key]
	_on.erase(key)
	_db.erase(key)
	_fade(p, 0.0, fade_s, true)


func _fade(p: AudioStreamPlayer, target: float, secs: float, stop_after: bool) -> void:
	_kill_fade(p)
	if secs <= 0.0 or not p.playing:
		_set_amp(target, p)
		if stop_after and target <= 0.0:
			_park(p)
		return
	var tw := create_tween()
	tw.tween_method(_set_amp.bind(p), float(_amp[p]), target, secs)
	if stop_after and target <= 0.0:
		tw.tween_callback(_park.bind(p))
	_fades[p] = tw


func _park(p: AudioStreamPlayer) -> void:
	p.stop()
	p.stream = null
	if not _free.has(p):
		_free.append(p)


func _kill_fade(p: AudioStreamPlayer) -> void:
	if _fades.has(p) and (_fades[p] as Tween).is_valid():
		(_fades[p] as Tween).kill()
	_fades.erase(p)


func _tween_gain(p: AudioStreamPlayer, db: float, secs: float) -> void:
	if _gain_tweens.has(p) and (_gain_tweens[p] as Tween).is_valid():
		(_gain_tweens[p] as Tween).kill()
	_gain_tweens.erase(p)
	if is_equal_approx(float(_gain[p]), db) or secs <= 0.0:
		_set_gain(db, p)
		return
	var tw := create_tween()
	tw.tween_method(_set_gain.bind(p), float(_gain[p]), db, secs)
	_gain_tweens[p] = tw


func _set_gain(value_db: float, p: AudioStreamPlayer) -> void:
	_gain[p] = value_db
	_apply_volume(p)


func _set_amp(value: float, p: AudioStreamPlayer) -> void:
	_amp[p] = clampf(value, 0.0, 1.0)
	_apply_volume(p)


func _set_duck(value_db: float) -> void:
	_duck_db = value_db
	for p: AudioStreamPlayer in _amp:
		_apply_volume(p)


func _apply_volume(p: AudioStreamPlayer) -> void:
	p.volume_db = float(_gain[p]) + linear_to_db(maxf(float(_amp[p]), MIN_AMP)) + _duck_db


func _ensure_bus() -> void:
	if AudioServer.get_bus_index(BUS) != -1:
		return
	AudioServer.add_bus()
	var idx := AudioServer.bus_count - 1
	AudioServer.set_bus_name(idx, BUS)
	AudioServer.set_bus_volume_db(idx, BUS_DB)
	AudioServer.set_bus_send(idx, SEND if AudioServer.get_bus_index(SEND) != -1 else &"Master")
