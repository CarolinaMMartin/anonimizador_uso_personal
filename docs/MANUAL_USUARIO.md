# Manual de usuario — Anonimizador académico de uso personal (IALAB)

**Versión:** 3.3.10

---

## 1. Qué hace esta herramienta

**Detección automatizada de datos personales.** Controlá, editá y luego descargá el documento anonimizado.

La anonimización se realiza **local en tu PC personal**. No se envían datos ni información a servidores externos.

Detecta automáticamente (entre otros):

- Personas, DNI, CUIT/CUIL
- Emails, teléfonos, domicilios
- Empresas y organismos judiciales (configurable)

Reemplaza cada dato por una etiqueta (ej. `[PERSONA_1]`, `[DNI_1]`) y permite exportar Word, PDF y tabla CSV.

---

## 2. Cómo iniciar

1. Doble clic en **`INICIAR.bat`**
2. Se abre http://127.0.0.1:8787 en el navegador
3. El indicador superior debe mostrar: `100% local v3.3.10 · Presidio · spaCy`

---

## 3. Flujo de trabajo (4 pasos)

### Paso 1 — Cargar documento

- Formatos: **Word (.docx)** o **PDF digital** (con texto seleccionable).
- Arrastrá el archivo o hacé clic en la zona de carga.
- **No** se procesan PDFs escaneados (solo PDF con texto seleccionable o Word).

**Tip:** Si el PDF es escaneado, convertilo antes a Word o a PDF con capa de texto.

### Paso 2 — Configurar y analizar

- **Modo de etiquetado:**
  - *Categorizado:* `[PERSONA_1]`, `[DNI_1]`… (recomendado si exportás CSV)
  - *Genérico:* `[NOMBRE]`, `[DNI]`…
  - *Iniciales:* reemplazo por iniciales
- **Categorías:** marcá qué tipos de datos buscar.
- Clic en **Analizar documento**.

### Paso 3 — Revisar

Dos pestañas:

- **Detecciones:** lista de hallazgos; podés activar/desactivar, cambiar tipo, unir similares o ignorar.
- **Grupos:** agrupa variantes del mismo dato (ej. mismo nombre escrito distinto).

**Vista previa:** texto original vs. anonimizado con colores por categoría.

**Selección manual:** podés marcar texto en la vista previa y agregar una detección.

### Paso 4 — Verificar y exportar

1. Clic en **Abrir editor y verificar**
2. Revisá y editá el texto anonimizado si hace falta
3. Ajustá formato (fuente, tamaño, interlineado, márgenes, alineación)
4. **Exportar Word** o **Exportar PDF**
5. **Tabla CSV** (equivalencias original → reemplazo) se descarga aparte en el paso 4

> **Atención:** al editar manualmente no restaures datos personales reales.

---

## 4. Consejos para mejores resultados

| Situación | Recomendación |
|-----------|---------------|
| Nombre no detectado | Agregalo manualmente en la vista previa |
| Falso positivo | Desactivá la detección o usá *Ignorar similares* |
| Mismo dato repetido | Revisá **Grupos** y confirmá el cluster |
| Monto confundido con DNI | Revisá y desactivá esa detección |
| Documento largo | Analizar puede tardar unos segundos (motor NLP local) |

---

## 5. Exportaciones

| Archivo | Contenido |
|---------|-----------|
| Word (.docx) | Documento anonimizado con formato elegido |
| PDF | Misma versión en PDF |
| CSV | Tabla de equivalencias (original → etiqueta) |

---

## 6. Privacidad y uso responsable

- Uso **personal y académico** (prototipo IALAB).
- Procesamiento 100 % local.
- Revisá siempre antes de exportar: la detección automática **no es perfecta**.
- No compartas el documento anonimizado sin revisar que no queden datos sensibles.

---

## 7. Cerrar la aplicación

1. Cerrá la pestaña del navegador
2. Cerrá la ventana negra del servidor (o dejala abierta si seguís trabajando)

Para volver a usar: ejecutá de nuevo **`INICIAR.bat`**.

---

## 8. Glosario breve

| Término | Significado |
|---------|-------------|
| Detección | Dato personal identificado automáticamente |
| Placeholder / etiqueta | Texto de reemplazo, ej. `[PERSONA_1]` |
| Cluster / grupo | Varias apariciones del mismo dato unificadas |
| Presidio / spaCy | Motores de análisis de texto (corren en tu PC) |

---

## 9. Checklist rápido antes de entregar un documento anonimizado

- [ ] Revisé todas las detecciones activas
- [ ] Revisé grupos sugeridos importantes
- [ ] Leí el texto en el editor de verificación
- [ ] Exporté Word o PDF
- [ ] No quedaron nombres, DNI, domicilios ni mails visibles
