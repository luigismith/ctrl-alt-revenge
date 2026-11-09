class_name PowerUpDef
extends Resource
## Un power-up dei tratti platform (catalogo di car-mappe, 8 novembre 2026): uno alla volta, il nuovo
## sostituisce il vecchio. Dura un tempo, un numero di usi o di colpi, oppure agisce subito. I valori
## stanno in data/powerup/<tipo>.tres.

enum Durata { TEMPO, USI, COLPI, SUBITO }

@export var id: StringName
## Il nome sull'HUD quando lo si prende.
@export var label: String = ""
## La scritta che compare al posto del nome (l'abbonamento: «RINNOVATO»).
@export var pickup_text: String = ""
@export var color: Color = Color.WHITE
@export var durata: Durata = Durata.TEMPO
## TEMPO: i secondi; USI e COLPI: quanti.
@export var amount: float = 0.0
## Il tempo passa solo mentre si usa (l'ombrello: 10 s di planata, a pezzi).
@export var only_while_used: bool = false

@export_group("Effetti")
@export var immune_toxic: bool = false
@export var damage_mult: int = 1
@export var breaks_guard: bool = false
@export var absorbs_hits: bool = false
@export var invisible: bool = false
## Px/tick: la caduta più veloce mentre si plana tenendo SALTO (0 = niente planata).
@export var glide_fall: float = 0.0
@export var extra_life: int = 0
@export var max_lives: int = 3
## La bomboletta: quanto acceca Colombe e telecamere, quanto stordisce i nemici.
@export var blind_s: float = 0.0
@export var stun_s: float = 0.0


## Il valore iniziale del contatore: tick per il TEMPO, usi o colpi per gli altri.
func start_amount() -> int:
	if durata == Durata.TEMPO:
		return roundi(amount * 60.0)
	return roundi(amount)
