# Licencias de terceros

Esta carpeta contiene textos de licencia para componentes incluidos o referenciados
en el Anonimizador Judicial.

| Archivo | Componente |
|---------|------------|
| `MIT.txt` | FastAPI, Presidio, spaCy (librería), RapidFuzz, python-docx, etc. |
| `Apache-2.0.txt` | python-multipart, aiofiles |
| `BSD-3-Clause.txt` | Uvicorn, NetworkX, NumPy (referencia) |
| `GPL-3.0.txt` | Modelo spaCy `es_core_news_md` (copia de referencia; canonical: `models/es_core_news_md/LICENSE` en el portable) |
| `BSD-3-Clause.txt` | ReportLab, Uvicorn, NetworkX |

Resumen operativo: `../THIRD_PARTY_NOTICES.txt`  
Informe para IT / Poder Judicial: `../docs/COMPLIANCE.md`

En el paquete portable, las licencias de dependencias empaquetadas también figuran
en `_internal/<paquete>.dist-info/licenses/`.
