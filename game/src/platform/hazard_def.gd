class_name HazardDef
extends Resource
## Un tipo di zona tossica (catalogo di car-mappe, 8 novembre 2026). Il danno è in energia al
## secondo e arriva dopo un ritardo di permanenza continua, così chi passa svelto non paga. Nessuna
## zona uccide al primo tocco. I valori stanno in data/tossiche/<tipo>.tres; i campi della zona LDtk
## `Tossica` li possono cambiare.

@export var id: StringName
@export var label: String = ""
@export var color: Color = Color.RED
@export var damage_s: float = 2.0
@export var delay_s: float = 0.0
## 0 = sempre attiva; altrimenti la zona è accesa per `active_s` secondi ogni `cycle_s`.
@export var cycle_s: float = 0.0
@export var active_s: float = 0.0
## La corsa in percentuale, dentro la zona (i fanghi: GIG cammina piano).
@export var speed_pct: int = 100
## L'energia sotto cui la zona non porta (i fanghi non uccidono da soli).
@export var min_energy: int = 0
