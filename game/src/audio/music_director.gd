extends Node
## Musica (autoload "Music").
##
## La musica non è nel repo. I brani si cercano, in quest'ordine, in:
##   1. res://assets_private/music/
##   2. <cartella dell'eseguibile>/music/
##   3. %USERPROFILE%/ctrlaltrevenge-lab/music/ (solo durante lo sviluppo, non nelle build esportate)
## dove un file music.json descrive ogni brano (id, file, loop, BPM, strati).
## Se non trova nulla resta muto, senza errori.
##
## Interfaccia usata dal gameplay (non cambiarla senza aggiornare docs/specifica-slice.md):
##   Music.play(track_id, fade_s = 0.5)        brano in loop: "title", "stage1"
##   Music.stop(fade_s = 0.5)
##   Music.set_layer(layer_id, on)             strato in più, es. "arena" durante l'arena
##   Music.play_jingle(track_id)               non in loop, es. "clear"; poi silenzio
##   Music.duck(on)                            abbassa la musica (pausa, schermate)
##   Music.has_track(track_id)                 il brano c'è (per esempio la musica di una scena)
##   Music.current_track()                     il brano in loop che suona adesso, o &""
## Il player gira con PROCESS_MODE_ALWAYS: la pausa del gioco non ferma la musica.
##
## Dettagli:
## - Vince la prima cartella con un music.json valido e almeno un brano il cui file esiste.
## - music.json: {"format": 1, "tracks": [{"id", "file", "loop", "loop_start", "loop_end",
##   "loop_start_sample", "loop_end_sample", "sample_rate", "bpm", "bar_beats", "gain_db",
##   "layers": [{"id", "file", "gain_db"}], "placeholder", "source"}, ...]}; i tempi sono in
##   secondi, i campioni (se ci sono) sono esatti. Lo scrive tools/audio/prepare_music.py.
## - OGG con AudioStreamOggVorbis.load_from_file, WAV con AudioStreamWAV.load_from_file
##   (in res:// vale il file importato). Gli OGG sono tagliati alla fine del loop e ripartono
##   da loop_offset = (inizio + 0,5 campioni): Godot tronca il tempo in campioni.
## - Un brano con strati diventa un AudioStreamSynchronized: base sempre a 0 dB, strati muti
##   finché set_layer() non li accende (dissolvenza di LAYER_FADE_S secondi).
##   set_layer accetta l'id dello strato ("arena") o quello lungo ("stage1_arena").
##   play() di un brano diverso spegne gli strati; play() del brano già in corso non lo fa
##   ripartire ma spegne i suoi strati con la dissolvenza.
## - play() fa una dissolvenza incrociata fra due player; play_jingle() sfuma la musica in
##   JINGLE_FADE_S e suona il jingle una volta sola su un terzo player.
## - duck() abbassa tutto di DUCK_DB in DUCK_FADE_S secondi; vale anche per i brani successivi.
## - silence() ferma tutto subito e ignora le richieste successive: serve prima di chiudere il
##   gioco (Game.quit_clean), perché l'AudioServer libera i playback solo nei cicli di mix
##   successivi (vedi sfx.gd).

const MANIFEST := "music.json"
const BUS := &"Music"
const SILENT_DB := -80.0
const MIN_AMP := 0.0001
const LAYER_FADE_S := 0.8
const JINGLE_FADE_S := 0.3
const DUCK_DB := -10.0
const DUCK_FADE_S := 0.25

var music_dir: String = ""           ## cartella trovata ("" = nessuna musica)
var _silenced := false

var _tracks: Dictionary = {}         # StringName -> Dictionary (voce validata di music.json)
var _streams: Dictionary = {}        # StringName -> AudioStream (cache)
var _players: Array[AudioStreamPlayer] = []
var _jingle: AudioStreamPlayer
var _current: AudioStreamPlayer = null
var _current_id: StringName = &""
var _amp: Dictionary = {}            # AudioStreamPlayer -> ampiezza della dissolvenza (0..1)
var _gain: Dictionary = {}           # AudioStreamPlayer -> gain_db del brano
var _fades: Dictionary = {}          # AudioStreamPlayer -> Tween
var _layer_tweens: Dictionary = {}   # StringName -> Tween
var _duck_db: float = 0.0
var _duck_tween: Tween
var _warned: Dictionary = {}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_ensure_bus()
	for i in 2:
		_players.append(_make_player("Music%s" % ["A", "B"][i]))
	_jingle = _make_player("Jingle")
	_scan(_candidate_dirs())


