# Manual de instalación — Anonimizador académico de uso personal (IALAB)

**Versión:** 3.3.10 · **Plataforma:** Windows 10/11 (64 bits) · **Uso:** personal / académico / institucional

---

## 1. Qué recibís

Un archivo ZIP, por ejemplo:

`AnonimizadorJudicial-NLP-PJ-v3.3.10.zip` (~130–200 MB)

Al descomprimirlo obtenés una carpeta con:

| Elemento | Función |
|----------|---------|
| `INICIAR.bat` | **Usá este** para abrir la aplicación |
| `AnonimizadorJudicial-NLP.exe` | Motor de la app (no hace falta abrirlo directo) |
| `VERIFICAR.bat` | Abre la página de comprobación técnica |
| `MANUAL_USUARIO.md` / `.txt` | Guía de uso |
| `LEEME_INSTALACION.txt` | Inicio rápido |
| `THIRD_PARTY_NOTICES.txt` | Licencias de software incluido |
| `LICENSES/` | Textos de licencia (GPL spaCy, MIT, BSD, etc.) |
| `COMPLIANCE.md` / `.txt` | Informe de cumplimiento para IT |
| `_internal/` | Librerías (no modificar) |
| `models/` | Modelo de lenguaje (no borrar) |

---

## 2. Requisitos del equipo

- Windows 10 u 11, 64 bits
- ~250–400 MB de espacio libre
- **No** requiere Python ni Internet para funcionar
- Navegador web (Chrome, Edge o Firefox)
- Permiso para ejecutar aplicaciones locales

---

## 3. Instalación paso a paso

### 3.1 Descomprimir

1. Descargá el ZIP completo.
2. Clic derecho → **Extraer todo…**
3. Elegí una carpeta fija, por ejemplo:
   - `C:\Programas\Anonimizador-IALAB\`
   - o `Documentos\Anonimizador-IALAB\`
4. **No** ejecutes el programa desde dentro del ZIP sin descomprimir.

### 3.2 Primera ejecución

1. Entrá a la carpeta descomprimida.
2. Doble clic en **`INICIAR.bat`**
3. Se abrirá el navegador en: http://127.0.0.1:8787
4. **No cierres** la ventana negra mientras uses la app (es el servidor local).

### 3.3 SmartScreen (Windows)

Si aparece “Windows protegió tu PC”:

1. Clic en **Más información**
2. **Ejecutar de todas formas**

Es normal en software académico sin certificado comercial.

### 3.4 Verificación

1. Ejecutá **`VERIFICAR.bat`** o abrí http://127.0.0.1:8787/health
2. Comprobá:
   - `"app_version": "3.3.10"`
   - `presidio.available`: true
   - `spacy.available`: true

---

## 4. Acceso directo (opcional)

1. Clic derecho en `INICIAR.bat` → **Enviar a** → **Escritorio (crear acceso directo)**
2. Renombrá el acceso directo: *Anonimizador IALAB*

---

## 5. Actualizar a una versión nueva

1. **Cerrá** la aplicación (ventana negra y navegador).
2. Descomprimí la **nueva** carpeta ZIP en otra ruta (ej. `Anonimizador-v3.3.10`).
3. Usá el `INICIAR.bat` **de la carpeta nueva**.
4. Podés borrar o renombrar la carpeta vieja (`_VIEJO`) para no confundirte.

> No es obligatorio borrar la versión anterior, pero **no abras las dos a la vez** (comparten el puerto 8787).

---

## 6. Problemas frecuentes

| Problema | Solución |
|----------|----------|
| No abre el navegador | Abrí manualmente http://127.0.0.1:8787 |
| “Puerto en uso” / no carga | Cerrá otras copias del anonimizador; reiniciá `INICIAR.bat` |
| Pantalla vieja / sin cambios | Estás en carpeta vieja; Ctrl+F5 o usá la carpeta nueva |
| Antivirus bloquea el .exe | Agregá excepción para la carpeta de instalación |
| Presidio/spaCy en false | Reinstalá descomprimiendo de nuevo el ZIP completo |
| PDF no carga | Solo PDF **digital** (texto seleccionable); no escaneos |

---

## 7. Privacidad

- Todo el procesamiento es **local** (127.0.0.1).
- **No** se envían documentos ni datos a servidores externos.
- **No** se requiere conexión a Internet (la interfaz usa fuentes del sistema).
- Los archivos de sesión quedan en la subcarpeta `data\` junto al programa (no vienen en el ZIP de instalación).

---

## 8. Licencias de software

El paquete incluye componentes de terceros (Presidio, spaCy, pdfplumber, ReportLab, etc.).

- Resumen: **`THIRD_PARTY_NOTICES.txt`**
- Textos legales: carpeta **`LICENSES/`**
- Informe para sistemas: **`COMPLIANCE.md`**

---

## 9. Soporte

Laboratorio de Innovación e Inteligencia Artificial (IALAB) — Facultad de Derecho, UBA.

Al reportar un error, indicá: versión (`/health`), Windows, tipo de archivo (Word/PDF) y captura de pantalla si es posible.
