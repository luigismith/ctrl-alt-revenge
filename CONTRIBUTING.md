# Contribuire

- **Codice** (GDScript, Python, shader, configurazione): è sotto licenza MIT. Aprendo una pull request concedi il tuo codice con la stessa licenza (Termini di servizio di GitHub, sezione D.6).
- **Asset**: grafica, musica, suoni, storia, personaggi e livelli non si accettano tramite pull request. Serve prima un accordo scritto separato, che secondo la stessa sezione D.6 prevale sulla licenza del repository.
- **Cosa non va mai nel repository**:
  - musica generata con Suno o altri media generati con AI;
  - master audio;
  - build del gioco;
  - asset di pack che vietano la ridistribuzione.

  Il controllo pre-commit blocca questi file. Attivalo una volta per ogni clone con `git config core.hooksPath tools/hooks`.
- **Pack di terze parti**: ognuno va in `game/assets/third_party/<pack>/` con:
  - un file `SOURCE.md`;
  - una tabella in `REUSE.toml`;
  - una riga in `THIRD-PARTY-NOTICES.md`.
