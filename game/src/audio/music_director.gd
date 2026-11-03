extends Node
## Musica (autoload "Music"). STUB: l'implementazione la scrive chi cura l'audio.
##
## La musica non è nel repo. I brani si cercano, in quest'ordine, in:
##   1. res://assets_private/music/
##   2. <cartella dell'eseguibile>/music/
##   3. %USERPROFILE%/ctrlaltrevenge-lab/music/
## dove un file music.json descrive ogni brano (id, file, loop, BPM, strati).
## Se non trova nulla resta muto, senza errori.
##
## Interfaccia usata dal gameplay (non cambiarla senza aggiornare docs/specifica-slice.md):
##   Music.play(track_id, fade_s = 0.5)        brano in loop: "title", "stage1"
##   Music.stop(fade_s = 0.5)
##   Music.set_layer(layer_id, on)             strato in più, es. "arena" durante l'arena
##   Music.play_jingle(track_id)               non in loop, es. "clear"; poi silenzio
##   Music.duck(on)                            abbassa la musica (pausa, schermate)
## Il player gira con PROCESS_MODE_ALWAYS: la pausa del gioco non ferma la musica.


func play(track_id: StringName, fade_s: float = 0.5) -> void:
	pass


func stop(fade_s: float = 0.5) -> void:
	pass


func set_layer(layer_id: StringName, on: bool) -> void:
	pass


func play_jingle(track_id: StringName) -> void:
	pass


func duck(on: bool) -> void:
	pass
