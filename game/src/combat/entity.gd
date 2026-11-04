class_name Entity
extends Node2D
## Qualcosa che vive nel mondo con le coordinate di pseudo-profondità del §3:
## px orizzontale, py linea dei piedi (profondità), ph altezza dal suolo.
## Lo sprite si disegna in (px, py − ph), l'ombra in (px, py).

enum Team { PLAYER, ENEMY, NEUTRAL }

## Identificativo crescente assegnato dal livello: decide l'ordine di aggiornamento e dei colpi.
var uid: int = 0
var team: Team = Team.NEUTRAL
var level: Level
var px: float = 0.0
var py: float = 0.0
var ph: float = 0.0
## Da togliere dal mondo alla fine del tick.
var removed: bool = false


## Un tick di simulazione.
func sim_tick() -> void:
	pass


## Aggiorna nodi e sprite dallo stato della simulazione (posizioni intere).
func sync_visual() -> void:
	pass


## Hurtbox nel piano (x, y dello schermo del mondo).
func world_hurtboxes() -> Array[Rect2]:
	return []


func can_be_hit_by(_attacker: Entity, _atk: AttackData) -> bool:
	return false


## Applica un colpo già deciso dal CombatSystem.
func receive_hit(_attacker: Entity, _atk: AttackData, _info: HitInfo) -> void:
	pass


## Larghezza dell'ombra in px (0 = nessuna ombra).
func shadow_width() -> int:
	return 0


## Ordine di disegno: per y crescente, a parità di y decide il bias.
func depth_z(bias: int = 0) -> int:
	return 100 + 2 * int(roundf(py)) + bias