# ------------------------------------------------------------------ interfaccia

func play(track_id: StringName, fade_s: float = 0.5) -> void:
	if _silenced:
		return
	if _current != null and _current_id == track_id and _current.playing:
		# Il brano continua senza ripartire, ma gli strati tornano spenti: per esempio
		# RICOMINCIA dalla pausa durante l'arena non deve lasciare acceso lo strato "arena".
		_layers_off(track_id)
		return
	var stream := _stream_for(track_id)
	if stream == null:
		stop(fade_s)
		return
	_stop_jingle(minf(fade_s, JINGLE_FADE_S))
	var old := _current
	var nxt := _free_player(old)
	if old != null:
		_fade(old, 0.0, fade_s, true)
	_kill_fade(nxt)
	nxt.stop()
	_reset_layers(track_id, stream)
	nxt.stream = stream
	_gain[nxt] = float(_tracks[track_id]["gain_db"])
	_set_amp(0.0 if fade_s > 0.0 else 1.0, nxt)
	nxt.play()
	_fade(nxt, 1.0, fade_s, false)
	_current = nxt
	_current_id = track_id


func stop(fade_s: float = 0.5) -> void:
	# sfuma tutto ciò che suona, anche un brano ancora in dissolvenza incrociata
	for p in _players:
		if p.playing:
			_fade(p, 0.0, minf(fade_s, float(_amp[p]) * fade_s) if p != _current else fade_s, true)
	_current = null
	_current_id = &""
	_stop_jingle(fade_s)


func set_layer(layer_id: StringName, on: bool) -> void:
	if _current == null or not _tracks.has(_current_id):
		return
	var info: Dictionary = _tracks[_current_id]
	var idx := _layer_index(info, layer_id)
	if idx < 0:
		return
	var sync := _current.stream as AudioStreamSynchronized
	if sync == null:
		return
	var layer: Dictionary = info["layers"][idx]
	var key := StringName("%s/%s" % [_current_id, layer["id"]])
	if _layer_tweens.has(key) and (_layer_tweens[key] as Tween).is_valid():
		(_layer_tweens[key] as Tween).kill()
	var from := db_to_linear(sync.get_sync_stream_volume(idx + 1) - float(layer["gain_db"]))
	var to := 1.0 if on else 0.0
	var tw := create_tween()
	tw.tween_method(_set_layer_amp.bind(sync, idx + 1, float(layer["gain_db"])), from, to, LAYER_FADE_S)
	_layer_tweens[key] = tw


func play_jingle(track_id: StringName) -> void:
	if _silenced:
		return
	if _current != null:
		_fade(_current, 0.0, JINGLE_FADE_S, true)
	_current = null
	_current_id = &""
	var stream := _stream_for(track_id)
	_kill_fade(_jingle)
	_jingle.stop()
	if stream == null:
		return
	_jingle.stream = stream
	_gain[_jingle] = float(_tracks[track_id]["gain_db"])
	_set_amp(1.0, _jingle)
	_jingle.play()


func has_track(track_id: StringName) -> bool:
	return _tracks.has(track_id)


func current_track() -> StringName:
	return _current_id if _current != null else &""


func duck(on: bool) -> void:
	if _duck_tween != null and _duck_tween.is_valid():
		_duck_tween.kill()
	_duck_tween = create_tween()
	_duck_tween.tween_method(_set_duck, _duck_db, DUCK_DB if on else 0.0, DUCK_FADE_S)


## Ferma subito brani, strati e jingle e ignora le richieste successive (chiusura del gioco).
func silence() -> void:
	_silenced = true
	for key: StringName in _layer_tweens.keys():
		if (_layer_tweens[key] as Tween).is_valid():
			(_layer_tweens[key] as Tween).kill()
	if _duck_tween != null and _duck_tween.is_valid():
		_duck_tween.kill()
	for p: AudioStreamPlayer in [_players[0], _players[1], _jingle]:
		_kill_fade(p)
		p.stop()
		p.stream = null
	_current = null
	_current_id = &""


# Alla chiusura i player si fermano, ma l'AudioServer cancella i playback solo nei cicli di mix
# successivi: se il motore esce subito (test da riga di comando che finiscono mentre un suono
# suona ancora) restano "resources still in use at exit". Qui si aspettano al massimo 200 ms,
# finché il server non ha fatto almeno tre cicli di mix.
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


