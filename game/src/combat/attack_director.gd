extends Node
## AttackDirector (autoload): dà il turno d'attacco a un solo nemico alla volta (§5).
## - Fra due attacchi nemici qualsiasi passano almeno 0,35 s (21 tick).
## - Fra due attacchi dello stesso nemico 0,6-1,0 s (cooldown_ticks nei dati del nemico): il recupero lo fissa il nemico con set_cooldown().
## Usa solo i tick della simulazione del livello: niente tempo reale, niente casualità propria.

const GLOBAL_GAP := 21

## uid del nemico che ha il turno (0 = nessuno).
var holder_uid: int = 0
var last_release_tick: int = -100000
var last_attack_start_tick: int = -100000
## Registro degli eventi [tick, uid, "grant" | "start" | "release"] per i test.
var events: Array[Array] = []
var keep_log: bool = false

var _cooldowns: Dictionary[int, int] = {}


func reset() -> void:
	holder_uid = 0
	last_release_tick = -100000
	last_attack_start_tick = -100000
	events.clear()
	_cooldowns.clear()


func can_request(thug: Entity, tick: int) -> bool:
	if holder_uid != 0 and holder_uid != thug.uid:
		return false
	if tick - last_release_tick < GLOBAL_GAP or tick - last_attack_start_tick < GLOBAL_GAP:
		return false
	return tick >= _cooldowns.get(thug.uid, -100000)


## Chiede il turno: true se concesso (o già posseduto).
func request(thug: Entity, tick: int) -> bool:
	if holder_uid == thug.uid:
		return true
	if not can_request(thug, tick):
		return false
	holder_uid = thug.uid
	_log(tick, thug.uid, "grant")
	return true


func release(thug: Entity, tick: int) -> void:
	if holder_uid != thug.uid:
		return
	holder_uid = 0
	last_release_tick = tick
	_log(tick, thug.uid, "release")


func on_attack_start(thug: Entity, tick: int) -> void:
	last_attack_start_tick = tick
	_log(tick, thug.uid, "start")


func set_cooldown(thug: Entity, until_tick: int) -> void:
	_cooldowns[thug.uid] = until_tick


func is_holder(thug: Entity) -> bool:
	return holder_uid == thug.uid


func forget(thug: Entity, tick: int) -> void:
	release(thug, tick)
	_cooldowns.erase(thug.uid)


func _log(tick: int, id: int, what: String) -> void:
	if keep_log:
		events.append([tick, id, what])
