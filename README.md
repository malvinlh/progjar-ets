# progjar-ets
Proyek ini dirancang untuk menguji dan membandingkan kinerja server yang diimplementasikan menggunakan multithreading pool dan multiprocessing pool di bawah permintaan klien yang konkuren. Pengujian dilakukan menggunakan stress test dengan berbagai parameter, seperti jumlah server workers (1, 5, 50), jumlah client workers (1, 5, 50), ukuran file (10 MB, 50 MB, 100 MB), dan operasi (download/upload).



## Cara Menjalankan

- Masuk ke dalam folder `orchestrator`.
- Jalankan script python menggunakan `python3 run_full_experiment.py`.
