extends Node
## Effetti sonori (autoload "Sfx"). STUB: l'implementazione la scrive chi cura l'audio.
##
## Interfaccia usata dal gameplay (non cambiarla senza aggiornare docs/specifica-slice.md):
##   Sfx.play(sfx_name, pitch_jitter = 0.05, volume_db = 0.0)
##     suona game/assets/sfx/<sfx_name>.wav su un bus "SFX"; se il file manca non fa nulla
##     (al massimo un avviso una volta sola, mai un errore).
##   Sfx.play_at(sfx_name, world_x, pitch_jitter = 0.05, volume_db = 0.0)
##     come play(), con un leggero pan stereo in base alla posizione sullo schermo.
## Il pitch casuale usa un generatore suo: non tocca il determinismo del gameplay.


func play(sfx_name: StringName, pitch_jitter: float = 0.05, volume_db: float = 0.0) -> void:
	pass


func play_at(sfx_name: StringName, world_x: float, pitch_jitter: float = 0.05, volume_db: float = 0.0) -> void:
	pass
