import os
os.chdir(r'c:\Users\Sergio Quispilaya H\OneDrive\Escritorio\dashboard mishell')
from data_loader import load_coverage_data
from map_renderer import render_colored_map

df = load_coverage_data('COBERTURAS INMUNIZACIONES POR PROVINCIA- EXPOSICION SVA SARAMPION MINSA.xlsx')

for vac in ['3 Dosis IPV', '1 Ref DPT', '1 Dosis SPR', '2 Ref DPT']:
    pass

vacunas = [
    '3\u00b0 Dosis IPV',
    '1\u00b0 Ref DPT',
    '1\u00b0 Dosis SPR',
    '2\u00b0 Ref DPT',
]
for vac in vacunas:
    mb = render_colored_map(df, vac, 'mapa-departamento-huancavelica-provincias.png')
    safe = vac.replace(' ', '_').replace('\u00b0', '')
    fname = f'mapa_exec_{safe}.png'
    with open(fname, 'wb') as f:
        f.write(mb)
    print(f'OK: {fname} ({len(mb):,} bytes)')

print('Todos los mapas generados.')
