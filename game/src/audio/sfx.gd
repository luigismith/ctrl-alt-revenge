extends Node
## Effetti sonori (autoload "Sfx").
##
## Interfaccia usata dal gameplay (non cambiarla senza aggiornare docs/specifica-slice.md):
##   Sfx.play(sfx_name, pitch_jitter = 0.05, volume_db = 0.0)
##     suona game/assets/sfx/<sfx_name>.wav su un bus "SFX"; se il file manca non fa nulla
##     (al massimo un avviso una volta sola, mai un errore).
##   Sfx.play_at(sfx_name, world_x, pitch_jitter = 0.05, volume_db = 0.0)
##     come play(), con un leggero pan stereo in base alla posizione sullo schermo.
## Il pitch casuale usa un generatore suo: non tocca il determinismo del gameplay.
##
## Come funziona:
## - 12 AudioStreamPlayer in un pool; se sono tutti occupati si riusa quello partito per primo.
## - I suoni elencati in assets/sfx/mix.json si caricano all'avvio, gli altri alla prima richiesta;
##   poi restano in cache (anche quando mancano, così l'avviso esce una volta sola).
## - mix.json (scritto da tools/audio/sfx_gen.py) dà il guadagno di missaggio di ogni suono:
##   i file hanno tutti il picco a -1 dBFS, il bilanciamento sta lì. volume_db si somma.
## - Pan: cinque posizioni. Sono bus figli di "SFX" con un AudioEffectPanner, creati all'avvio.
##   La posizione sullo schermo si ricava dalla trasformazione del canvas della viewport
##   (la Camera2D), quindi play_at vuole la x del mondo.
## - Lo stesso suono chiesto più volte nello stesso tick di fisica suona una volta sola.
## - process_mode ALWAYS: i suoni dell'interfaccia funzionano anche a gioco in pausa.
## - silence() ferma tutte le voci e non ne fa partire altre: serve prima di chiudere il gioco
##   (Game.quit_clean). Con Movie Maker l'audio si mescola solo dentro i fotogrammi registrati e
##   l'AudioServer libera i suoni fermati nei cicli di mix successivi: se il motore esce mentre
##   un suono suona, restano "resources still in use at exit". Per questo le registrazioni
##   finiscono con --quit-at-end (o con la galleria che chiude da sola), non con --quit-after.

const SFX_DIR := "res://assets/sfx/"
const MIX_FILE := "res://assets/sfx/mix.json"
const BUS := &"SFX"
const POOL_SIZE := 12
## Pan delle cinque posizioni (da sinistra a destra) e nomi dei bus; il centro è "SFX" stesso.
const PAN_VALUES: Array[float] = [-0.25, -0.12, 0.0, 0.12, 0.25]
const PAN_BUSES: Array[StringName] = [&"SFX_L2", &"SFX_L1", &"SFX", &"SFX_R1", &"SFX_R2"]
const MAX_JITTER := 0.5

var _players: Array[AudioStreamPlayer] = []
var _silenced := false
var _started: Array[int] = []
var _next_order: int = 0
var _cache: Dictionary = {}       # StringName -> AudioStream (null se manca)
var _mix_db: Dictionary = {}      # StringName -> float
var _last_tick: Dictionary = {}   # StringName -> tick di fisica dell'ultima partenza
var _warned := false
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	# seme fisso: le prove registrate (Movie Maker) suonano sempre uguali
	_rng.seed = 20261103
	_ensure_buses()
	for i in POOL_SIZE:
		var p := AudioStreamPlayer.new()
		p.name = "Voice%d" % i
		p.bus = BUS
		add_child(p)
		_players.append(p)
		_started.append(-1)
	_load_mix()
	for sfx_name: StringName in _mix_db:
		_get_stream(sfx_name)


## Ferma tutte le voci e ignora i suoni chiesti dopo (chiusura del gioco).
func silence() -> void:
	_silenced = true
	for p in _players:
		p.stop()
		p.stream = null


func play(sfx_name: StringName, pitch_jitter: float = 0.05, volume_db: float = 0.0) -> void:
	_play(sfx_name, 2, pitch_jitter, volume_db)


