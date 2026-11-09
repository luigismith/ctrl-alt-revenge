class_name SessionOptions
extends RefCounted
## Opzioni della sessione lette dagli argomenti utente (quelli dopo "--").
##
##   --autostart            salta il titolo e parte dal livello
##   --stanza               parte dalla stanza di prova in grigio (tappa 1)
##   --prologo              parte dal prologo in grigio (tappa 2)
##   --nuova-partita        salta il titolo e fa NUOVA PARTITA: il prologo e poi lo slice (con --autopilot
##                          stanza il prologo lo gioca il pilota, lo slice resta ai tasti)
##   --skip-to <tick>       nella stanza, un replay corre senza disegnare fino a quel tick
##   --replay <file>        riproduce gli ingressi del file (res://, user:// o percorso assoluto)
##   --seed <n>             seme del livello (vince sul seme del replay)
##   --record <file>        alla fine del livello salva gli ingressi giocati in un replay
##   --start-x <x>          fa partire GIG da questa x (prova rapida di un punto del livello)
##   --start-y <y>          con --start-x, i piedi di GIG a questa y (per un piano sopra quello di partenza)
##   --livello <nome>       nel prologo parte da questo livello del file LDtk (Prologo_B_Fuga)
##   --autopilot <scenario> GIG gioca da solo (serve a generare i replay di prova)
##   --quit-at-end          esce quando il replay finisce o il livello termina
##   --print-hash           alla fine stampa l'hash dello stato della simulazione
##   --debug-boxes          parte con hitbox e hurtbox visibili (come F1; solo build di debug)
##   --no-lights            parte con le luci dinamiche spente (come F5)
##   --solo-droni <tipi>    nei tratti platform tiene solo i droni di questi tipi (segugio,vedetta):
##                          serve a riprendere un drone da solo con Movie Maker
##   --b-grigio             nel prologo, B senza la scena disegnata delle palazzine (fatta per la griglia
##                          di prima): i blocchi in grigio e dietro il piano medio (con --prologo --livello
##                          Prologo_B_Fuga si prova la griglia nuova di B col pad)
##   --camera-stretta       nei tratti platform la vista resta quella di sempre, 480 × 270 (la telecamera
##                          larga è normale dall'8 novembre 2026; vedi TestRoom.wide_cam)
##   --camera-larga         la telecamera larga (è già normale: resta per i comandi di prima)
##   --senza-hud            senza l'interfaccia (barre, scritte, VAI), anche nelle arene: serve alle
##                          riprese con Movie Maker per il teaser e il sito

var autostart: bool = false
var room: bool = false
var prologue: bool = false
var new_game: bool = false
var skip_to: int = 0
var replay_path: String = ""
var record_path: String = ""
var level_seed: int = 1
var seed_given: bool = false
var start_x: float = -1.0
var start_y: float = -1.0
## --livello <nome>: il livello del file da cui parte il prologo (per esempio Prologo_B_Fuga).
var level_name: String = ""
var autopilot: String = ""
var quit_at_end: bool = false
var print_hash: bool = false
var debug_boxes: bool = false
var no_lights: bool = false
## --solo-droni: i tipi di drone da tenere; vuoto, tutti.
var solo_drones: PackedStringArray = []
## La telecamera larga nel platform (Luigi, 8 novembre 2026: normale, non più dietro un'opzione);
## --camera-stretta la spegne.
var wide_camera: bool = true
## --b-grigio: B del prologo in grigio, col piano medio dietro.
var grey_b: bool = false
## --senza-hud: niente interfaccia sopra il gioco, per le riprese.
var no_hud: bool = false
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
			"--stanza":
				o.room = true
			"--prologo":
				o.room = true
				o.prologue = true
			"--nuova-partita":
				o.new_game = true
			"--skip-to":
				o.skip_to = int(next)
				i += 1
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
			"--livello":
				o.level_name = next
				o.autostart = true
				i += 1
			"--start-x":
				o.start_x = float(next)
				o.autostart = true
				i += 1
			"--start-y":
				o.start_y = float(next)
				i += 1
			"--autopilot":
				o.autopilot = next
				o.autostart = true
				if next == "stanza":
					o.room = true
				i += 1
			"--quit-at-end":
				o.quit_at_end = true
			"--print-hash":
				o.print_hash = true
			"--debug-boxes":
				o.debug_boxes = true
			"--no-lights":
				o.no_lights = true
			"--camera-larga":
				o.wide_camera = true
			"--camera-stretta":
				o.wide_camera = false
			"--b-grigio":
				o.grey_b = true
			"--senza-hud":
				o.no_hud = true
			"--solo-droni":
				o.solo_drones = next.split(",", false)
				i += 1
			_:
				# Le parole senza "--" sono argomenti di altri script (es. make_replays.gd).
				if a.begins_with("--"):
					o.unknown.append(a)
		i += 1
	return o
