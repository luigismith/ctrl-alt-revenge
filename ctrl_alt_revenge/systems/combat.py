# systems/combat.py — Gestione collisioni di combattimento
import pygame
from ctrl_alt_revenge.settings import KNOCKBACK_FORCE_X, KNOCKBACK_FORCE_Y


class CombatSystem:
    """Gestisce le collisioni tra hitbox e hurtbox."""

    def __init__(self):
        self.hit_effects = []  # lista di (x, y, timer) per effetti visivi

    def update(self, player, enemies, dt=1.0):
        """Controlla tutte le collisioni di combattimento."""
        # Attacchi del player contro i nemici
        if player.hitbox_active and player.alive:
            for enemy in enemies:
                if not enemy.alive or enemy.iframes > 0:
                    continue
                if getattr(enemy, "hacked_ally", False):
                    continue
                if player.hitbox_rect.colliderect(enemy.hurtbox_rect):
                    kb_dir = 1 if player.facing == 1 else -1
                    enemy.take_damage(
                        player.hitbox_damage,
                        kb_dir * KNOCKBACK_FORCE_X,
                        KNOCKBACK_FORCE_Y
                    )
                    self.hit_effects.append((
                        enemy.hurtbox_rect.centerx,
                        enemy.hurtbox_rect.centery,
                        10  # durata dell'effetto in frame
                    ))

        # Attacchi dei nemici contro il player
        if player.alive and player.iframes <= 0:
            for enemy in enemies:
                if not enemy.alive:
                    continue
                if getattr(enemy, "hacked_ally", False):
                    continue

                # Hitbox attacco nemico
                if enemy.hitbox_active:
                    if enemy.hitbox_rect.colliderect(player.hurtbox_rect):
                        if player.is_parrying:
                            # Parry riuscito!
                            player.parry_success = True
                            enemy.stun(30)
                            enemy.deactivate_hitbox()
                            self.hit_effects.append((
                                player.hurtbox_rect.centerx,
                                player.hurtbox_rect.centery,
                                15
                            ))
                        else:
                            kb_dir = 1 if enemy.facing == 1 else -1
                            player.take_damage(
                                enemy.hitbox_damage,
                                kb_dir * KNOCKBACK_FORCE_X,
                                KNOCKBACK_FORCE_Y
                            )
                            enemy.deactivate_hitbox()

                # Danno da contatto
                elif enemy.hurtbox_rect.colliderect(player.hurtbox_rect):
                    if not player.is_parrying:
                        kb_dir = 1 if enemy.x < player.x else -1
                        player.take_damage(
                            enemy.contact_damage,
                            kb_dir * KNOCKBACK_FORCE_X * 0.5,
                            KNOCKBACK_FORCE_Y * 0.5
                        )

                # Laser del drone
                if hasattr(enemy, "laser_active") and enemy.laser_active and enemy.laser_rect:
                    if enemy.laser_rect.colliderect(player.hurtbox_rect):
                        player.take_damage(1, 0, KNOCKBACK_FORCE_Y)

                # Shockwave del boss
                if hasattr(enemy, "shockwave_rects"):
                    for sw_rect in enemy.shockwave_rects:
                        if sw_rect.colliderect(player.hurtbox_rect):
                            kb_dir = 1 if sw_rect.centerx < player.x else -1
                            player.take_damage(1, kb_dir * KNOCKBACK_FORCE_X, KNOCKBACK_FORCE_Y)
                            break

        # Aggiorna effetti visivi
        self.hit_effects = [(x, y, t - dt) for x, y, t in self.hit_effects if t > 0]

    def draw_effects(self, surface, camera_offset, particle_sprites):
        """Disegna gli effetti di hit."""
        hit_sprite = particle_sprites.get("hit")
        if not hit_sprite:
            return
        for x, y, t in self.hit_effects:
            draw_x = int(x) + camera_offset[0] - hit_sprite.get_width() // 2
            draw_y = int(y) + camera_offset[1] - hit_sprite.get_height() // 2
            surface.blit(hit_sprite, (draw_x, draw_y))
