class_name AttackData
extends Resource
## Dati di una mossa (§5 della specifica), salvati in game/data/attacks/*.tres.
## Tempi in tick a 60 Hz, distanze in px del mondo.

enum Weight { LIGHT, MEDIUM, HEAVY }

@export var id: StringName = &""
## Animazione dello sprite che la mossa usa.
@export var anim: StringName = &""
@export_group("Tempi")
@export var startup: int = 3
@export var active: int = 2
## Per air_kick è il recupero all'atterraggio.
@export var recovery: int = 9
@export_group("Effetto")
@export var damage: int = 4
@export var hitstop_attacker: int = 5
@export var hitstop_victim: int = 7
## Tick di stordimento della vittima dopo l'hitstop (0 = nessuno).
@export var stun: int = 14
## Peso del colpo: l'armatura del bruto regge solo i colpi LIGHT.
@export var weight: Weight = Weight.LIGHT
@export var knockdown: bool = false
## Lancio in px/s: x in avanti, y verso l'alto. Zero = valori di base dell'atterramento.
@export var launch: Vector2 = Vector2.ZERO
## Gravità del lancio in px/s².
@export var launch_gravity: float = 900.0
## Spinta all'indietro per i colpi che non atterrano, in px.
@export var push: float = 6.0
@export var juggle_cost: int = 1
## Tolleranza di profondità: ±10 per GIG, ±8 per i nemici.
@export var depth_tolerance: float = 10.0
@export var points: int = 10
## Trauma aggiunto alla telecamera (0-1): solo colpi pesanti, KO e proiezioni.
@export var shake: float = 0.0
@export_group("Suoni ed effetti")
## Suono all'avvio, se l'animazione non ne ha già uno.
@export var sfx_whoosh: StringName = &""
@export var sfx_hit: StringName = &"hit_light"
@export var fx_hit: StringName = &"hit_spark_light"
@export_group("Varie")
## Mossa in aria: il recupero si fa all'atterraggio e i fotogrammi dopo l'attivo restano com'erano.
@export var air: bool = false
## Tick dell'avvio in cui scatta il lampo (glint), se l'animazione non lo ha già; -1 = nessuno.
@export var glint_tick: int = -1
## L'avvio ha armatura (non si interrompe con i colpi leggeri).
@export var armor: bool = false
## Hitbox da usare se il fotogramma attivo non ne ha.
@export var hitbox: Rect2i = Rect2i(12, -70, 24, 12)


func total_ticks() -> int:
	return startup + active + recovery


func is_light() -> bool:
	return weight == Weight.LIGHT and not knockdown