# ------------------------------------------------------------------ ricerca e music.json

func _candidate_dirs() -> PackedStringArray:
	var dirs := PackedStringArray(["res://assets_private/music"])
	dirs.append(OS.get_executable_path().get_base_dir().path_join("music"))
	# La cartella del laboratorio serve solo durante lo sviluppo: le build esportate (modelli
	# d'esportazione, feature "template") non la cercano.
	if OS.has_feature("template"):
		return dirs
	var home := OS.get_environment("USERPROFILE")
	if home.is_empty():
		home = OS.get_environment("HOME")
	if not home.is_empty():
		dirs.append(home.replace("\\", "/").path_join("ctrlaltrevenge-lab").path_join("music"))
	return dirs


## Sceglie la prima cartella utilizzabile; restituisce il percorso ("" se non c'è musica).
func _scan(dirs: PackedStringArray) -> String:
	music_dir = ""
	_tracks = {}
	_streams = {}
	for dir in dirs:
		var manifest := dir.path_join(MANIFEST)
		if not FileAccess.file_exists(manifest):
			continue
		var tracks := _parse_manifest(FileAccess.get_file_as_string(manifest), dir)
		var usable := 0
		for id: StringName in tracks:
			if _file_ok(tracks[id]["path"]):
				usable += 1
		if usable > 0:
			music_dir = dir
			_tracks = tracks
			print("Music: %d brani da %s" % [usable, dir])
			return dir
	print_verbose("Music: nessun music.json utilizzabile, la musica resta spenta")
	return ""


## Legge il testo di music.json; ignora le voci incomplete. Non stampa errori.
func _parse_manifest(text: String, base_dir: String) -> Dictionary:
	var out: Dictionary = {}
	var json := JSON.new()
	if json.parse(text) != OK:
		_warn_once("json:" + base_dir, "Music: %s/%s non è un JSON valido (riga %d: %s)" % [
			base_dir, MANIFEST, json.get_error_line(), json.get_error_message()])
		return out
	var list: Array = []
	if json.data is Dictionary and (json.data as Dictionary).get("tracks") is Array:
		list = json.data["tracks"]
	elif json.data is Array:
		list = json.data
	for t: Variant in list:
		if not t is Dictionary:
			continue
		var d: Dictionary = t
		var id := str(d.get("id", ""))
		var file := str(d.get("file", ""))
		if id.is_empty() or file.is_empty():
			continue
		var layers: Array[Dictionary] = []
		var raw_layers: Variant = d.get("layers", [])
		if raw_layers is Array:
			for l: Variant in raw_layers:
				if l is Dictionary and not str((l as Dictionary).get("file", "")).is_empty():
					layers.append({
						"id": StringName(str(l.get("id", "layer%d" % layers.size()))),
						"path": base_dir.path_join(str(l["file"])),
						"gain_db": _num(l.get("gain_db", 0.0)),
					})
		out[StringName(id)] = {
			"id": StringName(id),
			"path": base_dir.path_join(file),
			"loop": _bool(d.get("loop", true), true),
			"loop_start": _num(d.get("loop_start", 0.0)),
			"loop_end": _num(d.get("loop_end", 0.0)),
			"loop_start_sample": int(_num(d.get("loop_start_sample", -1))),
			"loop_end_sample": int(_num(d.get("loop_end_sample", -1))),
			"sample_rate": int(_num(d.get("sample_rate", 0))),
			"bpm": _num(d.get("bpm", 0.0)),
			"bar_beats": int(_num(d.get("bar_beats", 4))),
			"gain_db": _num(d.get("gain_db", 0.0)),
			"placeholder": _bool(d.get("placeholder", false), false),
			"title": str(d.get("title", "")),
			"license": str(d.get("license", "")),
			"layers": layers,
		}
	return out


func _num(v: Variant) -> float:
	return float(v) if (v is float or v is int) else 0.0


# in GDScript confrontare tipi diversi con == è un errore: i valori non booleani danno il predefinito
func _bool(v: Variant, default: bool) -> bool:
	return v if v is bool else default


## Righe per i crediti: un brano per riga, "titolo" (licenza), solo quelli il cui file c'è.
## Vuoto se non c'è musica.
func credit_lines() -> PackedStringArray:
	var out := PackedStringArray()
	for id: StringName in _tracks:
		var t: Dictionary = _tracks[id]
		if not _file_ok(str(t["path"])):
			continue
		var title := str(t["title"]) if not str(t["title"]).is_empty() else String(id)
		var lic := str(t["license"])
		out.append("\"%s\"%s" % [title, "" if lic.is_empty() else " (%s)" % lic])
	return out


