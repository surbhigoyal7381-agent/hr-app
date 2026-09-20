// A small QR code encoder, drawn in the browser (slice 013 step 5, US-6).
//
// Why this exists: the joining code HR makes must be drawn as a QR picture in
// the browser from E7's answer, and no other request may ever carry the code
// (AC-47). Frappe ships a QR *scanner* (html5-qrcode) and a server-side QR
// page for two-factor setup, but no encoder for the browser - and a third-party
// encoder could not be brought into this repository. So this is our own: byte
// mode, error level M, versions 1 to 10 (up to 213 characters - an enrol link
// is about 80). It follows ISO/IEC 18004 and was checked module for module
// against Frappe's own `pyqrcode` for inputs across every version it supports.
//
// Global: `window.AlvoraaQR` with `encode`, `svg` and `draw`. No dependencies.

(function (root) {
	"use strict";

	// ── tables (error level M only) ──────────────────────────────────────
	// version -> [ec codewords per block, [blocks in group 1, data codewords
	// per block], [blocks in group 2, data codewords per block]]
	const EC_M = {
		1: [10, [1, 16], [0, 0]],
		2: [16, [1, 28], [0, 0]],
		3: [26, [1, 44], [0, 0]],
		4: [18, [2, 32], [0, 0]],
		5: [24, [2, 43], [0, 0]],
		6: [16, [4, 27], [0, 0]],
		7: [18, [4, 31], [0, 0]],
		8: [22, [2, 38], [2, 39]],
		9: [22, [3, 36], [2, 37]],
		10: [26, [4, 43], [1, 44]],
	};
	const ALIGN = {
		1: [], 2: [6, 18], 3: [6, 22], 4: [6, 26], 5: [6, 30], 6: [6, 34],
		7: [6, 22, 38], 8: [6, 24, 42], 9: [6, 26, 46], 10: [6, 28, 50],
	};
	const MAX_VERSION = 10;

	// ── GF(256) for Reed-Solomon ─────────────────────────────────────────
	const EXP = new Array(512);
	const LOG = new Array(256);
	(function () {
		let x = 1;
		for (let i = 0; i < 255; i++) {
			EXP[i] = x;
			LOG[x] = i;
			x <<= 1;
			if (x & 0x100) x ^= 0x11d;
		}
		for (let i = 255; i < 512; i++) EXP[i] = EXP[i - 255];
	})();

	function gfMul(a, b) {
		if (!a || !b) return 0;
		return EXP[LOG[a] + LOG[b]];
	}

	function generator(n) {
		let g = [1];
		for (let i = 0; i < n; i++) {
			const next = new Array(g.length + 1).fill(0);
			for (let j = 0; j < g.length; j++) {
				next[j] ^= g[j];
				next[j + 1] ^= gfMul(g[j], EXP[i]);
			}
			g = next;
		}
		return g;
	}

	function ecCodewords(data, n) {
		const g = generator(n);
		const rem = new Array(n).fill(0);
		for (let i = 0; i < data.length; i++) {
			const factor = data[i] ^ rem[0];
			rem.shift();
			rem.push(0);
			if (factor) {
				for (let j = 0; j < n; j++) rem[j] ^= gfMul(g[j + 1], factor);
			}
		}
		return rem;
	}

	// ── the bit stream ───────────────────────────────────────────────────
	function utf8(text) {
		const out = [];
		const s = unescape(encodeURIComponent(String(text)));
		for (let i = 0; i < s.length; i++) out.push(s.charCodeAt(i));
		return out;
	}

	function chooseVersion(byteCount) {
		for (let v = 1; v <= MAX_VERSION; v++) {
			const [ec, g1, g2] = EC_M[v];
			const dataCw = g1[0] * g1[1] + g2[0] * g2[1];
			const cci = v < 10 ? 8 : 16;
			if (4 + cci + 8 * byteCount <= 8 * dataCw) return v;
		}
		throw new Error("AlvoraaQR: text too long (" + byteCount + " bytes)");
	}

	function dataCodewords(bytes, version) {
		const [, g1, g2] = EC_M[version];
		const total = g1[0] * g1[1] + g2[0] * g2[1];
		const bits = [];
		const push = (value, count) => {
			for (let i = count - 1; i >= 0; i--) bits.push((value >> i) & 1);
		};
		push(0b0100, 4);
		push(bytes.length, version < 10 ? 8 : 16);
		bytes.forEach((b) => push(b, 8));
		const capacity = total * 8;
		push(0, Math.min(4, capacity - bits.length));
		while (bits.length % 8) bits.push(0);
		const words = [];
		for (let i = 0; i < bits.length; i += 8) {
			let w = 0;
			for (let j = 0; j < 8; j++) w = (w << 1) | bits[i + j];
			words.push(w);
		}
		for (let k = 0; words.length < total; k++) words.push(k % 2 ? 0x11 : 0xec);
		return words;
	}

	function interleave(words, version) {
		const [ec, g1, g2] = EC_M[version];
		const blocks = [];
		let at = 0;
		for (let i = 0; i < g1[0]; i++) {
			blocks.push(words.slice(at, at + g1[1]));
			at += g1[1];
		}
		for (let i = 0; i < g2[0]; i++) {
			blocks.push(words.slice(at, at + g2[1]));
			at += g2[1];
		}
		const ecs = blocks.map((b) => ecCodewords(b, ec));
		const out = [];
		const longest = Math.max(...blocks.map((b) => b.length));
		for (let i = 0; i < longest; i++) {
			blocks.forEach((b) => {
				if (i < b.length) out.push(b[i]);
			});
		}
		for (let i = 0; i < ec; i++) ecs.forEach((e) => out.push(e[i]));
		return out;
	}

	// ── the matrix ───────────────────────────────────────────────────────
	function makeMatrix(version) {
		const size = version * 4 + 17;
		const modules = [];
		const reserved = [];
		for (let r = 0; r < size; r++) {
			modules.push(new Array(size).fill(false));
			reserved.push(new Array(size).fill(false));
		}
		const set = (r, c, dark) => {
			modules[r][c] = dark;
			reserved[r][c] = true;
		};

		// finders and separators
		[[0, 0], [0, size - 7], [size - 7, 0]].forEach(([r0, c0]) => {
			for (let r = -1; r <= 7; r++) {
				for (let c = -1; c <= 7; c++) {
					const rr = r0 + r, cc = c0 + c;
					if (rr < 0 || cc < 0 || rr >= size || cc >= size) continue;
					const edge = r === -1 || r === 7 || c === -1 || c === 7;
					const ring = r === 0 || r === 6 || c === 0 || c === 6;
					const core = r >= 2 && r <= 4 && c >= 2 && c <= 4;
					set(rr, cc, !edge && (ring || core));
				}
			}
		});

		// alignment patterns
		const centres = ALIGN[version];
		centres.forEach((r0) => {
			centres.forEach((c0) => {
				if (reserved[r0][c0]) return;
				for (let r = -2; r <= 2; r++) {
					for (let c = -2; c <= 2; c++) {
						const ring = Math.max(Math.abs(r), Math.abs(c));
						set(r0 + r, c0 + c, ring !== 1);
					}
				}
			});
		});

		// timing
		for (let i = 8; i < size - 8; i++) {
			if (!reserved[6][i]) set(6, i, i % 2 === 0);
			if (!reserved[i][6]) set(i, 6, i % 2 === 0);
		}

		// the dark module, and the format areas (filled in later)
		set(size - 8, 8, true);
		for (let i = 0; i < 9; i++) {
			if (i !== 6) {
				reserved[8][i] = true;
				reserved[i][8] = true;
			}
		}
		for (let i = 0; i < 8; i++) {
			reserved[8][size - 1 - i] = true;
			reserved[size - 1 - i][8] = true;
		}
		// version areas, versions 7 and up
		if (version >= 7) {
			for (let i = 0; i < 6; i++) {
				for (let j = 0; j < 3; j++) {
					reserved[i][size - 11 + j] = true;
					reserved[size - 11 + j][i] = true;
				}
			}
		}
		return { size, modules, reserved };
	}

	function placeData(m, words) {
		const { size, modules, reserved } = m;
		let bit = 0;
		const total = words.length * 8;
		const bitAt = (i) => (words[i >> 3] >> (7 - (i & 7))) & 1;
		let upward = true;
		for (let col = size - 1; col > 0; col -= 2) {
			if (col === 6) col--;
			for (let k = 0; k < size; k++) {
				const row = upward ? size - 1 - k : k;
				for (let dc = 0; dc < 2; dc++) {
					const c = col - dc;
					if (reserved[row][c]) continue;
					modules[row][c] = bit < total ? bitAt(bit) === 1 : false;
					bit++;
				}
			}
			upward = !upward;
		}
	}

	const MASKS = [
		(r, c) => (r + c) % 2 === 0,
		(r) => r % 2 === 0,
		(r, c) => c % 3 === 0,
		(r, c) => (r + c) % 3 === 0,
		(r, c) => (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0,
		(r, c) => ((r * c) % 2) + ((r * c) % 3) === 0,
		(r, c) => (((r * c) % 2) + ((r * c) % 3)) % 2 === 0,
		(r, c) => (((r + c) % 2) + ((r * c) % 3)) % 2 === 0,
	];

	function applyMask(m, mask) {
		const { size, modules, reserved } = m;
		const out = modules.map((row) => row.slice());
		const f = MASKS[mask];
		for (let r = 0; r < size; r++) {
			for (let c = 0; c < size; c++) {
				if (!reserved[r][c] && f(r, c)) out[r][c] = !out[r][c];
			}
		}
		return out;
	}

	function bch(value, poly, bits) {
		// remainder of value * x^bits divided by poly (a Bose-Chaudhuri code)
		const degree = 31 - Math.clz32(poly);
		let v = value << (degree);
		for (let i = bits + degree - 1; i >= degree; i--) {
			if (v & (1 << i)) v ^= poly << (i - degree);
		}
		return (value << degree) | v;
	}

	function writeFormat(grid, size, mask) {
		// level M is 00; then the mask; BCH(15,5) with 0x537, then XOR 0x5412
		const data = (0b00 << 3) | mask;
		const info = bch(data, 0x537, 5) ^ 0x5412;
		// Walking the path below, the i-th module holds bit (14 - i): the most
		// significant bit sits at (8, 0). Checked against pyqrcode.
		const bitAt = (i) => (info >> (14 - i)) & 1;
		for (let i = 0; i < 15; i++) {
			const dark = bitAt(i) === 1;
			// around the top-left finder
			if (i < 6) grid[8][i] = dark;
			else if (i < 8) grid[8][i + 1] = dark;
			else if (i === 8) grid[7][8] = dark;
			else grid[14 - i][8] = dark;
			// the second copy: seven modules up column 8 from the bottom (the
			// dark module sits above them), then eight along row 8 to the right
			if (i < 7) grid[size - 1 - i][8] = dark;
			else grid[8][size - 15 + i] = dark;
		}
	}

	function writeVersion(grid, size, version) {
		if (version < 7) return;
		const info = bch(version, 0x1f25, 6);
		for (let i = 0; i < 18; i++) {
			const dark = ((info >> i) & 1) === 1;
			const a = Math.floor(i / 3), b = i % 3;
			grid[a][size - 11 + b] = dark;
			grid[size - 11 + b][a] = dark;
		}
	}

	function penalty(grid, size) {
		let score = 0;
		// rule 1: runs of five or more in a row or column
		for (let r = 0; r < size; r++) {
			for (const get of [(i) => grid[r][i], (i) => grid[i][r]]) {
				let run = 1;
				for (let i = 1; i < size; i++) {
					if (get(i) === get(i - 1)) {
						run++;
						if (run === 5) score += 3;
						else if (run > 5) score += 1;
					} else run = 1;
				}
			}
		}
		// rule 2: 2x2 blocks of one colour
		for (let r = 0; r < size - 1; r++) {
			for (let c = 0; c < size - 1; c++) {
				const v = grid[r][c];
				if (grid[r][c + 1] === v && grid[r + 1][c] === v && grid[r + 1][c + 1] === v) score += 3;
			}
		}
		// rule 3: the finder-like pattern 1011101 with 0000 on either side
		const pat = [true, false, true, true, true, false, true];
		const hasPattern = (get, at) => {
			for (let k = 0; k < 7; k++) if (get(at + k) !== pat[k]) return false;
			return true;
		};
		const light4 = (get, from) => {
			for (let k = 0; k < 4; k++) {
				const i = from + k;
				if (i < 0 || i >= size || get(i)) return false;
			}
			return true;
		};
		for (let r = 0; r < size; r++) {
			for (const get of [(i) => grid[r][i], (i) => grid[i][r]]) {
				for (let i = 0; i + 7 <= size; i++) {
					if (hasPattern(get, i) && (light4(get, i - 4) || light4(get, i + 7))) score += 40;
				}
			}
		}
		// rule 4: how far the dark share is from 50%
		let dark = 0;
		for (let r = 0; r < size; r++) for (let c = 0; c < size; c++) if (grid[r][c]) dark++;
		const pct = (dark * 100) / (size * size);
		const prev = Math.floor(pct / 5) * 5, next = prev + 5;
		score += Math.min(Math.abs(prev - 50), Math.abs(next - 50)) / 5 * 10;
		return score;
	}

	// ── the public face ──────────────────────────────────────────────────

	/** encode(text, {mask}) -> {version, size, mask, modules[][]} */
	function encode(text, opts) {
		opts = opts || {};
		const bytes = utf8(text);
		const version = chooseVersion(bytes.length);
		const words = interleave(dataCodewords(bytes, version), version);
		const m = makeMatrix(version);
		placeData(m, words);
		const finish = (mask) => {
			const grid = applyMask(m, mask);
			writeFormat(grid, m.size, mask);
			writeVersion(grid, m.size, version);
			return grid;
		};
		let mask = opts.mask;
		let grid;
		if (typeof mask === "number") {
			grid = finish(mask);
		} else {
			let best = Infinity;
			for (let k = 0; k < 8; k++) {
				const g = finish(k);
				const p = penalty(g, m.size);
				if (p < best) {
					best = p;
					mask = k;
					grid = g;
				}
			}
		}
		return { version: version, size: m.size, mask: mask, modules: grid };
	}

	/** svg(text, cell, margin) -> an <svg> string, black on white */
	function svg(text, cell, margin) {
		cell = cell || 4;
		margin = margin == null ? 4 : margin;
		const q = encode(text);
		const px = (q.size + margin * 2) * cell;
		let path = "";
		for (let r = 0; r < q.size; r++) {
			for (let c = 0; c < q.size; c++) {
				if (q.modules[r][c]) {
					path += "M" + (c + margin) * cell + " " + (r + margin) * cell + "h" + cell + "v" + cell + "h-" + cell + "z";
				}
			}
		}
		return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + px + " " + px +
			'" width="' + px + '" height="' + px + '" shape-rendering="crispEdges" role="img">' +
			'<rect width="100%" height="100%" fill="#fff"/><path d="' + path + '" fill="#000"/></svg>';
	}

	/** draw(canvas, text, cell, margin) -> the canvas, painted */
	function draw(canvas, text, cell, margin) {
		cell = cell || 8;
		margin = margin == null ? 4 : margin;
		const q = encode(text);
		const px = (q.size + margin * 2) * cell;
		canvas.width = px;
		canvas.height = px;
		const ctx = canvas.getContext("2d");
		ctx.fillStyle = "#fff";
		ctx.fillRect(0, 0, px, px);
		ctx.fillStyle = "#000";
		for (let r = 0; r < q.size; r++) {
			for (let c = 0; c < q.size; c++) {
				if (q.modules[r][c]) ctx.fillRect((c + margin) * cell, (r + margin) * cell, cell, cell);
			}
		}
		return canvas;
	}

	const api = { encode: encode, svg: svg, draw: draw, MAX_VERSION: MAX_VERSION };
	root.AlvoraaQR = api;
	if (typeof module === "object" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
