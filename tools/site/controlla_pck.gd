# SPDX-License-Identifier: MIT
extends SceneTree
## Controllo del pacchetto esportato, lanciato da export_web.sh:
##   godot --headless --main-pack <index.pck> -s tools/site/controlla_pck.gd
## Carica i dati dei combattenti come li legge la build. In Godot 4.7.2 la conversione dei .tres in
## binario all'esportazione svuotava i PackedStringArray e i PackedFloat32Array (attacks e
## attack_weights): nella demo web i nemici non avevano attacchi. Per questo project.godot la spegne
## (editor/export/convert_text_resources_to_binary=false), e qui si controlla che resti così.

const DIR := "res://data/fighters"


func _init() -> void:
	var errors := PackedStringArray()
	var n := 0
	var armed := 0
	for f in ResourceLoader.list_directory(DIR):
		if not f.ends_with(".tres"):
			continue
		var d: Resource = load(DIR.path_join(f))
		if d == null:
			errors.append("%s non si carica" % f)
			continue
		n += 1
		var attacks: PackedStringArray = d.get("attacks")
		var weights: PackedFloat32Array = d.get("attack_weights")
		armed += 1 if not attacks.is_empty() else 0
		if (not weights.is_empty() or not attacks.is_empty()) and weights.size() != attacks.size():
			errors.append("%s: %d attacchi e %d pesi" % [f, attacks.size(), weights.size()])
		for a in attacks:
			if load("res://data/attacks/%s.tres" % a) == null:
				errors.append("%s: manca l'attacco %s" % [f, a])
	if n == 0:
		errors.append("nessun combattente in %s" % DIR)
	elif armed == 0:
		errors.append("nessun combattente ha attacchi")
	if errors.is_empty():
		print("Pacchetto controllato: %d combattenti, %d con i loro attacchi." % [n, armed])
		print("CONTROLLO_PCK_OK")
	else:
		for e in errors:
			printerr("Pacchetto: " + e)
	quit(0 if errors.is_empty() else 1)