func _file_ok(path: String) -> bool:
	if path.begins_with("res://"):
		return ResourceLoader.exists(path) or FileAccess.file_exists(path)
	return FileAccess.file_exists(path)


# ------------------------------------------------------------------ caricamento

func _stream_for(track_id: StringName) -> AudioStream:
	if _streams.has(track_id):
		return _streams[track_id]
	if not _tracks.has(track_id):
		if not music_dir.is_empty():
			_warn_once("id:" + String(track_id), "Music: nessun brano \"%s\" in %s" % [track_id, music_dir])
		_streams[track_id] = null
		return null
	var info: Dictionary = _tracks[track_id]
	var base := _load_audio(info["path"], info)
	var result: AudioStream = base
	if base != null and not (info["layers"] as Array).is_empty():
		var sync := AudioStreamSynchronized.new()
		var layers: Array = info["layers"]
		sync.stream_count = 1 + layers.size()
		sync.set_sync_stream(0, base)
		sync.set_sync_stream_volume(0, 0.0)
		for i in layers.size():
			var ls := _load_audio(layers[i]["path"], info)
			if ls == null:
				# strato mancante: lo sostituisce il silenzio, la base suona comunque
				ls = _silence()
			sync.set_sync_stream(i + 1, ls)
			sync.set_sync_stream_volume(i + 1, SILENT_DB)
		result = sync
	_streams[track_id] = result
	return result


func _load_audio(path: String, info: Dictionary) -> AudioStream:
	if not _file_ok(path):
		_warn_once("file:" + path, "Music: manca il file %s" % path)
		return null
	var stream: AudioStream = null
	var ext := path.get_extension().to_lower()
	if path.begins_with("res://") and ResourceLoader.exists(path):
		stream = load(path) as AudioStream
	elif ext == "ogg":
		stream = AudioStreamOggVorbis.load_from_file(path)
	elif ext == "wav":
		stream = AudioStreamWAV.load_from_file(path)
	elif ext == "mp3":
		stream = AudioStreamMP3.load_from_file(path)
	if stream == null:
		_warn_once("load:" + path, "Music: non riesco a leggere %s" % path)
		return null
	_apply_loop(stream, info)
	return stream


func _apply_loop(stream: AudioStream, info: Dictionary) -> void:
	var looping: bool = info["loop"]
	var sr := int(info["sample_rate"])
	var s0 := int(info["loop_start_sample"])
	var offset := float(info["loop_start"])
	if sr > 0 and s0 >= 0:
		offset = (float(s0) + 0.5) / float(sr)
	if stream is AudioStreamOggVorbis:
		var ogg := stream as AudioStreamOggVorbis
		ogg.loop = looping
		ogg.loop_offset = offset if looping else 0.0
		ogg.bpm = float(info["bpm"])
		ogg.bar_beats = maxi(1, int(info["bar_beats"]))
		ogg.beat_count = 0  # con beat_count > 0 Godot taglierebbe il loop sul conteggio dei battiti
	elif stream is AudioStreamMP3:
		var mp3 := stream as AudioStreamMP3
		mp3.loop = looping
		mp3.loop_offset = offset if looping else 0.0
		mp3.bpm = float(info["bpm"])
		mp3.bar_beats = maxi(1, int(info["bar_beats"]))
		mp3.beat_count = 0
	elif stream is AudioStreamWAV:
		var wav := stream as AudioStreamWAV
		if not looping:
			wav.loop_mode = AudioStreamWAV.LOOP_DISABLED
			return
		var rate := float(sr if sr > 0 else wav.mix_rate)
		var b := s0 if s0 >= 0 else int(round(float(info["loop_start"]) * rate))
		var e := int(info["loop_end_sample"])
		if e <= 0:
			e = int(round(float(info["loop_end"]) * rate))
		if e > b:
			wav.loop_mode = AudioStreamWAV.LOOP_FORWARD
			wav.loop_begin = b
			wav.loop_end = e


func _free_player(busy: AudioStreamPlayer) -> AudioStreamPlayer:
	# il player diverso da quello in uso; fra i due preferisce quello fermo o più sfumato
	var best: AudioStreamPlayer = null
	for p in _players:
		if p == busy:
			continue
		if best == null or (best.playing and not p.playing) or float(_amp[p]) < float(_amp[best]):
			best = p
	return best


