class_name View
extends RefCounted
## La risoluzione interna del gioco, in un posto solo. Deve coincidere con
## display/window/size/viewport_* in project.godot (lo controlla un test).
##
## Il 5 novembre 2026 Luigi ha chiesto più dettaglio: da 384×216 a 480×270, con tutto più
## grande del 25% (60 px per metro invece di 48). Su un monitor 1080p sono pixel ×4.

const W := 480
const H := 270
const SIZE := Vector2(W, H)
const SIZE_I := Vector2i(W, H)
const CX := W / 2
## Pixel per metro, come gli sprite (tools/sprites/camera.json).
const PPM := 60
