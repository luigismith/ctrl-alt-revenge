extends SceneTree
## Prove dell'audio da riga di comando (progetto di prova creato da tools/audio/make_test_project.py):
##   godot --headless --path <progetto> -s res://tests/test_audio.gd
## Controlla la ricerca della musica e la lettura di music.json (compreso il caso "nessuna
## musica"), i bus, l'autoload Sfx (cache, guadagni, pan, file mancanti).
## Stampa una riga per prova e, se tutto passa, l'ultima riga "DONE"; esce con 0 solo se tutto passa.

const MusicScript := preload("res://src/audio/music_director.gd")
const SfxScript := preload("res://src/audio/sfx.gd")
const SFX_NAMES := [
	"whoosh_light", "whoosh_heavy", "hit_light", "hit_medium", "hit_heavy", "hit_kick", "knee",
	"grab", "throw", "body_fall", "body_thud", "step_a", "step_b", "jump", "land", "glint",
	"zap", "bin_hit", "bin_break", "pickup", "ko", "ui_move", "ui_confirm", "ui_pause", "go_arrow",
]

var _failures: int = 0
var _count: int = 0


func _initialize() -> void:
	process_frame.connect(_run, CONNECT_ONE_SHOT)


func check(condition: bool, test_name: String) -> void:
	_count += 1
	if condition:
		print("ok   - " + test_name)
	else:
		_failures += 1
		printerr("FAIL - " + test_name)


func _run() -> void:
	_test_buses()
	_test_manifest_parsing()
	_test_search_order_and_no_music()
	_test_real_music()
	_test_sfx()
	await create_timer(0.2).timeout
	if _failures == 0:
		print("Test passati: %d" % _count)
		print("DONE")
		quit(0)
	else:
		printerr("Test falliti: %d su %d" % [_failures, _count])
		quit(1)


func _test_buses() -> void:
	check(AudioServer.get_bus_index(&"Music") > 0, "bus Music presente")
	check(AudioServer.get_bus_index(&"SFX") > 0, "bus SFX presente")
	var has_limiter := false
	for i in AudioServer.get_bus_effect_count(0):
		if AudioServer.get_bus_effect(0, i) is AudioEffectHardLimiter:
			has_limiter = true
	check(has_limiter, "limitatore sul bus Master")
	check(is_equal_approx(AudioServer.get_bus_volume_db(AudioServer.get_bus_index(&"Music")), -6.0), "Music a -6 dB")


func _new_music() -> Node:
	var md: Node = MusicScript.new()
	root.add_child(md)
	return md


