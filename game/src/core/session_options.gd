class_name SessionOptions
extends RefCounted
## Opzioni della sessione lette dagli argomenti utente (quelli dopo "--").
##
##   --autostart            salta il titolo e parte dal livello
##   --replay <file>        riproduce gli ingressi del file (res://, user:// o percorso assoluto)
##   --seed <n>             seme del livello (vince sul seme del replay)
##   --record <file>        alla fine del livello salva gli ingressi giocati in un replay
##   --start-x <x>          fa partire GIG da questa x (prova rapida di un punto del livello)
##   --autopilot <scenario> GIG gioca da solo (serve a generare i replay di prova)
##   --quit-at-end          esce quando il replay finisce o il livello termina
##   --print-hash           alla fine stampa l'hash dello stato della simulazione
##   --debug-boxes          parte con hitbox e hurtbox visibili (come F1; solo build di debug)

var autostart: bool = false
var replay_path: String = ""
var record_path: String = ""
var level_seed: int = 1
var seed_given: bool = false
var start_x: float = -1.0
var autopilot: String = ""
var quit_at_end: bool = false
var print_hash: bool = false
var debug_boxes: bool = false
var unknown: PackedStringArray = []


static func parse(args: PackedStringArray) -> SessionOptions:
	var o := SessionOptions.new()
	var i := 0
	while i < args.size():
		var a := args[i]
		var next := args[i + 1] if i + 1 < args.size() else ""
		match a:
			"--autostart":
				o.autostart = true
			"--replay":
				o.replay_path = next
				o.autostart = true
				i += 1
			"--record":
				o.record_path = next
				i += 1
			"--seed":
				o.level_seed = int(next)
				o.seed_given = true
				i += 1
			"--start-x":
				o.start_x = float(next)
				o.autostart = true
				i += 1
			"--autopilot":
				o.autopilot = next
				o.autostart = true
				i += 1
			"--quit-at-end":
				o.quit_at_end = true
			"--print-hash":
				o.print_hash = true
			"--debug-boxes":
				o.debug_boxes = true
			_:
				# Le parole senza "--" sono argomenti di altri script (es. make_replays.gd).
				if a.begins_with("--"):
					o.unknown.append(a)
		i += 1
	return o