func _silence() -> AudioStreamWAV:
	var w := AudioStreamWAV.new()
	w.format = AudioStreamWAV.FORMAT_16_BITS
	w.mix_rate = 44100
	w.stereo = false
	var data := PackedByteArray()
	data.resize(8820)  # 0,1 s di zeri
	w.data = data
	w.loop_mode = AudioStreamWAV.LOOP_FORWARD
	w.loop_begin = 0
	w.loop_end = 4410
	return w


func _layer_index(info: Dictionary, layer_id: StringName) -> int:
	var layers: Array = info["layers"]
	var short := String(layer_id)
	var prefix := String(info["id"]) + "_"
	if short.begins_with(prefix):
		short = short.substr(prefix.length())
	for i in layers.size():
		if String(layers[i]["id"]) == String(layer_id) or String(layers[i]["id"]) == short:
			return i
	return -1


## Spegne con la dissolvenza tutti gli strati del brano in corso.
func _layers_off(track_id: StringName) -> void:
	if not _tracks.has(track_id):
		return
	for l: Dictionary in _tracks[track_id]["layers"]:
		set_layer(l["id"], false)


func _reset_layers(track_id: StringName, stream: AudioStream) -> void:
	for key: StringName in _layer_tweens.keys():
		if String(key).begins_with(String(track_id) + "/") and (_layer_tweens[key] as Tween).is_valid():
			(_layer_tweens[key] as Tween).kill()
	var sync := stream as AudioStreamSynchronized
	if sync == null:
		return
	sync.set_sync_stream_volume(0, 0.0)
	for i in range(1, sync.stream_count):
		sync.set_sync_stream_volume(i, SILENT_DB)


# ------------------------------------------------------------------ volumi e dissolvenze

func _make_player(player_name: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.name = player_name
	p.bus = BUS
	# Stream e non Sample: gli stream compositi (Synchronized) nel web funzionano solo così
	p.playback_type = AudioServer.PLAYBACK_TYPE_STREAM
	add_child(p)
	_amp[p] = 0.0
	_gain[p] = 0.0
	_apply_volume(p)
	return p


func _fade(p: AudioStreamPlayer, target: float, secs: float, stop_after: bool) -> void:
	_kill_fade(p)
	if secs <= 0.0 or not p.playing:
		_set_amp(target, p)
		if stop_after and target <= 0.0:
			p.stop()
		return
	var tw := create_tween()
	tw.tween_method(_set_amp.bind(p), float(_amp[p]), target, secs)
	if stop_after and target <= 0.0:
		tw.tween_callback(p.stop)
	_fades[p] = tw


func _kill_fade(p: AudioStreamPlayer) -> void:
	if _fades.has(p) and (_fades[p] as Tween).is_valid():
		(_fades[p] as Tween).kill()
	_fades.erase(p)


func _stop_jingle(fade_s: float) -> void:
	if _jingle.playing:
		_fade(_jingle, 0.0, fade_s, true)


func _set_amp(value: float, p: AudioStreamPlayer) -> void:
	_amp[p] = clampf(value, 0.0, 1.0)
	_apply_volume(p)


func _set_duck(value_db: float) -> void:
	_duck_db = value_db
	for p: AudioStreamPlayer in _amp:
		_apply_volume(p)


func _apply_volume(p: AudioStreamPlayer) -> void:
	p.volume_db = float(_gain[p]) + linear_to_db(maxf(float(_amp[p]), MIN_AMP)) + _duck_db


func _set_layer_amp(value: float, sync: AudioStreamSynchronized, index: int, gain_db: float) -> void:
	sync.set_sync_stream_volume(index, linear_to_db(maxf(value, MIN_AMP)) + gain_db)


func _ensure_bus() -> void:
	if AudioServer.get_bus_index(BUS) == -1:
		AudioServer.add_bus()
		var idx := AudioServer.bus_count - 1
		AudioServer.set_bus_name(idx, BUS)
		AudioServer.set_bus_send(idx, &"Master")


func _warn_once(key: String, msg: String) -> void:
	if _warned.has(key):
		return
	_warned[key] = true
	push_warning(msg)


## Solo per le prove: salta a 'seconds' nel brano in corso (anche negli strati).
func _debug_seek(seconds: float) -> void:
	if _current != null and _current.playing:
		_current.seek(seconds)
