class_name FighterData
extends Resource
## Valori di un personaggio (§5), salvati in game/data/fighters/*.tres.
## Velocità in px per tick, tempi in tick a 60 Hz.

@export var id: StringName = &""
## Nome mostrato nell'interfaccia.
@export var display_name: String = ""
@export var sprite_id: StringName = &""
@export var max_hp: int = 48
@export var walk_speed: Vector2 = Vector2(1.875, 1.25)
@export var run_speed: float = 3.75
@export var jump_velocity: float = 5.5
@export var gravity: float = 0.325
## Invulnerabilità dopo il rialzo.
@export var getup_invuln: int = 20
## Tick a terra prima di rialzarsi.
@export var down_ticks: int = 40
@export var ko_score: int = 500
## Larghezza dell'ombra in px.
@export var shadow_width: int = 33
@export_group("Intelligenza")
## Attacchi possibili, per id di AttackData, con il loro peso nella scelta.
@export var attacks: PackedStringArray = []
@export var attack_weights: PackedFloat32Array = []
## Distanza di attesa da GIG, minima e massima.
@export var wait_distance: Vector2 = Vector2(75.0, 112.5)
## Scostamento di profondità dalla corsia di GIG mentre aspetta.
@export var wait_lane_offset: Vector2 = Vector2(17.5, 32.5)
## Attesa fra due attacchi dello stesso nemico, minima e massima.
@export var cooldown_ticks: Vector2i = Vector2i(72, 120)
## Tick massimi di avvicinamento prima di rinunciare al turno d'attacco.
@export var approach_timeout: int = 150