func _test_manifest_parsing() -> void:
	var md := _new_music()
	var text := """{"format": 1, "tracks": [
		{"id": "stage1", "file": "s.ogg", "loop": true, "loop_start": 1.5, "loop_end": 10.0,
		 "loop_start_sample": 66150, "loop_end_sample": 441000, "sample_rate": 44100, "bpm": 150,
		 "bar_beats": 4, "gain_db": -2, "placeholder": true, "source": "prova",
		 "layers": [{"id": "arena", "file": "s_arena.ogg", "gain_db": -1}, {"id": "vuoto"}]},
		{"id": "clear", "file": "c.ogg", "loop": false},
		{"id": "", "file": "x.ogg"}, {"file": "y.ogg"}, {"id": "z"}, 42, "boh",
		{"id": "strano", "file": "w.ogg", "bpm": "veloce", "loop": "no", "layers": "niente"}]}"""
	var t: Dictionary = md._parse_manifest(text, "C:/finta")
	check(t.size() == 3, "music.json: 3 voci valide su 8")
	check(t.has(&"stage1") and t.has(&"clear") and t.has(&"strano"), "music.json: id letti come StringName")
	var s: Dictionary = t.get(&"stage1", {})
	check(s.get("path") == "C:/finta/s.ogg", "music.json: percorso = cartella + file")
	check(s.get("loop") == true and is_equal_approx(s.get("loop_start", 0.0), 1.5), "music.json: loop e inizio")
	check(s.get("loop_start_sample") == 66150 and s.get("sample_rate") == 44100, "music.json: campioni esatti")
	check(is_equal_approx(s.get("gain_db", 0.0), -2.0) and s.get("placeholder") == true, "music.json: guadagno e segnaposto")
	var layers: Array = s.get("layers", [])
	check(layers.size() == 1 and layers[0]["id"] == &"arena" and layers[0]["path"] == "C:/finta/s_arena.ogg",
		"music.json: strato arena (lo strato senza file è scartato)")
	check(t[&"clear"]["loop"] == false, "music.json: jingle senza loop")
	var w: Dictionary = t[&"strano"]
	check(w["bpm"] == 0.0 and w["loop"] == true and (w["layers"] as Array).is_empty(),
		"music.json: valori del tipo sbagliato diventano i predefiniti, senza errori")
	check(md._parse_manifest("{rotto", "x").is_empty(), "music.json non valido: nessun brano, nessun errore")
	check(md._parse_manifest("[]", "x").is_empty(), "music.json vuoto: nessun brano")
	var arr: Dictionary = md._parse_manifest('[{"id": "title", "file": "t.ogg"}]', "D:/m")
	check(arr.size() == 1 and arr[&"title"]["loop"] == true and is_equal_approx(arr[&"title"]["gain_db"], 0.0)
		and arr[&"title"]["loop_start_sample"] == -1, "music.json come lista semplice, con i valori predefiniti")
	check(md._layer_index(s, &"arena") == 0 and md._layer_index(s, &"stage1_arena") == 0
		and md._layer_index(s, &"boss") == -1, "strato per id corto e lungo")
	md.queue_free()


func _write(path: String, text: String) -> void:
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string(text)
	f.close()


