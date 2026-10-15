/* ===========================================================================
   Skrip antarmuka Sistem Informasi E-Posyandu
   =========================================================================== */
(function () {
    'use strict';

    function siap(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    siap(function () {

    /* ---- buka/tutup sidebar pada layar kecil ---- */
    var sidebar = document.getElementById('sidebar');
    var tombolMenu = document.getElementById('tombolMenu');
    var tirai = document.getElementById('tirai');

    function tutupMenu() {
        if (sidebar) sidebar.classList.remove('terbuka');
        if (tirai) tirai.classList.remove('tampil');
    }
    if (tombolMenu && sidebar) {
        tombolMenu.addEventListener('click', function () {
            sidebar.classList.toggle('terbuka');
            if (tirai) tirai.classList.toggle('tampil');
        });
    }
    if (tirai) tirai.addEventListener('click', tutupMenu);

    /* ---- konfirmasi tindakan yang menghapus data ---- */
    document.querySelectorAll('form[data-konfirmasi]').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            if (!window.confirm(form.dataset.konfirmasi)) e.preventDefault();
        });
    });

    /* ---- tampilkan / sembunyikan kata sandi ----
       Tombol: <button data-lihat-sandi="#password"> */
    document.querySelectorAll('[data-lihat-sandi]').forEach(function (tombol) {
        tombol.addEventListener('click', function () {
            var kolom = document.querySelector(tombol.dataset.lihatSandi);
            if (!kolom) return;
            kolom.type = kolom.type === 'password' ? 'text' : 'password';
            kolom.focus();
        });
    });

    /* ---- keterangan umur saat pengukuran ----
       Wadah: <span data-umur-ukur data-tanggal="#tanggal" data-lahir="#birth_date"> */
    document.querySelectorAll('[data-umur-ukur]').forEach(function (keluaran) {
        var tgl = document.querySelector(keluaran.dataset.tanggal);
        var lahirEl = document.querySelector(keluaran.dataset.lahir);
        if (!tgl || !lahirEl) return;

        function perbarui() {
            if (!tgl.value || !lahirEl.value) { keluaran.textContent = ''; return; }
            var a = new Date(tgl.value);
            var b = new Date(lahirEl.value);
            if (isNaN(a) || isNaN(b)) { keluaran.textContent = ''; return; }

            var hari = Math.floor((a - b) / 86400000);
            if (hari < 0) {
                keluaran.textContent = 'Tanggal pengukuran mendahului tanggal lahir.';
                return;
            }
            if (hari > 1856) {
                keluaran.textContent = 'Umur ' + hari + ' hari melebihi rentang tabel WHO (0-5 tahun).';
                return;
            }
            var bulan = Math.floor(hari / 30);
            var tahun = Math.floor(bulan / 12);
            var teks = (tahun ? tahun + ' tahun ' : '') + (bulan % 12) + ' bulan';
            keluaran.textContent = 'Umur saat diukur: ' + teks + ' (' + hari + ' hari)';
        }
        tgl.addEventListener('change', perbarui);
        tgl.addEventListener('input', perbarui);
        perbarui();
    });

    /* ---- keterangan umur dari tanggal lahir ----
       Wadah: <span data-umur-lahir data-lahir="#birth_date"> */
    document.querySelectorAll('[data-umur-lahir]').forEach(function (keluaran) {
        var asal = document.querySelector(keluaran.dataset.lahir);
        if (!asal) return;

        function perbarui() {
            if (!asal.value) {
                keluaran.textContent = 'Pilih tanggal lahir untuk melihat umur balita.';
                return;
            }
            var lahir = new Date(asal.value);
            var kini = new Date();
            if (isNaN(lahir) || lahir > kini) {
                keluaran.textContent = 'Tanggal lahir belum valid.';
                return;
            }
            var hari = Math.floor((kini - lahir) / 86400000);
            var tahun = Math.floor(hari / 365);
            var bulan = Math.floor((hari % 365) / 30);
            keluaran.textContent = 'Umur saat ini: ' +
                (tahun ? tahun + ' tahun ' : '') + bulan + ' bulan (' + hari + ' hari)';
        }
        asal.addEventListener('change', perbarui);
        asal.addEventListener('input', perbarui);
        perbarui();
    });

    /* ---- "Lupa kata sandi?" belum punya alur pemulihan sendiri,
       jadi arahkan pengguna ke administrator/kader yang mengelola akun ---- */
    var lupaLihat = document.getElementById('lupaSandi');
    if (lupaLihat) {
        lupaLihat.addEventListener('click', function (e) {
            e.preventDefault();
            window.alert('Untuk mengatur ulang kata sandi, hubungi administrator ' +
                         'atau kader posyandu yang mengelola akun Anda.');
        });
    }

    });

})();
