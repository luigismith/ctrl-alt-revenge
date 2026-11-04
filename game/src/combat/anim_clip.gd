class_name AnimClip
extends RefCounted
## Un'animazione: elenco di fotogrammi con la loro durata in tick.

var name: StringName = &""
var loop: bool = false
var frames: Array[AnimFrame] = []


func total_ticks() -> int:
	var t := 0
	for f in frames:
		t += f.ticks
	return t


func has_tag_anywhere(tag: int) -> bool:
	for f in frames:
		if f.has_tag(tag):
			return true
	return false


## Indici del primo e dell'ultimo fotogramma attivo, oppure (-1, -1).
func active_range() -> Vector2i:
	var first := -1
	var last := -1
	for i in frames.size():
		if frames[i].has_tag(AnimFrame.TAG_ACTIVE):
			if first < 0:
				first = i
			last = i
	return Vector2i(first, last)


## Tick di avvio, attivi e di recupero secondo i tag "active".
func segment_ticks() -> Vector3i:
	var r := active_range()
	if r.x < 0:
		return Vector3i(total_ticks(), 0, 0)
	var s := Vector3i.ZERO
	for i in frames.size():
		if i < r.x:
			s.x += frames[i].ticks
		elif i <= r.y:
			s.y += frames[i].ticks
		else:
			s.z += frames[i].ticks
	return s


## Portata massima in avanti delle hitbox attive (px dall'ancora), 0 se non ce ne sono.
func max_reach() -> int:
	var reach := 0
	# Il dx (passo in avanti) dei fotogrammi fino a quello attivo allunga la portata: il pugno del bruto
	# parte da più lontano e arriva con il passo.
	var moved := 0
	for f in frames:
		moved += f.dx
		if f.has_tag(AnimFrame.TAG_ACTIVE):
			for b in f.hit:
				reach = maxi(reach, b.position.x + b.size.x + moved)
	return reach


## Copia ritemporizzata: avvio, attivo e recupero durano esattamente i tick richiesti
## (i valori dell'AttackData vincono sui tick scritti nel JSON). Un segmento con più
## fotogrammi che tick tiene fotogrammi equidistanti e sposta eventi e dx su quelli tenuti.
## Con recovery < 0 i fotogrammi dopo l'attivo restano com'erano (mosse in aria).
## Con active = 0 e nessun fotogramma "active" (la proiezione) non si perde nessun fotogramma:
## l'avvio sono quelli che nel JSON iniziano prima della quota startup / (startup + recovery)
## della durata, il recupero tutti gli altri.
func retimed(startup: int, active: int, recovery: int) -> AnimClip:
	var c := AnimClip.new()
	c.name = name
	c.loop = false
	if frames.is_empty():
		return c
	var r := active_range()
	var src: Array[AnimFrame] = []
	for f in frames:
		src.append(f.copy())
	if r.x < 0 and active <= 0:
		var split := _split_index(startup, maxi(recovery, 0))
		c.frames.append_array(_distribute(src.slice(0, split), startup))
		if recovery < 0:
			c.frames.append_array(src.slice(split))
		else:
			c.frames.append_array(_distribute(src.slice(split), recovery))
		return c
	if r.x < 0:
		# Nessun fotogramma attivo: quello centrale diventa attivo.
		var mid := src.size() >> 1
		src[mid].tags |= AnimFrame.TAG_ACTIVE
		r = Vector2i(mid, mid)
	var seg_startup: Array[AnimFrame] = src.slice(0, r.x)
	var seg_active: Array[AnimFrame] = src.slice(r.x, r.y + 1)
	var seg_recovery: Array[AnimFrame] = src.slice(r.y + 1)
	if seg_startup.is_empty() and startup > 0:
		seg_startup.append(_inactive_copy(seg_active[0]))
	if seg_recovery.is_empty() and recovery > 0:
		seg_recovery.append(_inactive_copy(seg_active[seg_active.size() - 1]))
	c.frames.append_array(_distribute(seg_startup, startup))
	c.frames.append_array(_distribute(seg_active, active))
	if recovery < 0:
		c.frames.append_array(seg_recovery)
	else:
		c.frames.append_array(_distribute(seg_recovery, recovery))
	return c


## Indice del primo fotogramma del recupero per una mossa senza fotogrammi attivi: il primo che
## nel JSON inizia alla quota startup / (startup + recovery) della durata o dopo. Almeno un
## fotogramma per segmento, se il segmento ha tick.
func _split_index(startup: int, recovery: int) -> int:
	var n := frames.size()
	var boundary := float(total_ticks()) * startup / maxf(1.0, float(startup + recovery))
	var split := n
	var t := 0
	for i in n:
		if float(t) >= boundary - 0.001:
			split = i
			break
		t += frames[i].ticks
	if startup > 0:
		split = maxi(split, 1)
	if recovery > 0:
		split = mini(split, n - 1)
	return clampi(split, 0, n)


static func _inactive_copy(f: AnimFrame) -> AnimFrame:
	var g := f.copy()
	g.tags &= ~(AnimFrame.TAG_ACTIVE | AnimFrame.TAG_CANCEL)
	g.hit = []
	g.events = PackedStringArray()
	g.dx = 0
	return g


## Distribuisce `total` tick sui fotogrammi in proporzione alla durata originale (almeno 1 ciascuno).
static func _distribute(seg: Array[AnimFrame], total: int) -> Array[AnimFrame]:
	var out: Array[AnimFrame] = []
	if total <= 0 or seg.is_empty():
		return out
	var n := seg.size()
	if total < n:
		# Tiene `total` fotogrammi equidistanti; eventi e dx dei saltati passano al successivo tenuto.
		var pending_events := PackedStringArray()
		var pending_dx := 0
		var keep := {}
		for k in total:
			keep[int(floor(float(k) * n / total))] = true
		for i in n:
			if keep.has(i):
				var f := seg[i]
				var merged := pending_events.duplicate()
				merged.append_array(f.events)
				f.events = merged
				f.dx += pending_dx
				pending_events = PackedStringArray()
				pending_dx = 0
				f.ticks = 1
				out.append(f)
			else:
				pending_events.append_array(seg[i].events)
				pending_dx += seg[i].dx
		if not out.is_empty():
			out[out.size() - 1].events.append_array(pending_events)
			out[out.size() - 1].dx += pending_dx
		return out
	# Metodo del resto più grande: ogni fotogramma ha almeno 1 tick, il resto in proporzione.
	var weights := 0
	for f in seg:
		weights += maxi(f.ticks, 1)
	var spare := total - n
	var given := 0
	var remainders: Array[Vector2] = []
	for i in n:
		var share := float(spare) * maxi(seg[i].ticks, 1) / weights
		var whole := int(floor(share))
		seg[i].ticks = 1 + whole
		given += whole
		remainders.append(Vector2(share - whole, -i))
	remainders.sort()
	remainders.reverse()
	var k := 0
	while given < spare:
		seg[int(-remainders[k].y)].ticks += 1
		given += 1
		k += 1
	out.append_array(seg)
	return out