func _test_search_order_and_no_music() -> void:
	var base := OS.get_user_data_dir().path_join("audio_test_dirs")
	for d in ["vuota", "rotta", "senza_file", "buona", "buona2"]:
		DirAccess.make_dir_recursive_absolute(base.path_join(d))
	_write(base.path_join("rotta/music.json"), "{ non è json")
	_write(base.path_join("senza_file/music.json"), '{"tracks": [{"id": "stage1", "file": "manca.ogg"}]}')
	_write(base.path_join("buona/music.json"), '{"tracks": [{"id": "stage1", "file": "stage1.ogg"}]}')
	_write(base.path_join("buona/stage1.ogg"), "finto")
	_write(base.path_join("buona2/music.json"), '{"tracks": [{"id": "title", "file": "title.ogg"}]}')
	_write(base.path_join("buona2/title.ogg"), "finto")
	var md := _new_music()
	var dirs := PackedStringArray([base.path_join("non_esiste"), base.path_join("vuota"), base.path_join("rotta"),
		base.path_join("senza_file"), base.path_join("buona"), base.path_join("buona2")])
	check(md._scan(dirs) == base.path_join("buona"), "ricerca: vince la prima cartella con un brano esistente")
	check(md._tracks.has(&"stage1") and not md._tracks.has(&"title"), "ricerca: brani della cartella scelta")
	check(md._scan(PackedStringArray([base.path_join("buona2"), base.path_join("buona")])) == base.path_join("buona2"),
		"ricerca: conta l'ordine")
	var cands: PackedStringArray = md._candidate_dirs()
	check(cands.size() == 3 and cands[0] == "res://assets_private/music", "cartelle: prima res://assets_private/music")
	check(cands[1] == OS.get_executable_path().get_base_dir().path_join("music"), "cartelle: poi music/ accanto all'eseguibile")
	check(cands[2].ends_with("ctrlaltrevenge-lab/music") and not cands[2].contains("\\"), "cartelle: infine il laboratorio")
	# nessuna musica: tutto muto, nessun errore
	check(md._scan(PackedStringArray()) == "" and md.music_dir == "", "nessuna musica: cartella vuota")
	check(md._scan(PackedStringArray([base.path_join("non_esiste"), base.path_join("rotta")])) == "",
		"nessuna musica: cartelle inesistenti o rotte")
	md.play(&"stage1")
	md.set_layer(&"arena", true)
	md.duck(true)
	md.play_jingle(&"clear")
	md.duck(false)
	md.stop(0.0)
	md.play(&"title", 0.0)
	var silent := true
	for p: Node in md.get_children():
		if p is AudioStreamPlayer and (p as AudioStreamPlayer).playing:
			silent = false
	check(silent, "nessuna musica: play/set_layer/play_jingle/duck/stop non suonano e non danno errori")
	# brano in WAV: si carica con AudioStreamWAV.load_from_file e il loop usa i campioni di music.json
	var wav_dir := base.path_join("wav")
	DirAccess.make_dir_recursive_absolute(wav_dir)
	var src := AudioStreamWAV.new()
	src.format = AudioStreamWAV.FORMAT_16_BITS
	src.mix_rate = 44100
	src.stereo = false
	var data := PackedByteArray()
	data.resize(44100 * 2)
	for i in 44100:
		data.encode_s16(i * 2, int(8000.0 * sin(TAU * 220.0 * i / 44100.0)))
	src.data = data
	src.save_to_wav(wav_dir.path_join("prova.wav"))
	_write(wav_dir.path_join("music.json"), '{"tracks": [{"id": "stage1", "file": "prova.wav", "loop": true, '
		+ '"loop_start": 0.25, "loop_end": 1.0, "loop_start_sample": 11025, "loop_end_sample": 44100, '
		+ '"sample_rate": 44100}, {"id": "clear", "file": "prova.wav", "loop": false}]}')
	check(md._scan(PackedStringArray([wav_dir])) == wav_dir, "WAV: cartella trovata")
	md.play(&"stage1", 0.0)
	var ws := md._current.stream as AudioStreamWAV if md._current != null else null
	check(ws != null and ws.loop_mode == AudioStreamWAV.LOOP_FORWARD and ws.loop_begin == 11025
		and ws.loop_end == 44100, "WAV: loop in avanti dai campioni 11025-44100")
	md.play_jingle(&"clear")
	var wj := md._jingle.stream as AudioStreamWAV
	check(wj != null and wj.loop_mode == AudioStreamWAV.LOOP_DISABLED and md._jingle.playing, "WAV: jingle senza loop")
	md.stop(0.0)
	md.queue_free()


func _test_real_music() -> void:
	var md := _new_music()
	var cands: PackedStringArray = md._candidate_dirs()
	var dir: String = md._scan(PackedStringArray([cands[2]]))
	if dir.is_empty():
		print("saltato - musica vera non presente in %s" % cands[2])
		md.queue_free()
		return
	check(md._tracks.has(&"stage1") and md._tracks.has(&"title") and md._tracks.has(&"clear"),
		"musica vera: title, stage1 e clear in music.json")
	var info: Dictionary = md._tracks[&"stage1"]
	md.play(&"stage1", 0.0)
	var sync := md._current.stream as AudioStreamSynchronized
	check(sync != null and sync.stream_count == 2, "stage1: AudioStreamSynchronized con base e arena")
	if sync != null:
		var ogg := sync.get_sync_stream(0) as AudioStreamOggVorbis
		var want := (float(info["loop_start_sample"]) + 0.5) / float(info["sample_rate"])
		check(ogg != null and ogg.loop and absf(ogg.loop_offset - want) < 1e-7 and ogg.beat_count == 0,
			"stage1: loop con loop_offset = (inizio + 0,5 campioni) / frequenza")
		var arena := sync.get_sync_stream(1) as AudioStreamOggVorbis
		check(arena != null and absf(arena.loop_offset - want) < 1e-7, "stage1: lo strato ha lo stesso loop")
		check(absf(ogg.get_length() - float(info["loop_end"])) < 0.002, "stage1: il file finisce alla fine del loop")
		check(sync.get_sync_stream_volume(1) <= -79.0, "stage1: strato arena spento all'avvio")
	md.play(&"stage1", 0.5)
	check(md._current.playing and md._current_id == &"stage1", "play dello stesso brano: non riparte")
	md.play_jingle(&"clear")
	var jingle := md._jingle as AudioStreamPlayer
	var jog := jingle.stream as AudioStreamOggVorbis
	check(jingle.playing and jog != null and not jog.loop, "clear: jingle senza loop")
	md.play(&"title", 0.0)
	var t_ogg := md._current.stream as AudioStreamOggVorbis
	check(t_ogg != null and t_ogg.loop, "title: brano semplice in loop")
	md.stop(0.0)
	md.queue_free()


