# Manual de usuario — Anonimizador de uso personal

Herramienta académica de uso personal (IALAB).

---

## 1. Qué hace esta herramienta

**Detección automatizada de datos personales.** Controlá, editá y luego
descargá el documento anonimizado.

La anonimización se realiza **localmente en tu equipo**. No se envían
datos ni información a servidores externos.

Detecta automáticamente, entre otros:

- Personas, DNI y CUIT/CUIL.
- Emails, teléfonos y domicilios.
- Empresas y organismos judiciales.

Reemplaza cada dato por una etiqueta, por ejemplo `[PERSONA_1]` o
`[DNI_1]`, y permite exportar Word, PDF, CSV y Markdown.

---

## 2. Cómo iniciar

### Windows

1. Doble clic en **`INICIAR.bat`**.
2. Se abre <http://127.0.0.1:8787> en el navegador.

### macOS

1. La primera vez, clic derecho en **`INICIAR.command`** → **Abrir**.
2. Se abre <http://127.0.0.1:8787> en el navegador.

El indicador superior debe mostrar algo similar a:

```text
100% local vX.Y.Z · Presidio · spaCy
```

`vX.Y.Z` es la versión instalada. Podés compararla con la insignia
**“última versión”** del README o con la versión publicada en
[Releases](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/latest).

---

## 3. Flujo de trabajo

### Paso 1 — Cargar documento

- Formatos: **Word (.docx)** o **PDF digital** con texto seleccionable.
- Arrastrá el archivo o hacé clic en la zona de carga.
- No se procesan PDFs completamente escaneados.

**Consejo:** si el PDF es una imagen, convertilo antes a Word o a PDF con
capa de texto.

### Paso 2 — Configurar y analizar

- **Modo categorizado:** `[PERSONA_1]`, `[DNI_1]`.
- **Modo genérico:** `[NOMBRE]`, `[DNI]`.
- **Modo iniciales:** reemplaza nombres por iniciales.
- Marcá las categorías que querés buscar.
- Hacé clic en **Analizar documento**.

### Paso 3 — Revisar

La revisión tiene dos pestañas:

- **Detecciones:** permite activar, desactivar, cambiar tipo, editar o unir
  hallazgos.
- **Identidades o grupos:** reúne variantes que podrían corresponder al
  mismo dato.

En la vista previa podés comparar el texto original con el anonimizado y
seleccionar manualmente información que no haya sido detectada.

### Paso 4 — Verificar y exportar

1. Hacé clic en **Abrir editor y verificar**.
2. Leé y corregí el texto anonimizado.
3. Ajustá fuente, tamaño, interlineado, márgenes o alineación.
4. Exportá a Word o PDF.
5. Descargá la tabla CSV de equivalencias si la necesitás.

> **Atención:** al editar manualmente, no restaures datos personales
> reales por error.

---

## 4. Consejos para mejores resultados

| Situación | Recomendación |
|-----------|---------------|
| Nombre no detectado | Agregalo manualmente desde la vista previa |
| Falso positivo | Desactivá la detección o usá “Ignorar similares” |
| Mismo dato repetido | Revisá la pestaña de grupos |
| Monto confundido con DNI | Revisá y desactivá esa detección |
| Documento largo | El análisis puede tardar unos segundos porque se ejecuta localmente |

---

## 5. Exportaciones

| Archivo | Contenido |
|---------|-----------|
| Word (.docx) | Documento anonimizado con el formato elegido |
| PDF | Documento anonimizado en formato PDF |
| CSV | Tabla de equivalencias entre original y etiqueta |
| Markdown | Texto anonimizado fácil de copiar en otra herramienta |

---

## 6. Privacidad y uso responsable

- Uso **personal y académico**.
- Procesamiento 100 % local.
- Las sesiones viven **solo en memoria**: el texto del documento no se
  guarda en disco y se pierde al cerrar la aplicación.
- La detección automática **no es perfecta**.
- Revisá siempre el resultado antes de compartirlo.
- No publiques documentos reales, datos personales ni capturas sensibles
  en Issues o reportes de errores.

---

## 7. Cerrar la aplicación

Cerrar solo la pestaña del navegador puede no detener el programa que se
ejecuta por detrás.

### Windows

1. Cerrá la pestaña del navegador.
2. Abrí el Administrador de tareas (`Ctrl + Shift + Esc`).
3. Buscá `AnonimizadorJudicial-NLP.exe`.
4. Elegí **Finalizar tarea**.

Volver a ejecutar `INICIAR.bat` también cierra una copia anterior antes de
abrir una nueva.

### macOS

1. Cerrá la pestaña del navegador.
2. Abrí **Monitor de Actividad**.
3. Buscá `AnonimizadorJudicial-NLP`.
4. Elegí **Salir** o **Forzar salida**.

---

## 8. Glosario breve

| Término | Significado |
|---------|-------------|
| Detección | Dato personal identificado automáticamente |
| Placeholder o etiqueta | Texto de reemplazo, por ejemplo `[PERSONA_1]` |
| Cluster o grupo | Varias apariciones posiblemente pertenecientes al mismo dato |
| Presidio / spaCy | Motores de análisis de texto que corren localmente |

---

## 9. Checklist antes de compartir un documento

- [ ] Revisé todas las detecciones activas.
- [ ] Revisé los grupos sugeridos importantes.
- [ ] Leí el texto completo en el editor de verificación.
- [ ] Exporté el archivo correcto.
- [ ] Confirmé que no quedaron nombres, DNI, domicilios ni emails visibles.
