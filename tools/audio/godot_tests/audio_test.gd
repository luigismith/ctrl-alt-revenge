extends Node2D
## Scena di prova per Movie Maker (progetto creato da tools/audio/make_test_project.py):
##   godot --path <progetto> --write-movie <percorso assoluto>/f.png --fixed-fps 60 --quit-after 1500
## Il calendario è in tick di fisica (60 al secondo). Il WAV registrato si analizza con
## tools/audio/analyze_capture.py, che legge le righe "AUDIO_TEST" stampate qui.

## Primo salto: in un punto del brano dove lo strato arena suona sempre (88-105 s).
const SEEK_MID_S := 88.0

const STEPS := [
	[0, "play_stage1"],       # dissolvenza d'ingresso di 0,5 s
	[60, "seek_mid"],         # a 88 s
	[120, "layer_on"],        # strato arena acceso in 0,8 s
	[300, "layer_off"],       # e spento in 0,8 s
	[390, "duck_on"],         # -10 dB in 0,25 s
	[480, "duck_off"],
	[540, "layer_on"],        # di nuovo acceso: deve ripartire al giunto insieme alla base
	[600, "seek_end"],        # a 3 s dalla fine del loop: il giunto cade verso 13 s
	[1080, "jingle"],         # la musica sfuma in 0,3 s, poi "clear" una volta sola
	[1320, "sfx_left"],
	[1356, "sfx_right"],
	[1392, "sfx_center"],
	[1428, "sfx_missing"],
]

var _tick: int = 0
var _label: Label
var _seek_end: float = 0.0


func _ready() -> void:
	var info: Dictionary = Music._tracks.get(&"stage1", {})
	_seek_end = float(info.get("loop_end", 3.0)) - 3.0
	print("AUDIO_TEST music_dir=%s loop_start_sample=%d loop_end_sample=%d sample_rate=%d seek_mid=%.6f seek_end=%.6f mix_rate=%d" % [
		Music.music_dir, int(info.get("loop_start_sample", -1)), int(info.get("loop_end_sample", -1)),
		int(info.get("sample_rate", 0)), SEEK_MID_S, _seek_end, AudioServer.get_mix_rate()])
	var bg := ColorRect.new()
	bg.color = Color(0.07, 0.06, 0.14)
	bg.size = Vector2(480, 270)
	add_child(bg)
	_label = Label.new()
	_label.position = Vector2(8, 8)
	add_child(_label)


func _physics_process(_delta: float) -> void:
	for step: Array in STEPS:
		if step[0] == _tick:
			_run(step[1])
	_label.text = "prova audio - tick %d" % _tick
	_tick += 1


func _run(what: String) -> void:
	print("AUDIO_TEST tick=%d %s" % [_tick, what])
	match what:
		"play_stage1":
			Music.play(&"stage1", 0.5)
		"seek_mid":
			Music._debug_seek(SEEK_MID_S)
		"seek_end":
			Music._debug_seek(_seek_end)
		"layer_on":
			Music.set_layer(&"arena", true)
		"layer_off":
			Music.set_layer(&"stage1_arena", false)
		"duck_on":
			Music.duck(true)
		"duck_off":
			Music.duck(false)
		"jingle":
			Music.play_jingle(&"clear")
		"sfx_left":
			Sfx.play_at(&"hit_heavy", 8.0, 0.0)
		"sfx_right":
			Sfx.play_at(&"hit_heavy", 376.0, 0.0)
		"sfx_center":
			Sfx.play(&"hit_heavy", 0.0)
		"sfx_missing":
			Sfx.play(&"non_esiste")