func play_at(sfx_name: StringName, world_x: float, pitch_jitter: float = 0.05, volume_db: float = 0.0) -> void:
	_play(sfx_name, _pan_slot(world_x), pitch_jitter, volume_db)


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


# ------------------------------------------------------------------ interni

func _play(sfx_name: StringName, slot: int, pitch_jitter: float, volume_db: float) -> void:
	if _silenced:
		return
	var stream := _get_stream(sfx_name)
	if stream == null:
		return
	var tick := Engine.get_physics_frames()
	if _last_tick.get(sfx_name, -1) == tick:
		return
	_last_tick[sfx_name] = tick
	var i := _free_voice()
	var p := _players[i]
	p.stop()
	p.stream = stream
	p.bus = _bus_for_slot(slot)
	p.volume_db = float(_mix_db.get(sfx_name, 0.0)) + volume_db
	var j := clampf(absf(pitch_jitter), 0.0, MAX_JITTER)
	p.pitch_scale = 1.0 + _rng.randf_range(-j, j) if j > 0.0 else 1.0
	p.play()
	_started[i] = _next_order
	_next_order += 1


func _free_voice() -> int:
	var oldest := 0
	for i in POOL_SIZE:
		if not _players[i].playing:
			return i
		if _started[i] < _started[oldest]:
			oldest = i
	return oldest


func _get_stream(sfx_name: StringName) -> AudioStream:
	if _cache.has(sfx_name):
		return _cache[sfx_name]
	var path := SFX_DIR + String(sfx_name) + ".wav"
	var stream: AudioStream = null
	if ResourceLoader.exists(path):
		stream = load(path) as AudioStream
	if stream == null and not _warned:
		_warned = true
		push_warning("Sfx: manca %s (gli altri suoni mancanti non saranno segnalati)" % path)
	_cache[sfx_name] = stream
	return stream


func _load_mix() -> void:
	if not FileAccess.file_exists(MIX_FILE):
		return
	var json := JSON.new()
	if json.parse(FileAccess.get_file_as_string(MIX_FILE)) != OK:
		push_warning("Sfx: %s non è un JSON valido, guadagni a 0 dB" % MIX_FILE)
		return
	var data: Variant = json.data
	if data is Dictionary and data.get("gain_db") is Dictionary:
		var gains: Dictionary = data["gain_db"]
		for key: Variant in gains:
			_mix_db[StringName(str(key))] = float(gains[key])


func _pan_slot(world_x: float) -> int:
	var vp := get_viewport()
	if vp == null:
		return 2
	var width := vp.get_visible_rect().size.x
	if width <= 0.0:
		return 2
	var screen_x := (vp.get_canvas_transform() * Vector2(world_x, 0.0)).x
	var u := clampf(screen_x / width, 0.0, 0.9999)
	return int(u * PAN_VALUES.size())


func _bus_for_slot(slot: int) -> StringName:
	var bus_name := PAN_BUSES[clampi(slot, 0, PAN_BUSES.size() - 1)]
	# se qualcuno ha ricaricato il layout dei bus, i bus del pan vanno ricreati
	if AudioServer.get_bus_index(bus_name) == -1:
		_ensure_buses()
	return bus_name


func _ensure_buses() -> void:
	if AudioServer.get_bus_index(BUS) == -1:
		AudioServer.add_bus()
		var idx := AudioServer.bus_count - 1
		AudioServer.set_bus_name(idx, BUS)
		AudioServer.set_bus_send(idx, &"Master")
	for k in PAN_BUSES.size():
		var bus_name := PAN_BUSES[k]
		if bus_name == BUS or AudioServer.get_bus_index(bus_name) != -1:
			continue
		# i bus nuovi vanno in fondo: in Godot un bus manda solo a bus con indice più basso
		AudioServer.add_bus()
		var idx := AudioServer.bus_count - 1
		AudioServer.set_bus_name(idx, bus_name)
		AudioServer.set_bus_send(idx, BUS)
		var panner := AudioEffectPanner.new()
		panner.pan = PAN_VALUES[k]
		AudioServer.add_bus_effect(idx, panner)
