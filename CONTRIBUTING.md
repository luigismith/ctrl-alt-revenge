# Contribuire

- **Codice** (GDScript, Python, shader, configurazione): è sotto licenza MIT, tranne gli script per Blender in `tools/blender/`, che sono GPL-3.0-or-later. Aprendo una pull request concedi il tuo codice con la licenza della cartella in cui lo metti (Termini di servizio di GitHub, sezione D.6; vedi `REUSE.toml`).
- **Asset**: grafica, musica, suoni, storia, personaggi e livelli non si accettano tramite pull request. Serve prima un accordo scritto separato, che secondo la stessa sezione D.6 prevale sulla licenza del repository.
- **Cosa non va mai nel repository**:
  - musica, voci e master audio;
  - video con la musica, come il trailer;
  - gli originali delle immagini generate con AI: entra solo la pixel art che ne deriva;
  - la storia privata e le battute delle scene;
  - build del gioco e la cache di importazione di Godot (`.godot/`);
  - asset di pack che vietano la ridistribuzione.

  Il controllo pre-commit blocca l’audio (tranne gli effetti sonori ammessi in `tools/public_audio_allowlist.txt`), le cartelle private, la storia e le battute, la cache `.godot/` e i file oltre 20 MB; il resto si controlla a mano. Il controllo si attiva una volta per ogni clone con `git config core.hooksPath tools/hooks`.
- **Pack di terze parti**: ognuno va in `game/assets/third_party/<pack>/` con:
  - un file `SOURCE.md`;
  - una tabella in `REUSE.toml`;
  - una riga in `THIRD-PARTY-NOTICES.md`.
