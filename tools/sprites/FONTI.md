# Fonti esterne della pipeline dei personaggi

I file elencati qui stanno nel laboratorio (`%USERPROFILE%\ctrlaltrevenge-lab\sources\`), non nel repository. Crediti e licenze per il pubblico sono in `THIRD-PARTY-NOTICES.md`; qui resta la prova della verifica.

## Fonti verificate (3 novembre 2026)

Licenza controllata alla fonte (pagina del pack) e nel file di licenza dentro l'archivio.

| Fonte | URL | Licenza | File usati (nel laboratorio) | sha256 |
|---|---|---|---|---|
| Quaternius Universal Base Characters (Standard) | https://quaternius.com/packs/universalbasecharacters.html | CC0 1.0 (pagina: "CC0 License"; `License_Standard.txt`) | archivio `Universal Base Characters[Standard].zip` (128 968 391 byte) | `fdbf1804c90dfc1ea03e992bff7da2dfd1a79318e13270a660180f9308455f40` |
| | | | `Superhero_Male_FullBody.gltf` | `e7fcea214ecf8855afbf910b50de6f9c7d1decfb71ca28bad8a4481452dafeb4` |
| | | | `Superhero_Male_FullBody.bin` | `459003f9745853ae562a85506a2b94dd56515c1f37728f9fa3d2ce1a3e4cd92f` |
| | | | `Hair_Buzzed.gltf` / `.bin` | `6e709c691d4feccda9788df917bf9604e751f02da21cee2bc81bcc3d26b3b580` / `5d4b5452ff879ed1d516694be57d1106c070c7133e747a8c9432b01ebf20e908` |
| | | | `Hair_Beard.gltf` / `.bin` | `80013b9791ce12c65fbe693cf669b02ef5c38091c653bf13b9415d2d8380e0ce` / `bf2f46ef5808665ef31082f787bc68c51ff063e81b76ca1a51ac86a9ae723be7` |
| Quaternius Universal Animation Library (Standard) | https://quaternius.com/packs/universalanimationlibrary.html | CC0 1.0 (pagina: "CC0 License"; `License.txt`) | archivio `universal_animation_librarystandard.zip` (14 541 205 byte) | `18ff1a7215f4852b320203e8aaf02a1578b5c8eef9027fbaedfcedc7b85a3ac2` |
| | | | `Unreal Engine/AL_Standard.fbx` | `c836c5d47de2a414818f7644632ac43aa84475df6709f4514b9410d232800fd9` |
| Quaternius Universal Animation Library 2 (Standard) | https://quaternius.com/packs/universalanimationlibrary2.html | CC0 1.0 (pagina: "CC0 License"; `License.txt`) | archivio `universal_animation_library_2standard.zip` (10 257 419 byte) | `ec0e40d6d78fe9aaad59e322f40865a8675c22f0745e291622e54520391a9217` |
| | | | `Unreal-Godot/UAL2_Standard.glb` | `0815dd05531cae9bc313fc9c0ba81330bc72f8e19ec45f73738e74ddc5796a43` |
| Mesh2Motion (animazioni) | https://github.com/Mesh2Motion/mesh2motion-app/blob/main/LICENSE-CC0.MD | CC0 1.0 ("All 3d models, blend files, rigs, animations") | `kick-roundhouse.glb`, `kick-front.glb` | `673397db0ad14c8b356235fbcc80e7fc657623fd6cf1e8474686234f2627e3e8`, `bea482aeed8dda0c24e70e9730d21c787518f8d66399b34cb7a5a5a7f6a6e6f6` |
| | | | dump JSON delle pose (`spike-out/m2m_json/kick-roundhouse.json`, `kick-front.json`) | `3f4e83ea07d7757b7a2eaed7f9ef2ef0fa41bdaccd085054475ee0d3de2a3398`, `3d7884a79e78369b4a15c00a94110bc1da0ec64465354f3afbbffff9f864e73e` |

Le clip UAL usate: Punch_Jab, Punch_Cross, Walk_Loop, Sprint_Loop, Hit_Head, Hit_Chest, Idle_Loop, Crouch_Idle_Loop, Crouch_Fwd_Loop (UAL1); Melee_Hook, Melee_Hook_Rec, Hit_Knockback, LayToIdle, NinjaJump_Start, NinjaJump_Land, ClimbUp_1m_RM, Slide_Start (UAL2). Dalla Mesh2Motion: kick-roundhouse (calcio finale di GIG). Tutte dalla versione Standard gratuita: le clip delle versioni Pro e Source (a pagamento, anche se CC0) non si usano.

Pipeline v7 (4 novembre 2026): le pose chiave e i tempi delle mosse scritte sono in `tools/blender/char_anim.py` (nostri); stivali (`char_boots.py`), codino con la molla e timbri del viso (`tools/sprites/pix_v7.py`) sono geometria e disegno procedurale nostri. La prova che ha portato alla v7, con le licenze verificate degli strumenti valutati e scartati (Cascadeur, mocap da video, librerie non commerciali), è nel laboratorio: `spike-sprite-v7/LEGGIMI.md`.

Figura nuova di GIG e cel shading (4 novembre 2026): nessuna fonte nuova. Proporzioni, spinte della mesh e vestiti stanno in `tools/sprites/chars/gig.json` e `tools/blender/char_build.py`; il cel (toni per materiale, contatti, normali lisciate, tavolozza "a ruoli") in `tools/sprites/pixelize.py` e `pix_v7.py`: tutto codice nostro. Le prove, con i giudizi ciechi e le misure, sono nel laboratorio: `prove-gig-figura/LEGGIMI.md` e `prove-cel-shading/LEGGIMI.md`.
