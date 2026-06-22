# Manual de instalación — Anonimizador Judicial

**Plataforma:** Windows 10/11 (64 bits) · **Uso:** personal / académico

Esta es una **aplicación portable**: no es un instalador tradicional. No
modifica tu sistema y, en general, **no requiere permisos de
administrador** (salvo restricciones particulares de tu equipo o de tu
organización).

---

## 1. Qué recibís

Un archivo ZIP que descargás desde **Releases**. El tamaño exacto de la
descarga y el espacio que ocupa una vez extraído se informan en cada
Release.

Al extraerlo obtenés una carpeta con, entre otros:

| Elemento | Función |
|----------|---------|
| `INICIAR.bat` | **Usá este** para abrir la aplicación |
| `AnonimizadorJudicial-NLP.exe` | Programa principal (no hace falta abrirlo directo) |
| `VERIFICAR.bat` | Abre la página de comprobación |
| `MANUAL_USUARIO.md` / `.txt` | Guía de uso |
| `LEEME_INSTALACION.txt` | Inicio rápido |
| `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.txt`, `LICENSES/` | Licencias |
| `models/` | Modelo de lenguaje (no borrar) |
| `_internal/` | Archivos del programa (no modificar) |

---

## 2. Requisitos del equipo

- Windows 10 u 11, 64 bits.
- Espacio libre en disco (ver el dato indicado en la Release).
- Navegador web (Edge, Chrome o Firefox).
- **No** requiere Python ni Internet para funcionar.

---

## 3. Instalación paso a paso

### 3.1 Extraer el ZIP

1. Descargá el ZIP completo desde Releases.
2. Clic derecho sobre el ZIP → **Extraer todo…**
3. Elegí una carpeta fija, por ejemplo:
   - `C:\Programas\Anonimizador\`
   - o `Documentos\Anonimizador\`
4. **No ejecutes el programa desde dentro del ZIP.** Primero hay que
   extraerlo.

### 3.2 Abrir la aplicación

1. Entrá a la carpeta extraída.
2. Doble clic en **`INICIAR.bat`**.
3. Se abre el navegador en <http://127.0.0.1:8787>.

Durante el inicio puede aparecer brevemente una ventana; es normal y se
cierra sola. No necesitás dejar ninguna ventana abierta para usar la
aplicación.

### 3.3 Si aparece SmartScreen

Windows puede mostrar un aviso ("Windows protegió tu PC") porque la
aplicación no tiene una firma comercial:

1. Clic en **Más información**.
2. Clic en **Ejecutar de todas formas**.

Es habitual en aplicaciones académicas sin certificado de pago.

### 3.4 Verificación

1. Ejecutá **`VERIFICAR.bat`** o abrí <http://127.0.0.1:8787/health>.
2. Comprobá que aparezcan `presidio` y `spacy` en `true`.

---

## 4. Cómo cerrar completamente la aplicación

La aplicación tiene dos partes: la **pestaña del navegador** y el
**programa** que corre por detrás.

**Cerrar solo la pestaña del navegador puede no detener el programa.**

Para cerrarlo del todo:

1. Cerrá la pestaña del navegador.
2. Abrí el **Administrador de tareas** (`Ctrl + Shift + Esc`).
3. Buscá **`AnonimizadorJudicial-NLP.exe`** en la lista.
4. Seleccionalo y elegí **Finalizar tarea**.

Volver a hacer doble clic en `INICIAR.bat` también cierra la copia
anterior antes de abrir una nueva.

---

## 5. Actualizar a una versión nueva

1. Cerrá la aplicación (ver punto 4).
2. Descargá el ZIP nuevo desde Releases.
3. Extraelo en **otra carpeta** (por ejemplo, una carpeta con el número
   de versión).
4. Usá el `INICIAR.bat` **de la carpeta nueva**.

No abras dos versiones a la vez: ambas usan el mismo puerto (8787).

---

## 6. Problemas frecuentes

| Problema | Solución |
|----------|----------|
| No abre el navegador | Abrí manualmente <http://127.0.0.1:8787> |
| "Puerto en uso" | Cerrá otras copias del anonimizador (ver punto 4) y volvé a abrir |
| Pantalla vieja / sin cambios | Estás en una carpeta vieja; usá la carpeta nueva |
| Antivirus bloquea el programa | Agregá una excepción para la carpeta |
| `presidio`/`spacy` en false | Volvé a extraer el ZIP completo |
| El PDF no carga | Solo PDF **digital** (con texto seleccionable); no escaneos |

---

## 7. Privacidad

- Todo el procesamiento es **local** (127.0.0.1).
- **No** se envían documentos ni datos a servidores externos.
- **No** se requiere conexión a Internet.
- Las sesiones viven **solo en memoria**: el texto del documento no se
  guarda en disco y se pierde al cerrar la aplicación.

---

## 8. Licencias

El paquete incluye componentes de terceros (Presidio, spaCy, pdfplumber,
ReportLab, etc.).

- Resumen: **`THIRD_PARTY_NOTICES.txt`**
- Textos legales: carpeta **`LICENSES/`**
- Informe de cumplimiento: **`COMPLIANCE.md`**
