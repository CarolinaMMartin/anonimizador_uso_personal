# Manual de instalación — Anonimizador Judicial

**Plataformas publicadas:** Windows 10/11 (64 bits) y macOS · **Uso:** personal / académico

Esta es una **aplicación portable**: no es un instalador tradicional. No
modifica tu sistema y, en general, **no requiere permisos de
administrador** (salvo restricciones particulares de tu equipo o de tu
organización).

---

## 1. Qué recibís

Descargás desde **Releases** el archivo correspondiente a tu sistema:

- `AnonimizadorJudicial-Windows.zip` para Windows.
- `AnonimizadorJudicial-Mac` para macOS.

El tamaño exacto de cada descarga y el espacio que ocupa una vez extraída
se informan en la Release correspondiente.

El paquete incluye el programa, el modelo local, los manuales y los avisos
de licencia necesarios. No borres carpetas internas del paquete.

---

## 2. Requisitos del equipo

- Windows 10/11 de 64 bits o macOS.
- Espacio libre en disco indicado en la Release.
- Navegador web actual.
- **No** requiere Python ni Internet para funcionar.

---

## 3. Instalación en Windows

### 3.1 Extraer el ZIP

1. Descargá `AnonimizadorJudicial-Windows.zip` desde Releases.
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
cierra sola.

### 3.3 Si aparece SmartScreen

Windows puede mostrar el aviso “Windows protegió tu PC” porque la
aplicación académica no tiene una firma comercial:

1. Clic en **Más información**.
2. Clic en **Ejecutar de todas formas**.

---

## 4. Instalación en macOS

1. Descargá **`AnonimizadorJudicial-Mac`** desde Releases.
2. Descomprimí el archivo completo.
3. Abrí la carpeta extraída.
4. La primera vez, hacé clic derecho en **`INICIAR.command`** y elegí
   **Abrir**.
5. Confirmá nuevamente con **Abrir** si macOS muestra una advertencia.
6. La aplicación se abre en <http://127.0.0.1:8787>.

Si macOS bloquea la apertura, revisá **Configuración del Sistema →
Privacidad y seguridad** y autorizá la aplicación descargada.

No muevas `INICIAR.command` fuera de la carpeta extraída: necesita los
demás archivos del paquete.

---

## 5. Verificar funcionamiento y versión

La parte superior de la aplicación muestra el estado del motor local y la
versión instalada, por ejemplo:

```text
100% local v3.3.11 · Presidio · spaCy
```

Para una verificación técnica también podés abrir
<http://127.0.0.1:8787/health> y comprobar:

- `app_version`: versión instalada.
- `presidio.available`: `true`.
- `spacy.available`: `true`.

Compará `app_version` con la **última versión** indicada en el README o en
[GitHub Releases](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/latest).
Si coinciden, tenés la versión más reciente.

En Windows también podés ejecutar `VERIFICAR.bat`; en macOS,
`VERIFICAR.command`.

---

## 6. Cómo cerrar completamente la aplicación

Cerrar solo la pestaña del navegador puede no detener el programa que se
ejecuta por detrás.

### Windows

1. Cerrá la pestaña del navegador.
2. Abrí el **Administrador de tareas** (`Ctrl + Shift + Esc`).
3. Buscá `AnonimizadorJudicial-NLP.exe`.
4. Elegí **Finalizar tarea**.

Volver a ejecutar `INICIAR.bat` también cierra una copia anterior del
anonimizador antes de abrir una nueva.

### macOS

1. Cerrá la pestaña del navegador.
2. Abrí **Monitor de Actividad**.
3. Buscá `AnonimizadorJudicial-NLP`.
4. Seleccionalo y elegí **Salir** o **Forzar salida**.

---

## 7. Actualizar a una versión nueva

1. Cerrá completamente la aplicación.
2. Descargá otra vez el archivo correspondiente a tu sistema desde
   Releases.
3. Extraelo en **otra carpeta**.
4. Abrí la aplicación desde la carpeta nueva.
5. Verificá la versión mostrada en la parte superior.

No abras dos versiones a la vez: ambas utilizan el puerto 8787.

---

## 8. Problemas frecuentes

| Problema | Solución |
|----------|----------|
| No abre el navegador | Abrí manualmente <http://127.0.0.1:8787> |
| “Puerto en uso” | Cerrá otras copias del anonimizador y volvé a abrir |
| Pantalla vieja o sin cambios | Usá la carpeta de la descarga más reciente |
| Antivirus o macOS bloquean el programa | Autorizá la aplicación desde las opciones de seguridad del sistema |
| `presidio` o `spacy` aparecen en `false` | Volvé a extraer el paquete completo |
| El PDF no carga | Solo se admiten PDF digitales con texto seleccionable |

---

## 9. Privacidad

- Todo el procesamiento es **local** (`127.0.0.1`).
- **No** se envían documentos ni datos a servidores externos.
- **No** se requiere conexión a Internet.
- Las sesiones viven **solo en memoria**: el texto del documento no se
  guarda en disco y se pierde al cerrar la aplicación.

---

## 10. Licencias

El paquete incluye componentes de terceros como Presidio, spaCy,
pdfplumber y ReportLab.

- Resumen: `THIRD_PARTY_NOTICES.txt`.
- Textos legales: carpeta `LICENSES/`.
- Informe de cumplimiento: `COMPLIANCE.md`.
