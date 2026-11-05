/*
	CTRL+ALT REVENGE! · sito: le scale intere, prima del primo disegno
	SPDX-FileCopyrightText: 2026 Luigi Massari
	SPDX-License-Identifier: MIT

	tools/site/build.py copia questo file dentro il <head> di ogni pagina, dopo il foglio di stile: così le misure
	giuste ci sono già al primo disegno e l'impaginazione non salta quando arriva sito.js. Scrive su :root
	--u (px CSS per pixel del dispositivo), le scale --n* (pixel del dispositivo per pixel del gioco) e le misure
	di CAR Pixel (multipli di 12 pixel del dispositivo). Decide anche il movimento: la scelta salvata con il
	pulsante «Animazioni», altrimenti prefers-reduced-motion.
	sito.js richiama window.carScala() a ogni cambio di finestra o di zoom: rifà i conti e restituisce i valori.
*/
(function () {
	'use strict';
	var doc = document.documentElement;
	doc.classList.add('js');
	var salvato = null;
	try { salvato = localStorage.getItem('car-movimento'); } catch (e) { /* modalità privata: pazienza */ }
	var ridotto = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
	doc.setAttribute('data-movimento', salvato === 'si' ? 'si' : salvato === 'no' ? 'no' : ridotto ? 'no' : 'si');

	function scala() {
		var dpr = window.devicePixelRatio || 1;
		var vw = doc.clientWidth || window.innerWidth;
		var vhFisso = Number(new URLSearchParams(window.location.search).get('vh')) || 0;   // catture a pagina intera
		var vh = vhFisso || window.innerHeight;
		// n: la scala intera più grande che sta in cssMax; vicino: la scala intera più vicina a quella voluta
		var n = function (base, cssMax) { return Math.max(1, Math.floor((cssMax * dpr) / base + 1e-6)); };
		var vicino = function (c) { return Math.max(1, Math.round(c * dpr)); };
		var m12 = function (c) { return (Math.max(1, Math.round((c * dpr) / 12)) * 12) / dpr; };
		var largo = vw >= 700;
		var margine = Math.min(72, Math.max(16, vw * 0.05));      // come --margine: clamp(16px, 5vw, 72px)
		var S = { dpr: dpr, u: 1 / dpr, vw: vw, vh: vh, largo: largo, margine: margine };

		// L'HUD in alto: più basso sugli schermi bassi, così resta spazio per il gioco.
		S.nh = vw >= 1100 ? (vh < 800 ? vicino(1.34) : vicino(2)) : vicino(1);
		S.ni = largo ? vicino(2) : vicino(1.34);
		S.fpUi = m12(largo ? 24 : 18);
		S.fpMedio = m12(vw >= 1200 ? 36 : largo ? 30 : 24);
		S.fpTitolo = m12(vw >= 1200 ? 48 : largo ? 40 : 30);
		S.fpPiccolo = m12(12);
		S.hud = (34 * S.nh) / dpr + 16;
		if (largo) {
			// L'eroe: HUD, logo, motto e il video del gioco, nello schermo. Il video può passare la piega di un
			// decimo della sua altezza (sotto c'è solo la didascalia). Poi si prova una scala in più, se il video
			// sta nella larghezza fra i margini e passa la piega al massimo di due quinti: Luigi, 5 novembre 2026,
			// lo vuole ×3 anche in una finestra alta 950 px su un monitor 1080p, anche se poi si scorre.
			// Prima il video più grande, poi il logo.
			// Sopra i 1000 px la testa ha il logo a sinistra e, a destra, motto, genere e pulsanti: è alta quanto
			// il più alto dei due; sotto va in colonna, e le altezze si sommano (@container eroe in sito.css).
			var affiancata = vw > 1000;
			var destra = S.fpMedio * 1.3 * 2 + S.fpUi * 1.3 + 52 + 28;
			var testa = function (nl) {
				var logo = (89 * nl) / dpr;
				return affiancata ? Math.max(logo, destra) : logo + 14 + destra;
			};
			var piega = 0.9;
			var sta = function (nw, nl) { return S.hud + 12 + (4 * nw) / dpr + testa(nl) + (piega * 270 * nw) / dpr <= vh; };
			var nw = n(480, Math.min(vw, 2400));
			while (nw > 1 && !sta(nw, 1)) nw--;
			piega = 0.6;
			if ((480 * (nw + 1)) / dpr <= Math.min(vw - 2 * margine, 2400) && sta(nw + 1, 1)) nw++;
			// il logo si sceglie con la stessa tolleranza, così su uno schermo più alto non diventa più piccolo
			var nl = Math.min(n(248, affiancata ? vw * 0.45 : vw - 2 * margine), nw);
			while (nl > 1 && !sta(nw, nl)) nl--;
			S.nw = nw;
			S.nl = Math.max(1, nl);
		} else {
			// Telefoni: il gioco a scala intera. Se la scala successiva sborda al massimo di 5 pixel del gioco
			// per lato, si usa quella e si tagliano i lati: l'HUD del gioco resta intero (iPhone da 375 px).
			var k = n(480, vw);
			var taglio = (480 - (vw * dpr) / (k + 1)) / 2;
			S.nw = taglio <= 5 ? k + 1 : k;
			S.nl = n(248, vw - 2 * margine);
		}
		S.nc = vw >= 1200 ? vicino(3) : vicino(2);
		S.ns = vw >= 1600 ? vicino(3) : largo ? vicino(2) : vicino(1.34);
		S.nm = vw >= 420 ? vicino(2) : vicino(1.5);
		S.nr = largo ? vicino(3) : vicino(2);
		S.nx = Math.max(1, Math.min(vicino(3), Math.floor((Math.min(vw - 40, 450) * dpr) / 150)));

		var st = doc.style;
		['nw', 'nl', 'nc', 'ns', 'ni', 'nh', 'nm', 'nr', 'nx'].forEach(function (k) { st.setProperty('--' + k, S[k]); });
		st.setProperty('--u', S.u);
		st.setProperty('--fp-ui', S.fpUi + 'px');
		st.setProperty('--fp-medio', S.fpMedio + 'px');
		st.setProperty('--fp-titolo', S.fpTitolo + 'px');
		st.setProperty('--fp-piccolo', S.fpPiccolo + 'px');
		if (vhFisso) st.setProperty('--vh-fisso', vhFisso + 'px');
		return S;
	}
	window.carScala = scala;
	scala();
}());
