extends SceneTree
## Galleria per il controllo visivo con Movie Maker delle schermate che i replay non toccano:
##   godot --path game --write-movie <dir>/f.png --fixed-fps 60 --quit-after 900 -s res://tests/ui_gallery.gd
## Ogni 90 fotogrammi: titolo, crediti, livello con le box di debug (F1), pausa, CONTINUA?,
## GAME OVER, fine demo; dopo 630 fotogrammi chiude da sola (--quit-after è solo una sicurezza).
## La logica è in ui_gallery_impl.gd, caricato a runtime.

var _impl: RefCounted


func _process(_delta: float) -> bool:
	if _impl == null:
		var script: GDScript = load("res://tests/ui_gallery_impl.gd")
		if script == null or not script.can_instantiate():
			printerr("ui_gallery_impl.gd non si compila")
			quit(1)
			return false
		_impl = script.new()
	_impl.call("frame", root)
	return false
