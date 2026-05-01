import csv

rows = list(csv.DictReader(open('test_wati_final.csv', encoding='utf-8')))

# Verify columns
print("=== KOLOM ===")
print(list(rows[0].keys()))
print()

# Preview first 10 rows
print("=== PREVIEW 10 BARIS PERTAMA ===")
for r in rows[:10]:
    print(f"No:{r['No']:<4} | {r['Tanggal Chat']} {r['Jam Chat']} | {r['Nama Klien'][:22]:<24} | Acara:{r['Acara']:<12} | FU:{r['Follow Up Ke-']:<4} | Closing:{r['Closing']:<10} | Produk:{r['Produk'][:25]:<27} | Kec:{r['Kecepatan Membalas (Jam)']}")
print()

# Count Follow Up distribution
fu_dist = {}
for r in rows:
    k = r['Follow Up Ke-'] if r['Follow Up Ke-'] else '(Chat Pertama)'
    fu_dist[k] = fu_dist.get(k, 0) + 1
print("=== DISTRIBUSI FOLLOW UP ===")
for k in sorted(fu_dist.keys()):
    print(f"  {k:<20}: {fu_dist[k]} baris")
print()

# Count Acara distribution
print("=== DISTRIBUSI ACARA ===")
acara_dist = {}
for r in rows:
    acara_dist[r['Acara']] = acara_dist.get(r['Acara'], 0) + 1
for k, v in sorted(acara_dist.items()):
    print(f"  {k:<20}: {v}")
print()

# Count Produk distribution
print("=== DISTRIBUSI PRODUK ===")
produk_dist = {}
for r in rows:
    produk_dist[r['Produk']] = produk_dist.get(r['Produk'], 0) + 1
for k, v in sorted(produk_dist.items()):
    print(f"  {k:<40}: {v}")
