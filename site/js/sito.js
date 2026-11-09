/*
	CTRL+ALT REVENGE! · sito
	SPDX-FileCopyrightText: 2026 Luigi Massari
	SPDX-License-Identifier: MIT

	Niente dipendenze, niente cookie, niente richieste fuori dal sito. Che cosa fa:
	- movimento: rispetta prefers-reduced-motion, e un pulsante solo ferma tutto (la scelta iniziale la fa
	  scala.js, nel <head>, prima del primo disegno);
	- scale intere: ogni pixel del gioco è un numero intero di pixel del dispositivo, anche con lo schermo al 125%,
	  e CAR Pixel va a multipli di 12 pixel del dispositivo (i conti di base li fa scala.js, qui si rifanno);
	- la nube rossa sopra i tetti e la polvere del maestrale, retinate con la matrice di Bayer, a semi fissi;
	- il video del gioco, che sfuma a scacchi nella notte e parte solo quando si vede (e non con «Risparmio dati»);
	- il teaser, che non scarica niente prima del clic e parte con la musica dal pulsante d'oro;
	- i cartelloni della storia, dipinti a spruzzo su un muro: su schermi larghi la telecamera scorre lungo il muro;
	- i tre tasti del riavvio, la strada in cui GIG cammina, gli sprite veri con i loro tempi;
	- i tasti dei comandi che si accendono, la luce provata con la normal map di GIG, il CONTINUA? della 404.
	A ogni fotogramma prima si legge (scorrimento, posizioni) e poi si scrive: niente impaginazioni forzate.
*/
'use strict';
(() => {
	const doc = document.documentElement;
	const script = document.currentScript;
	const BASE = new URL('..', script ? script.src : location.href).href;
	const $ = (s, r = document) => r.querySelector(s);
	const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
	const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
	const css = (el, k, v) => el && el.style.setProperty(k, v);
	const memoria = {
		get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
		set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* modalità privata: pazienza */ } },
	};
	const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map((v) => (v + 0.5) / 16);
	const hex = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
	function mulberry32(a) {
		return function () {
			a |= 0; a = (a + 0x6D2B79F5) | 0;
			let t = Math.imul(a ^ (a >>> 15), 1 | a);
			t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
			return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
		};
	}

	/* ------------------------------------------------------------ chi guarda che cosa */
	const visibile = new WeakMap();
	const quandoCambia = new WeakMap();
	const osserva = (() => {
		if (!('IntersectionObserver' in window)) return (el, cb) => { visibile.set(el, true); if (cb) setTimeout(cb, 0); };
		const io = new IntersectionObserver((ee) => {
			for (const e of ee) {
				visibile.set(e.target, e.isIntersecting);
				const cb = quandoCambia.get(e.target);
				if (cb) cb();
			}
			richiedi();
		}, { rootMargin: '120px 0px' });
		return (el, cb) => { if (el) { visibile.set(el, false); if (cb) quandoCambia.set(el, cb); io.observe(el); } };
	})();
	const vede = (el) => !!el && visibile.get(el) !== false;

	/* ------------------------------------------------------------ movimento */
	const ridotto = matchMedia('(prefers-reduced-motion: reduce)');
	let moto = doc.dataset.movimento !== 'no';
	const bottoneMoto = $('.moto');
	function impostaMovimento(v, salva) {
		moto = v;
		doc.dataset.movimento = v ? 'si' : 'no';
		if (bottoneMoto) {
			// Il nome resta «Animazioni»: lo stato lo dicono aria-pressed e la spia (la scritta «: sì» è solo per gli occhi).
			const stato = v ? bottoneMoto.dataset.si : bottoneMoto.dataset.no;
			bottoneMoto.setAttribute('aria-pressed', String(v));
			const s = $('.moto__stato', bottoneMoto);
			if (s) s.textContent = stato;
			bottoneMoto.title = (bottoneMoto.dataset.nome || '') + stato;
		}
		if (salva) memoria.set('car-movimento', v ? 'si' : 'no');
		if (!v) {
			polvere.pulisci();
			css(nube.el, '--par-nube', '0px');
			css(tettiEroe, '--par-tetti', '0px');
		}
		aggiornaVideo();
		impagina();
	}

	/* ------------------------------------------------------------ scale intere */
	const S = { dpr: 1, u: 1, vw: doc.clientWidth, vh: window.innerHeight, largo: true, margine: 72, hud: 84,
		nw: 2, nl: 2, nc: 3, ns: 2, ni: 2, nh: 2, nm: 2, nr: 3, nx: 3 };
	function calcolaScale() {
		if (window.carScala) Object.assign(S, window.carScala());
		const dpr = S.dpr;
		const vicino = (c) => Math.max(1, Math.round(c * dpr));
		// Prima si leggono tutte le misure, poi si scrive.
		const scatole = $$('.schermate').map((box) => ({ imgs: $$('img', box), W: box.clientWidth }));
		const ui = $$('[data-pixel-w]');
		const Wui = S.vw - 2 * Math.max(20, S.margine);
		// Le schermate di un pilastro stanno in fila alla scala intera più grande che ci sta; se in fila
		// diventerebbero più piccole di un pixel CSS per pixel del gioco, vanno a capo, tutte alla stessa scala.
		for (const { imgs, W } of scatole) {
			const larghe = imgs.map((i) => Number(i.getAttribute('width')));
			const somma = larghe.reduce((a, b) => a + b, 0);
			const fila = Math.floor(((W - 18 * (imgs.length - 1)) * dpr) / somma);
			const k = fila >= Math.round(dpr) ? Math.min(vicino(2), fila)
				: Math.max(1, Math.min(vicino(2), ...larghe.map((w) => Math.floor((W * dpr) / w))));
			for (const i of imgs) css(i, '--pq', k / dpr + 'px');
		}
		// Le scritte dell'interfaccia (ZONA LIBERATA, il logo e il CONTINUA? della 404) stanno alla loro scala;
		// se non ci stanno, alla scala intera più grande che ci sta: mai schiacciate.
		for (const el of ui) {
			const voluta = S[el.dataset.pixelScala || 'ni'] || 1;
			const k = Math.max(1, Math.min(voluta, Math.floor((Wui * dpr) / Number(el.dataset.pixelW))));
			css(el, '--pz', k / dpr + 'px');
		}
	}
	const px = (game, n) => (game * n) / S.dpr;
	const aggancia = (cssPx) => Math.round(cssPx * S.dpr) / S.dpr;

	/* ------------------------------------------------------------ nube rossa (canvas) */
	const NUBE = ['#0d060b', '#170913', '#210e1b', '#2d1325', '#221121', '#2c1024', '#3e142c', '#561a36', '#722240', '#8f2c4a'].map(hex);
	const TW = 256, TH = 64;
	function rumore(W, H, celle, seme) {
		const r = mulberry32(seme);
		const cx = celle, cy = Math.max(2, Math.round((celle * H) / W));
		const lat = new Float32Array(cx * cy);
		for (let i = 0; i < lat.length; i++) lat[i] = r();
		const out = new Float32Array(W * H);
		const liscia = (t) => t * t * (3 - 2 * t);
		for (let y = 0; y < H; y++) {
			const fy = (y / H) * cy, y0 = Math.floor(fy), ty = liscia(fy - y0), y1 = (y0 + 1) % cy;
			for (let x = 0; x < W; x++) {
				const fx = (x / W) * cx, x0 = Math.floor(fx), tx = liscia(fx - x0), x1 = (x0 + 1) % cx;
				const a = lat[y0 * cx + x0], b = lat[y0 * cx + x1], c = lat[y1 * cx + x0], d = lat[y1 * cx + x1];
				const ab = a + (b - a) * tx, cd = c + (d - c) * tx;
				out[y * W + x] = ab + (cd - ab) * ty;
			}
		}
		return out;
	}
	let TEX = null;
	function tessitura() {
		if (TEX) return TEX;
		const a = rumore(TW, TH, 8, 2087), b = rumore(TW, TH, 16, 417), c = rumore(TW, TH, 32, 15);
		TEX = new Float32Array(TW * TH);
		for (let i = 0; i < TEX.length; i++) TEX[i] = a[i] * 0.55 + b[i] * 0.3 + c[i] * 0.15;
		return TEX;
	}
	// Disegna la nube in un canvas a celle di `passo` pixel del gioco: `righe` (in celle) è dove la nube tocca i tetti.
	// `dopo` può aggiungere qualcosa (le cupole del primo cartellone) prima che l'immagine vada sul canvas.
	function disegnaNube(ctx, img, W, H, righe, o1, o2, passo = 1, dopo = null) {
		const T = tessitura();
		const d = img.data, R = NUBE.length - 1;
		let p = 0;
		for (let y = 0; y < H; y++) {
			let g = y / righe;
			if (g > 1) g = Math.max(0, 1 - (g - 1) * 1.6);
			const base = g * g * 1.05 - 0.2;
			const yg = y * passo;
			const r1 = ((Math.floor(yg * 0.85) % TH) + TH) % TH * TW;
			const r2 = ((Math.floor(yg * 1.7 + 23) % TH) + TH) % TH * TW;
			const by = (y & 3) * 4;
			for (let x = 0; x < W; x++) {
				const xg = x * passo;
				const nn = T[r1 + ((xg + o1) & 255)] * 0.62 + T[r2 + ((xg * 2 + o2) & 255)] * 0.38;
				let i = base + (nn - 0.48) * (0.6 + g * 1.3);
				i = i < 0 ? 0 : i > 0.999 ? 0.999 : i;
				let k = Math.floor(i * R + BAYER[by + (x & 3)]);
				if (k > R) k = R;
				const c = NUBE[k];
				d[p] = c[0]; d[p + 1] = c[1]; d[p + 2] = c[2]; d[p + 3] = 255;
				p += 4;
			}
		}
		if (dopo) dopo(d, W, H);
		ctx.putImageData(img, 0, 0);
	}
	const nube = {
		el: $('.eroe__nube'), ctx: null, img: null, W: 0, H: 0, righe: 1, chiave: '', passo: 1,
		misura(larghezza, altezza, cielo) {
			if (!this.el) return;
			const pw = px(1, S.nw);
			// Sui telefoni le celle della nube sono di 2-3 pixel del gioco: costa un decimo e la nube resta quella.
			this.passo = Math.max(1, Math.ceil(larghezza / pw / (S.largo ? 800 : 320)));
			const pc = pw * this.passo;
			this.W = Math.ceil(larghezza / pc) + 1;
			this.H = Math.ceil(altezza / pc) + 1;
			this.righe = Math.max(8, cielo / pc);
			this.el.width = this.W; this.el.height = this.H;
			this.el.style.width = this.W * pc + 'px';
			this.el.style.height = this.H * pc + 'px';
			this.ctx = this.el.getContext('2d', { alpha: false });
			this.img = this.ctx.createImageData(this.W, this.H);
			this.chiave = '';
		},
		disegna(tempo) {
			if (!this.ctx) return;
			// Tre volte al secondo bastano: la nube si muove piano. Lo scorrimento lo fa translate3d, senza ridisegnare.
			const o1 = Math.floor(tempo * 1.1), o2 = Math.floor(tempo * 2.05);
			const chiave = o1 + ':' + o2;
			if (chiave === this.chiave) return;
			this.chiave = chiave;
			disegnaNube(this.ctx, this.img, this.W, this.H, this.righe, o1, o2, this.passo);
		},
	};
	// Le cupole bianche di SIDERA sopra la vecchia fabbrica (ci sono dal 2041), con la patina rossa della nube.
	const CUPOLE = [[34, 76, 30, 25], [94, 78, 38, 31], [146, 76, 20, 15]];          // centro x, base, raggio, altezza
	const BIANCO_SPORCO = ['#d9cdd2', '#b9a3ad', '#8f7b8c', '#5e4d63', '#3a2c44'].map(hex);
	function cupole(d, W, H) {
		for (const [cx, base, r, h] of CUPOLE) {
			for (let x = Math.max(0, cx - r); x <= Math.min(W - 1, cx + r); x++) {
				const u = (x - cx) / r;
				const top = Math.round(base - h * Math.sqrt(Math.max(0, 1 - u * u)));
				for (let y = Math.max(0, top); y <= Math.min(H - 1, base); y++) {
					// luce da sinistra, in alto: più scure verso destra e verso la base; il bordo è il più scuro
					const v = (y - top) / Math.max(1, base - top);
					let t = 0.35 + u * 0.38 + v * 0.42;
					if (y === top) t += 0.35;
					const k = clamp(Math.floor(t * 4 + BAYER[(y & 3) * 4 + (x & 3)] - 0.5), 0, BIANCO_SPORCO.length - 1);
					const c = BIANCO_SPORCO[k], p = (y * W + x) * 4;
					d[p] = c[0]; d[p + 1] = c[1]; d[p + 2] = c[2];
				}
			}
		}
	}
	// la nube dipinta del primo cartellone: la stessa nube, ferma o quasi, con le cupole
	const arteNube = {
		el: $('.arte-nube'), ctx: null, img: null, chiave: '',
		disegna(tempo) {
			if (!this.el) return;
			if (!this.ctx) { this.ctx = this.el.getContext('2d', { alpha: false }); this.img = this.ctx.createImageData(this.el.width, this.el.height); }
			const o1 = 40 + Math.floor(tempo * 1.2), o2 = 90 + Math.floor(tempo * 2.1);
			const chiave = o1 + ':' + o2;
			if (chiave === this.chiave) return;
			this.chiave = chiave;
			disegnaNube(this.ctx, this.img, this.el.width, this.el.height, this.el.height * 0.66, o1, o2, 1, cupole);
		},
	};

	/* ------------------------------------------------------------ polvere del maestrale */
	const polvere = {
		el: $('.polvere'), ctx: null, W: 0, H: 0, parti: [], tempo: 0, pari: false,
		COLORI: ['#3e142c', '#5c3023', '#77402b', '#93553a', '#b8663a'],
		misura() {
			if (!this.el) return;
			// sui telefoni granelli di 2-3 pixel del gioco: meno pixel da disegnare, lo stesso vento
			const passo = S.largo ? 1 : Math.max(1, Math.ceil((S.vw * S.dpr) / Math.max(1, S.nw) / 320));
			const pd = px(1, Math.max(1, S.nw)) * passo;
			this.W = Math.ceil(S.vw / pd);
			this.H = Math.ceil(S.vh / pd);
			this.el.width = this.W; this.el.height = this.H;
			this.el.style.width = this.W * pd + 'px';
			this.el.style.height = this.H * pd + 'px';
			this.ctx = this.el.getContext('2d');
			const r = mulberry32(1704);
			const quante = Math.round((this.W * this.H) / 760);
			this.parti = Array.from({ length: quante }, () => ({ x: r() * this.W, y: r() * this.H, z: 0.3 + r() * 0.7, f: r() * 6.283 }));
			this.caso = mulberry32(417);
		},
		vento(t) {
			const g = Math.max(0, Math.sin(t * 0.55) * Math.sin(t * 0.21 + 2.1));
			return 0.55 + 2.2 * g * g;   // raffiche di maestrale
		},
		passo(dt) {
			if (!this.ctx || !moto) return;
			this.tempo += dt / 1000;
			this.pari = !this.pari;
			if (this.pari) return;          // 30 al secondo bastano, al ritmo della pixel art
			const s = (dt * 2) / 1000;
			const { W, H, ctx } = this;
			ctx.clearRect(0, 0, W, H);
			const v = this.vento(this.tempo);
			for (const p of this.parti) {
				p.x += (9 + 30 * p.z) * v * s;
				p.y += (Math.sin(this.tempo * 1.7 + p.f) * 5 * p.z + 2.5) * s;
				if (p.x > W + 3) { p.x -= W + 6; p.y = this.caso() * H; }
				if (p.y > H + 3) { p.y -= H + 6; p.x = this.caso() * W; }
				ctx.fillStyle = this.COLORI[Math.min(this.COLORI.length - 1, Math.floor(p.z * this.COLORI.length))];
				// granelli tirati dal vento: quelli vicini sono strisce orizzontali, più lunghe nelle raffiche
				ctx.fillRect(p.x | 0, p.y | 0, 1 + (p.z > 0.5 ? 1 : 0) + (v > 1.5 && p.z > 0.7 ? 1 : 0), 1);
			}
		},
		pulisci() { if (this.ctx) this.ctx.clearRect(0, 0, this.W, this.H); },
	};

	/* ------------------------------------------------------------ eroe: video, maschere, parallasse */
	const eroe = $('.eroe');
	const cielo = $('.eroe__cielo');
	const figura = $('.eroe__gioco');
	const tettiEroe = $('.eroe__tetti');
	const video = $('.eroe__video');
	const risparmio = !!(navigator.connection && navigator.connection.saveData);
	function aggiornaVideo() {
		if (!video) return;
		const deve = moto && !risparmio && vede(video) && !document.hidden;
		if (deve && video.paused) {
			const p = video.play();
			if (p && p.catch) p.catch(() => { /* il browser non vuole: resta il poster */ });
		} else if (!deve && !video.paused) video.pause();
	}
	// Maschera a scacchi (retino di Bayer) calcolata a 1x e ingrandita: il video sfuma nella notte.
	function ingrandisci(piccolo, n) {
		const grande = document.createElement('canvas');
		grande.width = piccolo.width * n; grande.height = piccolo.height * n;
		const g = grande.getContext('2d');
		g.imageSmoothingEnabled = false;
		g.drawImage(piccolo, 0, 0, grande.width, grande.height);
		return grande.toDataURL('image/png');
	}
	function maschera(wg, hg, n, { alto = 0, basso = 0, lato = 0, latoDa = 0 } = {}) {
		const piccolo = document.createElement('canvas');
		piccolo.width = wg; piccolo.height = hg;
		const c = piccolo.getContext('2d');
		const img = c.createImageData(wg, hg);
		const d = img.data;
		for (let y = 0; y < hg; y++) {
			for (let x = 0; x < wg; x++) {
				let a = 1;
				if (alto && y < alto) a = Math.min(a, (y + 0.5) / alto);
				if (basso && y >= hg - basso) a = Math.min(a, (hg - y - 0.5) / basso);
				if (lato && y >= latoDa) {
					if (x < lato) a = Math.min(a, (x + 0.5) / lato);
					if (x >= wg - lato) a = Math.min(a, (wg - x - 0.5) / lato);
				}
				d[(y * wg + x) * 4 + 3] = a > BAYER[(y & 3) * 4 + (x & 3)] ? 255 : 0;
			}
		}
		c.putImageData(img, 0, 0);
		return ingrandisci(piccolo, n);
	}
	let mascheraChiave = '', tettiChiave = '', limiteNube = 0, limiteTetti = 0;
	function impaginaEroe() {
		if (!eroe || !figura || !video) return;
		const pw = px(1, S.nw);
		const re = eroe.getBoundingClientRect();
		const rv = video.getBoundingClientRect();
		const alto = rv.top - re.top;
		nube.misura(re.width, re.height, alto - 45 * pw);
		// La parallasse non porta mai la fascia rossa sotto i tetti; sui telefoni la nube sta ferma.
		limiteNube = S.largo ? 38 * pw : 0;
		limiteTetti = S.largo ? 30 * pw : 0;
		const chiave = S.nw + ':' + S.dpr;
		if (tettiChiave !== chiave) {
			tettiChiave = chiave;
			if (tettiEroe) {
				css(tettiEroe, '--maschera-tetti', `url("${maschera(4, 175, S.nw, { basso: 55 })}")`);
				css(tettiEroe, '--maschera-tetti-w', px(4, S.nw) + 'px');
			}
			// in fondo all'eroe la nube sfuma a scacchi nella notte, come il video
			if (cielo) {
				css(cielo, '--maschera-cielo', `url("${maschera(4, 16, S.nw, { basso: 16 })}")`);
				css(cielo, '--maschera-cielo-w', px(4, S.nw) + 'px');
				css(cielo, '--maschera-cielo-h', px(16, S.nw) + 'px');
			}
		}
		// Il video sfuma ai lati (sotto l'HUD del gioco, che resta intero) e in basso; se sborda, niente lati.
		const lato = re.width - rv.width > 10 * pw ? 15 : 0;
		const chiaveVideo = [S.nw, S.dpr, lato].join(':');
		if (chiaveVideo !== mascheraChiave) {
			mascheraChiave = chiaveVideo;
			css(video, '--maschera', `url("${maschera(480, 270, S.nw, { basso: 10, lato, latoDa: 44 })}")`);
		}
	}

	/* ------------------------------------------------------------ sprite veri, con i tempi veri */
	const DATI = {};
	const sprite = [];
	// ?v= è l'impronta dei file degli sprite (tools/site/build.py): niente miscugli di versioni dalla cache.
	const urlMedia = (f) => new URL('media/sprite/' + f + (doc.dataset.mediaV ? '?v=' + doc.dataset.mediaV : ''), BASE).href;
	class Sprite {
		constructor(el, d) {
			this.el = el; this.d = d; this.anim = null; this.i = 0; this.t = 0; this.poi = null; this.fx = -1; this.fy = -1;
			this.var = el.dataset.variante || '';
			const contenitore = el.parentElement && el.parentElement.matches('.palco__sprite, .palchetto:not(.palchetto--due), .continua__gig') ? el.parentElement : null;
			for (const b of [el, contenitore]) {
				if (!b) continue;
				css(b, '--cw', d.cella[0]); css(b, '--ch', d.cella[1]);
				css(b, '--iw', d.dimensioni[0]); css(b, '--ih', d.dimensioni[1]);
				css(b, '--px0', d.piedi[0]); css(b, '--py0', d.piedi[1]);
			}
			this.variante(this.var);
			this.imposta(el.dataset.anim || 'guardia');
			osserva(el);
		}
		variante(v) {
			this.var = v;
			const f = v && this.d.varianti && this.d.varianti[v] ? this.d.varianti[v] : this.d.immagine;
			css(this.el, '--img', `url("${urlMedia(f)}")`);
		}
		imposta(nome, poi) {
			const a = this.d.animazioni[nome];
			if (!a) return;
			this.anim = a; this.nome = nome; this.i = 0; this.t = 0; this.poi = poi || null;
			this.disegna();
		}
		get azione() { return !!this.poi; }
		passo(dt) {
			if (!this.anim) return;
			if (!this.poi && (!moto || !vede(this.el))) return;   // ferme se non si vedono o senza movimento
			this.t += dt;
			let f = this.anim.fotogrammi[this.i];
			while (this.t >= f.ms) {
				this.t -= f.ms;
				this.i++;
				if (this.i >= this.anim.fotogrammi.length) {
					if (this.anim.ciclo) this.i = 0;
					else {
						this.i = this.anim.fotogrammi.length - 1;
						const poi = this.poi; this.poi = null;
						if (poi) { poi(); return; }
						break;
					}
				}
				f = this.anim.fotogrammi[this.i];
			}
			this.disegna();
		}
		fotogramma(nome, i) {
			if (this.nome !== nome) { this.anim = this.d.animazioni[nome]; this.nome = nome; this.poi = null; }
			const n = this.anim.fotogrammi.length;
			this.i = ((i % n) + n) % n;
			this.t = 0;
			this.disegna();
		}
		disegna() {
			const f = this.anim.fotogrammi[this.i];
			if (f.x !== this.fx) { this.fx = f.x; css(this.el, '--fx', f.x); }
			if (f.y !== this.fy) { this.fy = f.y; css(this.el, '--fy', f.y); }
		}
	}
	async function caricaSprite() {
		const nomi = [...new Set($$('[data-sprite]').map((e) => e.dataset.sprite))];
		await Promise.all(nomi.map(async (n) => {
			try {
				const r = await fetch(urlMedia(n + '.json'));
				if (r.ok) DATI[n] = await r.json();
			} catch (e) { /* senza i dati restano ferme */ }
		}));
		for (const el of $$('[data-sprite]')) {
			const d = DATI[el.dataset.sprite];
			if (!d) continue;
			const s = new Sprite(el, d);
			el._sprite = s;
			if (el.dataset.x) css(el, '--x', el.dataset.x);
			if (el.dataset.y) css(el, '--y', el.dataset.y);
			sprite.push(s);
		}
		strada.gig = $('.strada__gig') && $('.strada__gig')._sprite;
		luce.prova();
		richiedi();
	}
	const MOSSE = { gig: 'gancio', punk: 'gancio_caricato', bruto: 'pugno' };
	for (const b of $$('.palco__sprite')) {
		b.addEventListener('click', () => {
			const el = $('.sprite', b);
			const s = el && el._sprite;
			if (!s || s.azione) return;
			s.imposta(MOSSE[b.dataset.azione], () => s.imposta('guardia'));
			if (b.dataset.azione === 'gig') parlaTere($('.voce--tere .tere'), 1400);
			richiedi();
		});
	}
	const tereTimer = new WeakMap();
	function parlaTere(el, ms) {
		if (!el) return;
		el.classList.add('parla');
		clearTimeout(tereTimer.get(el));
		tereTimer.set(el, setTimeout(() => el.classList.remove('parla'), ms));
	}

	/* ------------------------------------------------------------ la strada: si scorre e GIG cammina */
	const strada = { el: $('.strada__scena'), gig: null, ultimoP: null, fermo: 0, passi: 0 };
	const STRADA_W = 1175;
	function aggiornaStrada(ora, r) {
		const el = strada.el;
		if (!el || !r) return;
		if (!(r.bottom > -50 && r.top < S.vh + 50) && strada.ultimoP !== null) return;
		const ps = px(1, S.ns);
		const V = r.width / ps;
		const t = clamp((S.vh - r.top) / (S.vh + r.height), 0, 1);
		const p = moto ? 75 + (825 - 75) * t : 700;
		const cam = clamp(p - V * 0.36, 0, Math.max(0, STRADA_W - V));
		css(el, '--strada-x', -Math.round(cam * S.ns) / S.dpr + 'px');
		css(el, '--strada-tetti-x', (-Math.round(cam * 0.5 * S.ns) - 375 * S.ns) / S.dpr + 'px');
		const g = strada.gig;
		if (g) {
			css(g.el, '--x', Math.round((p - cam) * S.ns) / S.ns);
			css(g.el, '--y', g.el.dataset.y || 235);
			if (strada.ultimoP !== null && Math.abs(p - strada.ultimoP) > 0.05) {
				strada.passi += p - strada.ultimoP;
				g.fotogramma('camminata', Math.floor(strada.passi / 7.5));
				strada.fermo = ora;
			} else if (g.nome === 'camminata' && ora - strada.fermo > 150) {
				g.imposta('guardia');
			}
			strada.ultimoP = p;
		}
	}

	/* ------------------------------------------------------------ il muro dei cartelloni */
	const muro = { el: $('.muro'), vista: $('.muro__vista'), striscia: $('.muro__striscia'), attivo: false, corsa: 0, vistaH: 0, macchie: '' };
	function impaginaMuro() {
		if (!muro.el) return;
		const attiva = moto && S.vw >= 1000 && S.vh >= 620;
		muro.attivo = attiva;
		muro.el.classList.toggle('muro--pan', attiva);
		// Con la telecamera la striscia non scorre di lato: la lista non prende il fuoco (lo prendono i tasti).
		if (muro.striscia) {
			if (attiva) muro.striscia.removeAttribute('tabindex');
			else muro.striscia.tabIndex = 0;
		}
		if (!attiva) {
			muro.el.style.height = '';
			css(muro.striscia, '--pan', '0px');
		} else {
			muro.vistaH = S.vh - S.hud;
			const cw = Math.round(clamp(S.vw * 0.4, 460, 600));
			css(muro.el, '--cartellone-w', cw + 'px');
			css(muro.el, '--arte-h', Math.round(clamp(muro.vistaH * 0.46, 230, 340)) + 'px');
			muro.corsa = Math.max(0, muro.striscia.scrollWidth - S.vw);
			muro.el.style.height = Math.round(muro.vistaH + muro.corsa * 0.85) + 'px';
			aggiornaMuro(muro.el.getBoundingClientRect());
		}
		dipingiCartelloni();
	}
	function aggiornaMuro(r) {
		if (!muro.attivo || !r) return;
		const percorso = muro.el.offsetHeight - muro.vistaH;
		const p = percorso > 0 ? clamp((S.hud - r.top) / percorso, 0, 1) : 0;
		css(muro.striscia, '--pan', aggancia(-p * muro.corsa) + 'px');
	}
	// I bordi dell'arte, dipinti a spruzzo: frastagliati, a retino di Bayer, con un seme per cartellone.
	function bordoSpruzzo(wg, hg, n, seme) {
		const r = mulberry32(seme);
		const liscio = (k) => {
			const a = Array.from({ length: k }, () => r() * 3.2);
			return a.map((v, i) => (v + a[Math.max(0, i - 1)] + a[Math.min(k - 1, i + 1)]) / 3);
		};
		const su = liscio(wg), giu = liscio(wg), sx = liscio(hg), dx = liscio(hg);
		const piccolo = document.createElement('canvas');
		piccolo.width = wg; piccolo.height = hg;
		const c = piccolo.getContext('2d');
		const img = c.createImageData(wg, hg);
		const d = img.data;
		const B = 4;
		for (let y = 0; y < hg; y++) {
			for (let x = 0; x < wg; x++) {
				const dist = Math.min(y - su[x], hg - 1 - y - giu[x], x - sx[y], wg - 1 - x - dx[y]);
				const a = dist >= B ? 1 : (dist + 0.5) / B;
				d[(y * wg + x) * 4 + 3] = a > BAYER[(y & 3) * 4 + (x & 3)] ? 255 : 0;
			}
		}
		c.putImageData(img, 0, 0);
		return ingrandisci(piccolo, n);
	}
	// Il muro: macchie e polvere rossa a retino, una tessera che si ripete (si vede appena).
	function macchieMuro(n) {
		const W = 112, H = 56;
		const a = rumore(W, H, 7, 1991), b = rumore(W, H, 14, 2041);
		const piccolo = document.createElement('canvas');
		piccolo.width = W; piccolo.height = H;
		const c = piccolo.getContext('2d');
		const img = c.createImageData(W, H);
		const d = img.data;
		for (let y = 0; y < H; y++) {
			for (let x = 0; x < W; x++) {
				const i = y * W + x, p = i * 4, soglia = BAYER[(y & 3) * 4 + (x & 3)];
				const macchia = (a[i] - 0.5) * 2.4, polvere = (b[i] - 0.56) * 2.6;
				if (macchia > soglia) { d[p] = 11; d[p + 1] = 8; d[p + 2] = 22; d[p + 3] = 70; }
				else if (polvere > soglia) { d[p] = 119; d[p + 1] = 64; d[p + 2] = 43; d[p + 3] = 46; }
			}
		}
		c.putImageData(img, 0, 0);
		return ingrandisci(piccolo, n);
	}
	const spruzzi = new WeakMap();
	function dipingiCartelloni() {
		const arti = $$('.cartellone__arte');
		const misure = arti.map((a) => a.getBoundingClientRect());
		const pg = px(1, S.nm);
		arti.forEach((a, i) => {
			const r = misure[i];
			if (!r.width || !r.height) return;
			const wg = Math.ceil(r.width / pg), hg = Math.ceil(r.height / pg);
			const chiave = [wg, hg, S.nm, S.dpr].join(':');
			if (spruzzi.get(a) === chiave) return;
			spruzzi.set(a, chiave);
			css(a, '--spruzzo', `url("${bordoSpruzzo(wg, hg, S.nm, 41 + i * 97)}")`);
			css(a, '--spruzzo-w', wg * pg + 'px');
			css(a, '--spruzzo-h', hg * pg + 'px');
		});
		const chiave = S.ni + ':' + S.dpr;
		if (muro.el && muro.macchie !== chiave) {
			muro.macchie = chiave;
			css(muro.el, '--muro-macchie', `url("${macchieMuro(S.ni)}")`);
			css(muro.el, '--muro-macchie-w', px(112, S.ni) + 'px');
			css(muro.el, '--muro-macchie-h', px(56, S.ni) + 'px');
		}
	}
	if (muro.el) {
		// Con la tastiera, la telecamera va sul cartellone che ha il fuoco: subito, senza lo scorrimento morbido.
		muro.el.addEventListener('focusin', (e) => {
			if (!muro.attivo) return;
			const c = e.target.closest('.cartellone');
			if (!c) return;
			if (muro.vista.scrollLeft) muro.vista.scrollLeft = 0;
			const cw = c.offsetWidth;
			const pan = clamp(c.offsetLeft - (S.vw - cw) / 2, 0, muro.corsa);
			const percorso = muro.el.offsetHeight - muro.vistaH;
			const top = muro.el.getBoundingClientRect().top + window.scrollY - S.hud;
			window.scrollTo({ top: top + (muro.corsa ? (pan / muro.corsa) * percorso : 0), behavior: 'instant' });
		});
		// Dove overflow: clip non c'è, la vista è un contenitore che scorre: il fuoco non deve spostarla.
		if (muro.vista) muro.vista.addEventListener('scroll', () => { if (muro.attivo && muro.vista.scrollLeft) muro.vista.scrollLeft = 0; }, { passive: true });
	}

	/* ------------------------------------------------------------ i tre tasti del riavvio */
	const riavvio = $('.riavvio');
	const tasti = riavvio ? $$('.tasto', riavvio) : [];
	const statoRiavvio = $('.riavvio__stato');
	const finale = $('.cartellone--riavvio');
	const bottoneFinale = $('.risveglio__bottone');
	function statoBraccio(s) {
		riavvio.dataset.stato = s;
		// il testo cambia davvero (non solo con il CSS), così i lettori di schermo lo annunciano
		if (statoRiavvio && statoRiavvio.dataset[s]) statoRiavvio.textContent = statoRiavvio.dataset[s];
	}
	function riavvia() {
		if (!riavvio || riavvio.dataset.stato !== 'bloccato') return;
		statoBraccio('riavvio');
		for (const t of tasti) t.setAttribute('aria-pressed', 'true');
		setTimeout(() => {
			for (const t of tasti) t.setAttribute('aria-pressed', 'false');
			if (finale) {
				// Il fuoco va sul titolo del sesto cartellone prima che il pulsante sparisca; senza la telecamera
				// la striscia scorre fino al sesto, così il riavvio si vede anche sui telefoni.
				const titolo = $('h3', finale);
				const fuoco = document.activeElement;
				const aveva = fuoco && (riavvio.contains(fuoco) || fuoco === bottoneFinale);
				if (titolo) titolo.tabIndex = -1;
				if (!muro.attivo && muro.striscia) {
					const s = muro.striscia;
					const pad = parseFloat(getComputedStyle(s).scrollPaddingInlineStart) || 0;
					const left = finale.getBoundingClientRect().left - s.getBoundingClientRect().left + s.scrollLeft - pad;
					s.scrollTo({ left, behavior: moto ? 'smooth' : 'auto' });
				}
				// (con la telecamera il gestore di focusin porta la pagina sul sesto cartellone)
				if (titolo && aveva) titolo.focus({ preventScroll: true });
				finale.dataset.stato = 'acceso';
				statoBraccio('acceso');
				const r = $('.risveglio__ritratto', finale);
				if (r) { r.src = r.dataset.acceso; r.alt = r.dataset.altAcceso; }
				const g = $('.sprite', finale);
				const sp = g && g._sprite;
				setTimeout(() => {
					if (sp) { sp.variante(''); sp.imposta('gancio', () => sp.imposta('guardia')); }
					parlaTere($('.tere', finale), 1800);
					richiedi();
				}, muro.attivo ? 0 : 450);
			} else statoBraccio('acceso');
			richiedi();
		}, moto ? 1100 : 250);
	}
	for (const t of tasti) {
		t.addEventListener('click', () => {
			if (riavvio.dataset.stato !== 'bloccato') return;
			t.setAttribute('aria-pressed', String(t.getAttribute('aria-pressed') !== 'true'));
			if (tasti.every((k) => k.getAttribute('aria-pressed') === 'true')) riavvia();
		});
	}
	if (bottoneFinale) bottoneFinale.addEventListener('click', riavvia);
	// Le frecce del muro, quando si scorre di lato (schermi stretti o movimento ridotto)
	for (const b of $$('.muro__frecce [data-dir]')) {
		b.addEventListener('click', () => {
			const c = $('.cartellone', muro.striscia);
			const passo = c ? c.getBoundingClientRect().width + 32 : 400;
			muro.striscia.scrollBy({ left: Number(b.dataset.dir) * passo, behavior: moto ? 'smooth' : 'auto' });
		});
	}
	// Se il sistema lascia passare CTRL+ALT+CANC (su Windows non succede), vale anche quello.
	document.addEventListener('keydown', (e) => {
		if (e.ctrlKey && e.altKey && e.key === 'Delete') riavvia();
	});

	/* ------------------------------------------------------------ HUD */
	const hud = $('#hud');
	function aggiornaHud(y) { if (hud) hud.classList.toggle('hud--pieno', y > 24); }
	// Se la barra non ci sta (lingua, carattere più grande, zoom), si passa al menu: lo decide la misura vera.
	function misuraHud() {
		if (!hud) return;
		hud.classList.remove('hud--stretto');
		if (hud.scrollWidth > hud.clientWidth + 1) hud.classList.add('hud--stretto');
	}
	const voci = $$('.hud__nav a');
	if ('IntersectionObserver' in window && voci.length) {
		const io = new IntersectionObserver((ee) => {
			for (const e of ee) {
				if (!e.isIntersecting) continue;
				for (const a of voci) a.setAttribute('aria-current', String(a.getAttribute('href') === '#' + e.target.id));
			}
		}, { rootMargin: '-45% 0px -50% 0px' });
		for (const a of voci) { const s = $(a.getAttribute('href')); if (s) io.observe(s); }
	}
	const menu = $('.hud__menu');
	const nav = $('#sezioni');
	function chiudiMenu() { if (nav) nav.classList.remove('aperto'); if (menu) menu.setAttribute('aria-expanded', 'false'); }
	if (menu && nav) {
		menu.addEventListener('click', () => {
			const aperto = nav.classList.toggle('aperto');
			menu.setAttribute('aria-expanded', String(aperto));
		});
		for (const a of voci) a.addEventListener('click', chiudiMenu);
		document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && nav.classList.contains('aperto')) { chiudiMenu(); menu.focus(); } });
	}

	/* ------------------------------------------------------------ i tasti dei comandi si accendono */
	const kbd = new Map();
	for (const k of $$('.comandi kbd[data-tasto]')) {
		if (!kbd.has(k.dataset.tasto)) kbd.set(k.dataset.tasto, []);
		kbd.get(k.dataset.tasto).push(k);
	}
	if (kbd.size) {
		const accendi = (e, si) => {
			if (e.ctrlKey || e.metaKey || e.altKey) return;
			for (const k of kbd.get(e.code) || []) k.classList.toggle('premuto', si);
		};
		document.addEventListener('keydown', (e) => accendi(e, true));
		document.addEventListener('keyup', (e) => accendi(e, false));
		window.addEventListener('blur', () => { for (const l of kbd.values()) for (const k of l) k.classList.remove('premuto'); });
	}

	/* ------------------------------------------------------------ la luce provata con la normal map */
	const luce = {
		tela: $('.luce__tela'), ctx: null, out: null, alb: null, nor: null, W: 150, H: 150, chiesta: false,
		vista: 'luce', lx: 115, ly: 42, auto: true, tempo: 0, anim: null, i: 0, t: 0, chiave: '', pronta: false,
		// La normal map (100 KB) si scarica solo quando il riquadro sta per entrare nello schermo.
		prova() {
			if (this.chiesta || !this.tela || !DATI.gig || !vede(this.tela)) return;
			this.chiesta = true;
			this.carica();
		},
		async carica() {
			const d = DATI.gig;
			const leggi = (f) => new Promise((ok, ko) => {
				const im = new Image();
				im.onload = () => {
					const c = document.createElement('canvas');
					c.width = im.width; c.height = im.height;
					const g = c.getContext('2d');
					g.drawImage(im, 0, 0);
					ok(g.getImageData(0, 0, im.width, im.height));
				};
				im.onerror = ko;
				im.src = urlMedia(f);
			});
			try {
				[this.alb, this.nor] = await Promise.all([leggi(d.immagine), leggi(d.normali)]);
			} catch (e) { return; }
			// la normal map deve combaciare con lo sprite pixel per pixel, se no la luce disegna strisce
			if (this.alb.width !== this.nor.width || this.alb.height !== this.nor.height) return;
			this.d = d;
			this.anim = d.animazioni.guardia;
			this.ctx = this.tela.getContext('2d');
			this.out = this.ctx.createImageData(this.W, this.H);
			this.pronta = true;
			this.tela.tabIndex = 0;
			const punta = (e) => {
				const r = this.tela.getBoundingClientRect();
				this.lx = clamp(((e.clientX - r.left) / r.width) * this.W, 0, this.W - 1);
				this.ly = clamp(((e.clientY - r.top) / r.height) * this.H, 0, this.H - 1);
				this.auto = false;
				richiedi();
			};
			this.tela.addEventListener('pointermove', punta);
			this.tela.addEventListener('pointerdown', punta);
			this.tela.addEventListener('keydown', (e) => {
				const passi = { ArrowLeft: [-4, 0], ArrowRight: [4, 0], ArrowUp: [0, -4], ArrowDown: [0, 4] }[e.key];
				if (!passi) return;
				e.preventDefault();
				this.lx = clamp(this.lx + passi[0], 0, this.W - 1);
				this.ly = clamp(this.ly + passi[1], 0, this.H - 1);
				this.auto = false;
				richiedi();
			});
			for (const b of $$('.luce__comandi [data-vista]')) {
				b.addEventListener('click', () => {
					this.vista = b.dataset.vista;
					for (const x of $$('.luce__comandi [data-vista]')) x.setAttribute('aria-pressed', String(x === b));
					this.chiave = '';
					richiedi();
				});
			}
			richiedi();
		},
		passo(dt) {
			if (!this.pronta || !vede(this.tela)) return;
			if (moto) {
				this.t += dt;
				let f = this.anim.fotogrammi[this.i];
				while (this.t >= f.ms) { this.t -= f.ms; this.i = (this.i + 1) % this.anim.fotogrammi.length; f = this.anim.fotogrammi[this.i]; }
				if (this.auto) {
					this.tempo += dt / 1000;
					this.lx = 75 + 58 * Math.cos(this.tempo * 0.9);
					this.ly = 55 + 32 * Math.sin(this.tempo * 0.7);
				}
			}
			this.disegna();
		},
		disegna() {
			const f = this.anim.fotogrammi[this.i];
			const lxq = Math.round(this.lx), lyq = Math.round(this.ly);
			const chiave = [this.vista, f.x, f.y, lxq, lyq].join(':');
			if (chiave === this.chiave) return;
			this.chiave = chiave;
			const { W, H } = this;
			const o = this.out.data;
			const [cw, ch] = this.d.cella;
			const ox = Math.round((W - cw) / 2), oy = H - ch - 6;
			// fondo: la notte, con un velo arancio dove arriva la luce
			for (let y = 0; y < H; y++) {
				for (let x = 0; x < W; x++) {
					const p = (y * W + x) * 4;
					let r = 11, g = 8, b = 22;
					if (this.vista === 'luce') {
						const dd = Math.hypot(x - lxq, y - lyq);
						const a = Math.max(0, 1 - dd / 88);
						const q = a * a * 0.5 > BAYER[(y & 3) * 4 + (x & 3)] * 0.5 ? 1 : 0;
						if (q) { r = 38; g = 20; b = 30; }
					}
					if (y === oy + ch - 1 || y === oy + ch) { r = 38; g = 28; b = 57; }
					o[p] = r; o[p + 1] = g; o[p + 2] = b; o[p + 3] = 255;
				}
			}
			const A = this.alb.data, N = this.nor.data, IW = this.alb.width;
			const AMB = [0.38, 0.34, 0.52], COL = [1.0, 0.68, 0.38], E = 2.1, Z = 35, R = 130;
			for (let y = 0; y < ch; y++) {
				for (let x = 0; x < cw; x++) {
					const s = ((f.y + y) * IW + f.x + x) * 4;
					if (A[s + 3] < 8) continue;
					const p = ((oy + y) * W + ox + x) * 4;
					if (this.vista === 'normali') { o[p] = N[s]; o[p + 1] = N[s + 1]; o[p + 2] = N[s + 2]; continue; }
					if (this.vista === 'piatto') { o[p] = A[s]; o[p + 1] = A[s + 1]; o[p + 2] = A[s + 2]; continue; }
					// Come una PointLight2D di Godot: normale (verde verso l'alto), altezza della luce, attenuazione.
					const nx = N[s] / 127.5 - 1, ny = -(N[s + 1] / 127.5 - 1), nz = N[s + 2] / 127.5 - 1;
					const dx = lxq - (ox + x), dy = lyq - (oy + y);
					const dist = Math.hypot(dx, dy);
					const l = Math.hypot(dx, dy, Z);
					const ndl = Math.max(0, (nx * dx + ny * dy + nz * Z) / l);
					const att = Math.max(0, 1 - dist / R);
					const k = ndl * att * att * E;
					o[p] = Math.min(255, A[s] * (AMB[0] + COL[0] * k));
					o[p + 1] = Math.min(255, A[s + 1] * (AMB[1] + COL[1] * k));
					o[p + 2] = Math.min(255, A[s + 2] * (AMB[2] + COL[2] * k));
				}
			}
			if (this.vista === 'luce') {
				for (let y = -1; y <= 1; y++) for (let x = -1; x <= 1; x++) {
					const X = lxq + x, Y = lyq + y;
					if (X < 0 || Y < 0 || X >= W || Y >= H) continue;
					const p = (Y * W + X) * 4;
					const centro = !x && !y;
					o[p] = 255; o[p + 1] = centro ? 246 : 194; o[p + 2] = centro ? 220 : 122;
				}
			}
			this.ctx.putImageData(this.out, 0, 0);
		},
	};

	/* ------------------------------------------------------------ testi pieghevoli: chiusi sui telefoni */
	if (doc.clientWidth < 700) for (const d of $$('details.pieghevole')) d.open = false;

	/* ------------------------------------------------------------ 404: CONTINUA? */
	const cifra = $('.continua__cifra');
	if (cifra) {
		let k = 9;
		css(cifra, '--cifra', k);
		const conta = setInterval(() => {
			if (!moto) return;
			k = Math.max(0, k - 1);
			css(cifra, '--cifra', k);
			if (!k) clearInterval(conta);
		}, 1000);
	}

	/* ------------------------------------------------------------ ciclo */
	let raf = 0, ultimo = 0, tempo = 0;
	function ciclo(ora) {
		raf = 0;
		const dt = ultimo ? Math.min(100, ora - ultimo) : 16;
		ultimo = ora;
		if (moto) tempo += dt / 1000;
		// prima si legge...
		const y = window.scrollY;
		const rs = strada.el ? strada.el.getBoundingClientRect() : null;
		const rm = muro.attivo ? muro.el.getBoundingClientRect() : null;
		// ...poi si scrive
		const inEroe = eroe && y < S.vh * 1.4;
		if (moto && inEroe) {
			css(nube.el, '--par-nube', aggancia(Math.min(y * 0.45, limiteNube)) + 'px');
			css(tettiEroe, '--par-tetti', aggancia(Math.min(y * 0.2, limiteTetti)) + 'px');
		}
		if (inEroe) nube.disegna(tempo);
		if (vede(arteNube.el)) arteNube.disegna(moto ? tempo : 0);
		aggiornaHud(y);
		aggiornaStrada(ora, rs);
		aggiornaMuro(rm);
		const stradaInVista = strada.el && vede(strada.el);
		const conPolvere = moto && (inEroe || stradaInVista);
		if (polvere.el) {
			polvere.el.hidden = !conPolvere;
			if (conPolvere) polvere.passo(dt);
			css(polvere.el, '--polvere-opacita', (y < S.vh ? 0.9 - (y / S.vh) * 0.5 : 0.45).toFixed(3));
		}
		let azioni = false, vivi = false;
		for (const s of sprite) {
			s.passo(dt);
			azioni = azioni || s.azione;
			vivi = vivi || vede(s.el);
		}
		luce.passo(dt);
		const continua = azioni || (moto && (inEroe || conPolvere || vivi || (luce.pronta && vede(luce.tela))));
		if (continua && !document.hidden) raf = requestAnimationFrame(ciclo);
		else ultimo = 0;
	}
	function richiedi() { if (!raf) raf = requestAnimationFrame(ciclo); }

	function impagina() {
		calcolaScale();
		misuraHud();
		impaginaEroe();
		impaginaMuro();
		polvere.misura();
		nube.chiave = '';
		arteNube.chiave = '';
		if (luce.pronta) luce.chiave = '';
		richiedi();
	}

	/* ------------------------------------------------------------ teaser */
	// Senza JavaScript restano i controlli del browser. Qui, finché non parte, c'è solo il pulsante d'oro
	// (sul telefono non si vedono due ▶); dal primo play tornano i controlli. Il clic è un gesto, quindi
	// l'audio parte; se il browser rifiuta lo stesso, si torna ai suoi controlli.
	const teaser = $('.teaser__video');
	const via = $('.teaser__via');
	if (teaser && via) {
		teaser.controls = false;
		via.hidden = false;
		const avvia = () => {
			teaser.controls = true;
			via.hidden = true;
			const p = teaser.play();
			if (p) p.catch(() => { teaser.controls = true; });
			teaser.focus({ preventScroll: true });
		};
		via.addEventListener('click', avvia);
		teaser.addEventListener('play', () => { teaser.controls = true; via.hidden = true; });
	}

	/* ------------------------------------------------------------ avvio */
	if (bottoneMoto) bottoneMoto.addEventListener('click', () => impostaMovimento(!moto, true));
	ridotto.addEventListener('change', () => { if (!memoria.get('car-movimento')) impostaMovimento(!ridotto.matches, false); });
	if (video) osserva(video, aggiornaVideo);
	if (strada.el) osserva(strada.el);
	if (arteNube.el) osserva(arteNube.el);
	if (luce.tela) osserva(luce.tela, () => luce.prova());
	impostaMovimento(doc.dataset.movimento !== 'no', false);
	if (document.fonts && document.fonts.ready) document.fonts.ready.then(impagina);
	window.addEventListener('load', impagina);
	let attesa = 0;
	window.addEventListener('resize', () => { clearTimeout(attesa); attesa = setTimeout(impagina, 120); });
	(function osservaZoom() {
		const mq = matchMedia(`(resolution: ${window.devicePixelRatio || 1}dppx)`);
		const su = () => { mq.removeEventListener('change', su); impagina(); osservaZoom(); };
		mq.addEventListener('change', su);
	})();
	window.addEventListener('scroll', richiedi, { passive: true });
	document.addEventListener('visibilitychange', () => { aggiornaVideo(); richiedi(); });
	caricaSprite();
})();