func _test_sfx() -> void:
	var sfx: Node = SfxScript.new()
	root.add_child(sfx)
	check(sfx._mix_db.size() == SFX_NAMES.size(), "Sfx: mix.json con %d guadagni" % SFX_NAMES.size())
	var loaded := 0
	for n in SFX_NAMES:
		if sfx._cache.get(StringName(n)) is AudioStreamWAV:
			loaded += 1
	check(loaded == SFX_NAMES.size(), "Sfx: tutti i %d WAV caricati all'avvio" % SFX_NAMES.size())
	var w: AudioStreamWAV = sfx._cache.get(&"hit_heavy")
	check(w != null and not w.stereo and w.mix_rate == 44100 and w.format == AudioStreamWAV.FORMAT_16_BITS,
		"Sfx: WAV mono 16 bit 44,1 kHz importato in PCM")
	check(w != null and w.loop_mode == AudioStreamWAV.LOOP_DISABLED, "Sfx: nessun loop negli effetti")
	sfx.play(&"hit_light")
	var playing := _playing(sfx)
	check(playing == 1, "Sfx: play() fa partire una voce")
	sfx.play(&"hit_light")
	check(_playing(sfx) == 1, "Sfx: lo stesso suono nello stesso tick parte una volta sola")
	sfx.play(&"non_esiste")
	sfx.play(&"neanche_questo")
	check(sfx._warned and _playing(sfx) == 1, "Sfx: suoni mancanti ignorati con un solo avviso")
	var vp := root.get_viewport()
	var width := vp.get_visible_rect().size.x
	check(width == 480.0, "viewport larga 480 px (il pan usa questa misura)")
	check(sfx._pan_slot(0.0) == 0 and sfx._pan_slot(479.0) == 4 and sfx._pan_slot(240.0) == 2
		and sfx._pan_slot(-500.0) == 0 and sfx._pan_slot(5000.0) == 4, "Sfx: cinque posizioni di pan sullo schermo")
	var idx := AudioServer.get_bus_index(&"SFX_L2")
	var pan_ok := idx > 0 and AudioServer.get_bus_send(idx) == &"SFX" and AudioServer.get_bus_effect(idx, 0) is AudioEffectPanner
	if pan_ok:
		pan_ok = is_equal_approx((AudioServer.get_bus_effect(idx, 0) as AudioEffectPanner).pan, -0.25)
	check(pan_ok, "Sfx: bus del pan figli di SFX con AudioEffectPanner")
	check(AudioServer.get_bus_index(&"SFX_L2") > AudioServer.get_bus_index(&"SFX"), "Sfx: i bus del pan stanno dopo SFX")
	for i in 14:
		sfx._last_tick.clear()
		sfx.play(StringName(SFX_NAMES[i % SFX_NAMES.size()]))
	check(_playing(sfx) <= 12, "Sfx: al massimo 12 voci (le più vecchie si riusano)")
	sfx.queue_free()


func _playing(sfx: Node) -> int:
	var n := 0
	for p: Node in sfx.get_children():
		if p is AudioStreamPlayer and (p as AudioStreamPlayer).playing:
			n += 1
	return n
