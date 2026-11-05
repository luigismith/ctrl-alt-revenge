class_name CombatSystem
extends RefCounted
## Risolve i colpi una volta per tick, dopo che tutti gli attori si sono mossi.
## Per ogni attaccante (in ordine di uid) e ogni bersaglio (in ordine di uid) controlla:
## squadra, colpo già dato da questa istanza d'attacco, tolleranza di profondità,
## invulnerabilità e stato del bersaglio, sovrapposizione fra hitbox e hurtbox (x e altezza).
## Poi applica il colpo: danno, hitstop, reazione, punti, suoni, effetti, tremolio.

## Il punto di contatto sopra questa altezza dai piedi dà la reazione "alta".
const HIGH_HIT_HEIGHT := 65.0

var level: Level
## Colpi applicati in questo tick: [uid attaccante, uid vittima, id attacco] (per test e debug).
var last_hits: Array[Array] = []


func _init(lvl: Level) -> void:
	level = lvl


func resolve() -> void:
	last_hits.clear()
	var targets := level.hittables()
	for a in level.fighters:
		if a.removed:
			continue
		var atk := a.current_hit_attack()
		if atk == null:
			continue
		var boxes := a.active_hitboxes()
		if boxes.is_empty():
			continue
		var a_team: Entity.Team = a.body_team if a.state == Fighter.State.THROWN else a.team
		for v in targets:
			if v == a or v.removed or a.hit_registry.has(v.uid):
				continue
			if v.team == a_team or (v.team == Entity.Team.NEUTRAL and a_team != Entity.Team.PLAYER):
				continue
			if absf(a.py - v.py) > atk.depth_tolerance:
				continue
			if not v.can_be_hit_by(a, atk):
				continue
			var overlap := _overlap(boxes, v.world_hurtboxes())
			if overlap.size.x < 0.0:
				continue
			apply_hit(a, v, atk, overlap.get_center(), 0)


## Primo rettangolo di sovrapposizione fra due elenchi di box (size.x < 0 se nessuna).
static func _overlap(a: Array[Rect2], b: Array[Rect2]) -> Rect2:
	for ra in a:
		for rb in b:
			if ra.intersects(rb):
				return ra.intersection(rb)
	return Rect2(0, 0, -1, -1)


## Applica un colpo deciso (anche dalle mosse a coppie, che non passano dalle box).
## `dir` = direzione della spinta; 0 = lontano dall'attaccante.
func apply_hit(a: Fighter, v: Entity, atk: AttackData, point: Vector2, dir: int) -> void:
	a.hit_registry[v.uid] = true
	if dir == 0:
		dir = 1 if v.px > a.px else (-1 if v.px < a.px else a.facing)
	var high := point.y < v.py - v.ph - HIGH_HIT_HEIGHT
	var by_player := a.team == Entity.Team.PLAYER or (a.state == Fighter.State.THROWN and a.body_team == Entity.Team.PLAYER)
	v.receive_hit(a, atk, HitInfo.new(point, dir, high))
	a.hitstop = maxi(a.hitstop, atk.hitstop_attacker)
	if a.state == Fighter.State.ATTACK or a is Gig:
		a.connected = true
	if a is Gig:
		(a as Gig).on_attack_connected(v)
	last_hits.append([a.uid, v.uid, String(atk.id)])
	if by_player:
		Game.add_score(atk.points)
		Game.count(StringName("hit_" + String(atk.id)))
		if v is Thug:
			level.on_enemy_hit(v as Thug)
	if level.sound_enabled and atk.sfx_hit != &"":
		Sfx.play_at(atk.sfx_hit, point.x)
	level.fx.spawn(atk.fx_hit, point.x, point.y, dir, v.depth_z(2) + 2)
	if atk.shake > 0.0:
		level.add_shake(atk.shake)
