import csv
from collections import Counter

with open('D:\\Trikarta Analis\\Marketing\\Ngagel\\Whatsapp\\Raw_Devi_Analysis_v2.csv', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

print(f'Total klien: {len(rows)}')
print()
header = f"{'No':<4} {'Nama Klien':<35} {'FU Ke-':<8} {'Closing':<10} {'Produk'}"
print(header)
print('-' * 90)
for r in rows:
    nama = r['Nama Klien'][:33]
    produk = r['Produk'][:30]
    print(f"{r['No']:<4} {nama:<35} {r['Follow Up Ke-']:<8} {r['Closing']:<10} {produk}")

print()
c = Counter(r['Closing'] for r in rows)
print('=== REKAP CLOSING ===')
for status, count in c.items():
    print(f"  {status}: {count} klien")
