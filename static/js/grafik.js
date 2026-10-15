/* ===========================================================================
   Penggambar grafik pertumbuhan (KMS digital) berbasis SVG.
   Menampilkan kurva rujukan WHO (-3 s.d. +3 SD) dan titik pengukuran anak.
   =========================================================================== */
(function (global) {
    'use strict';

    // warna garis rujukan WHO per nilai Z
    var WARNA_Z = {
        '-3': '#E5322C',
        '-2': '#EF9000',
        '-1': '#B8C0CF',
        '0': '#2E9E5B',
        '1': '#B8C0CF',
        '2': '#00AEEF',
        '3': '#E6178C'
    };
    var KETEBALAN_Z = { '-3': 2, '-2': 2, '-1': 1, '0': 2, '1': 1, '2': 2, '3': 2 };
    var LABEL_Z = {
        '-3': '−3 SD', '-2': '−2 SD', '-1': '−1 SD', '0': 'Median',
        '1': '+1 SD', '2': '+2 SD', '3': '+3 SD'
    };

    var BULAN = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun',
                 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];

    function warnaTitik(z) {
        if (z === null || z === undefined) return '#7A8394';
        if (z < -2) return '#E5322C';
        if (z < -1.5) return '#EF9000';
        return '#2E9E5B';
    }

    function buat(tag, atribut, teks) {
        var el = document.createElementNS('http://www.w3.org/2000/svg', tag);
        for (var k in atribut) {
            if (atribut.hasOwnProperty(k)) el.setAttribute(k, atribut[k]);
        }
        if (teks !== undefined) el.textContent = teks;
        return el;
    }

    /* ---------------------------------------------------------------------
       gambar(wadah, data, opsi)
         wadah : elemen DOM tempat SVG dimasukkan
         data  : { titik, kurva, axis, unit, short, label }
         opsi  : { tinggi }
       --------------------------------------------------------------------- */
    function gambar(wadah, data, opsi) {
        opsi = opsi || {};
        wadah.innerHTML = '';

        var titik = data.titik || [];
        var kurva = data.kurva || {};
        var axis = data.axis || 'day';

        var W = 900;
        var H = opsi.tinggi || 420;
        var M = { atas: 18, kanan: 16, bawah: 46, kiri: 52 };
        var lw = W - M.kiri - M.kanan;
        var lh = H - M.atas - M.bawah;

        // ---- tentukan rentang sumbu ----
        var semuaY = [];
        var semuaX = [];

        Object.keys(kurva).forEach(function (z) {
            (kurva[z] || []).forEach(function (p) {
                semuaX.push(p[0]);
                semuaY.push(p[1]);
            });
        });
        titik.forEach(function (p) {
            semuaX.push(p.x);
            semuaY.push(p.y);
        });

        if (!semuaX.length) {
            wadah.innerHTML = '<div class="kosong" style="padding:30px">' +
                'Belum ada data untuk digambar.</div>';
            return;
        }

        var xMin = Math.min.apply(null, semuaX);
        var xMax = Math.max.apply(null, semuaX);
        var yMin = Math.min.apply(null, semuaY);
        var yMax = Math.max.apply(null, semuaY);

        // beri sedikit ruang pada sumbu Y
        var padY = (yMax - yMin) * 0.06 || 1;
        yMin = Math.max(0, yMin - padY);
        yMax = yMax + padY;

        function sx(v) { return M.kiri + (v - xMin) / (xMax - xMin) * lw; }
        function sy(v) { return M.atas + lh - (v - yMin) / (yMax - yMin) * lh; }

        var svg = buat('svg', {
            viewBox: '0 0 ' + W + ' ' + H,
            'class': 'grafik-svg',
            preserveAspectRatio: 'xMidYMid meet',
            role: 'img'
        });

        // ---- latar & bingkai ----
        svg.appendChild(buat('rect', {
            x: M.kiri, y: M.atas, width: lw, height: lh,
            fill: '#FCFDFE', stroke: '#E4E7EE', 'stroke-width': 1, rx: 8
        }));

        // ---- garis bantu horizontal + label sumbu Y ----
        var nGridY = 5;
        for (var i = 0; i <= nGridY; i++) {
            var yv = yMin + (yMax - yMin) * i / nGridY;
            var yp = sy(yv);
            svg.appendChild(buat('line', {
                x1: M.kiri, y1: yp, x2: M.kiri + lw, y2: yp,
                stroke: '#EFF1F6', 'stroke-width': 1
            }));
            svg.appendChild(buat('text', {
                x: M.kiri - 8, y: yp + 4, 'text-anchor': 'end',
                'font-size': 11, fill: '#8A92A3'
            }, Math.round(yv * 10) / 10));
        }

        // ---- garis bantu vertikal + label sumbu X ----
        var langkahX = (xMax - xMin) / 6;
        for (var j = 0; j <= 6; j++) {
            var xv = xMin + langkahX * j;
            var xp = sx(xv);
            svg.appendChild(buat('line', {
                x1: xp, y1: M.atas, x2: xp, y2: M.atas + lh,
                stroke: '#EFF1F6', 'stroke-width': 1
            }));
            var labelX;
            if (axis === 'day') {
                var bulan = Math.round(xv / 30.44);
                labelX = bulan < 12 ? bulan + ' bln' : Math.floor(bulan / 12) + ' thn ' + (bulan % 12) + ' bln';
            } else {
                labelX = Math.round(xv) + ' cm';
            }
            svg.appendChild(buat('text', {
                x: xp, y: M.atas + lh + 17, 'text-anchor': 'middle',
                'font-size': 11, fill: '#8A92A3'
            }, labelX));
        }

        // ---- kurva rujukan WHO ----
        // urutan: dari luar ke dalam supaya kurva median tergambar di atas
        var urutanZ = ['-3', '-2', '-1', '1', '2', '3', '0'];
        urutanZ.forEach(function (z) {
            var deret = kurva[z];
            if (!deret || !deret.length) return;
            var d = deret.map(function (p, idx) {
                return (idx === 0 ? 'M' : 'L') + sx(p[0]).toFixed(2) + ' ' + sy(p[1]).toFixed(2);
            }).join(' ');
            svg.appendChild(buat('path', {
                d: d, fill: 'none', stroke: WARNA_Z[z],
                'stroke-width': KETEBALAN_Z[z],
                'stroke-dasharray': (z === '0' ? '' : (parseInt(z, 10) % 2 === 0 ? '' : '5 4')),
                'stroke-linecap': 'round', opacity: z === '0' ? 1 : .85
            }));
        });

        // ---- garis penghubung pengukuran anak ----
        if (titik.length > 1) {
            var dAnak = titik.map(function (p, idx) {
                return (idx === 0 ? 'M' : 'L') + sx(p.x).toFixed(2) + ' ' + sy(p.y).toFixed(2);
            }).join(' ');
            svg.appendChild(buat('path', {
                d: dAnak, fill: 'none', stroke: '#105A3C',
                'stroke-width': 2.6, 'stroke-linecap': 'round',
                'stroke-linejoin': 'round', opacity: .92
            }));
        }

        // ---- titik pengukuran anak ----
        var info = buat('g', {});
        titik.forEach(function (p) {
            var cx = sx(p.x), cy = sy(p.y);
            var ling = buat('circle', {
                cx: cx, cy: cy, r: 5.5,
                fill: warnaTitik(p.z), stroke: '#fff', 'stroke-width': 2.2
            });
            ling.style.cursor = 'pointer';

            var judul = buat('title', {}, p.tanggal + ' — ' + p.label +
                ' — ' + p.y + ' ' + (data.unit || '') +
                (p.z !== null && p.z !== undefined ? ' — Z: ' + p.z.toFixed(2) + ' SD' : ''));
            ling.appendChild(judul);
            info.appendChild(ling);
        });
        svg.appendChild(info);

        // ---- label sumbu ----
        svg.appendChild(buat('text', {
            x: M.kiri + lw / 2, y: H - 6, 'text-anchor': 'middle',
            'font-size': 11.5, fill: '#5A6272', 'font-weight': 600
        }, axis === 'day' ? 'Umur anak' : 'Panjang / tinggi badan'));

        svg.appendChild(buat('text', {
            x: 14, y: M.atas + lh / 2, 'text-anchor': 'middle',
            'font-size': 11.5, fill: '#5A6272', 'font-weight': 600,
            transform: 'rotate(-90 14 ' + (M.atas + lh / 2) + ')'
        }, (data.short || '') + ' (' + (data.unit || '') + ')'));

        wadah.appendChild(svg);

        // ---- legenda ----
        var legenda = document.createElement('div');
        legenda.className = 'grafik-legend';
        urutanZ.slice().sort(function (a, b) { return parseInt(a, 10) - parseInt(b, 10); })
            .forEach(function (z) {
                if (!kurva[z] || !kurva[z].length) return;
                var butir = document.createElement('span');
                butir.className = 'butir';
                var garis = document.createElement('span');
                garis.className = 'garis';
                garis.style.background = WARNA_Z[z];
                garis.style.height = KETEBALAN_Z[z] + 'px';
                butir.appendChild(garis);
                butir.appendChild(document.createTextNode(LABEL_Z[z]));
                legenda.appendChild(butir);
            });

        var butirAnak = document.createElement('span');
        butirAnak.className = 'butir';
        var garisAnak = document.createElement('span');
        garisAnak.className = 'garis';
        garisAnak.style.background = '#105A3C';
        garisAnak.style.height = '3px';
        butirAnak.appendChild(garisAnak);
        butirAnak.appendChild(document.createTextNode('Pengukuran anak'));
        legenda.appendChild(butirAnak);

        wadah.appendChild(legenda);
    }

    global.GrafikKMS = { gambar: gambar, warnaTitik: warnaTitik, BULAN: BULAN };
})(window);
