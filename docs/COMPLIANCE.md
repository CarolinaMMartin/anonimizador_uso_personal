# Cumplimiento legal y de licencias — Anonimizador Judicial

Versión de referencia: ver `app_version` en `/health`.

---

## 1. Resumen ejecutivo

| Aspecto | Estado en build estándar |
|---------|--------------------------|
| Procesamiento de datos | 100 % local (`127.0.0.1`), sin APIs en la nube |
| Conexión a Internet en runtime | **No requerida** (UI sin CDN; Presidio sin tldextract/red) |
| Datos personales en el ZIP | **No** (sin `sessions.db` ni documentos de ejemplo) |
| Componentes copyleft | **Modelo spaCy (GPL-3.0)** |
| PDF | **pdfplumber (MIT) + ReportLab (BSD)** |
| Licencias de terceros | `THIRD_PARTY_NOTICES.txt` + carpeta `LICENSES/` |

**Titularidad:** confirmar con IALAB/UBA (ver `LICENSE` en la raíz).

---

## 2. Tabla de cumplimiento por componente

| Componente / licencia | Qué requiere | Qué hacemos | Dónde queda |
|----------------------|--------------|-------------|-------------|
| **MIT / BSD / Apache** | Conservar aviso de licencia | `LICENSES/` + `THIRD_PARTY_NOTICES.txt` | Raíz + ZIP portable |
| **FastAPI, Presidio, spaCy lib., NetworkX, RapidFuzz, python-docx, pdfplumber, reportlab, Uvicorn, Pydantic** | Aviso permisivo | Listados como terceros | Informe + portable |
| **Modelo `es_core_news_md` (GPL-3.0)** | Aviso GPL al redistribuir binario + modelo | `LICENSES/GPL-3.0.txt` | Portable + docs |
| **PyInstaller** | Herramienta de build | Solo desarrollo | `THIRD_PARTY_NOTICES.txt` |
| **Diccionarios JSON propios** | Documentar autoría | `data/README.md` | Repo + ZIP |
| **Logo / marca IALAB** | Autorización institucional | Pendiente IALAB | Manual |
| **Fuentes** | Sin CDN | Fuentes del sistema | `frontend/styles.css` |
| **SQLite / sessions.db** | Privacidad | No se distribuye | Manual §7 |
| **Frontend propio** | Titularidad | `LICENSE` | Repo |

---

## 3. Modelo spaCy GPL-3.0

El portable incluye `models/es_core_news_md/` (~40 MB). Licencia **GPL-3.0**.

Texto completo incluido en el paquete: **`models/es_core_news_md/LICENSE`** (no editar).
Copia de referencia adicional: `LICENSES/GPL-3.0.txt`.

---

## 4. Componentes runtime del paquete 

- Motor: FastAPI + Uvicorn (localhost)
- Detección: **regex AR + Presidio + spaCy**
- Extracción PDF: **pdfplumber** (MIT)
- Export: **python-docx** (MIT), **ReportLab** (BSD)
- Resolución: RapidFuzz, NetworkX
- UI: HTML/CSS/JS propio
- Diccionarios + modelo spaCy

No hay OCR, LLM local, ni APIs externas de IA.

### Presidio y red (tldextract) 

Por defecto, el `EmailRecognizer` de Presidio usa `tldextract`, que en su
primera invocación intenta descargar la Public Suffix List desde
`publicsuffix.org` ([Presidio #1205](https://github.com/microsoft/presidio/issues/1205)).
Esto rompía la promesa de "procesamiento 100 % local" en redes aisladas. Esto es solo una advertencia para los desarrolladores. Del publicado ya fue eliminado. 

**Mitigación aplicada desde v3.3.9 (vigente):**
- `EmailRecognizer` **removido** del analyzer Presidio.
- Emails detectados por **regex AR** + catálogo (`RGX_EMAIL`).
- `tldextract` forzado a usar un snapshot local embebido
  (`app/detection/presidio_offline.py`) que bloquea cualquier llamada a
  red.
- Test de regresión: `tests/test_presidio_offline.py` verifica que ni
  `tldextract` ni `presidio_analyzer` intenten resolver `publicsuffix.org`.

Se conserva esta nota como **decisión de diseño documentada**: si alguien
en un fork reactiva el `EmailRecognizer`, debe revisar también
`presidio_offline.py` para no reintroducir la fuga de red.


## 5. Generación del paquete *(solo desarrollo; no aplica al usuario final)*

El usuario final **no ejecuta** estos comandos. Recibe el ZIP ya empaquetado.

```powershell
.venv\Scripts\python scripts\install_nlp.py
.venv\Scripts\python scripts\build_portable_full.py
.venv\Scripts\python scripts\package_release.py --suffix PJ-v3.3.10
```

---

*Última revisión: junio 2026*
