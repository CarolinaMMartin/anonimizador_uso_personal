# Anonimizador Judicial

[![Licencia Apache 2.0](https://img.shields.io/badge/licencia-Apache_2.0-blue.svg)](LICENSE)
[![Última versión publicada](https://img.shields.io/github/v/release/CarolinaMMartin/anonimizador_uso_personal?label=%C3%BAltima%20publicaci%C3%B3n)](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/latest)
[![Procesamiento local](https://img.shields.io/badge/procesamiento-100%25%20local-success.svg)](#privacidad)

Aplicación de uso personal y académico para anonimizar documentos judiciales
argentinos. Combina expresiones regulares, Microsoft Presidio y spaCy con
revisión humana y exportación Word, PDF, CSV y Markdown. Los documentos se
procesan en el equipo del usuario.

**Versión del código: 3.3.12.** Cambios y limitaciones en
[CHANGELOG.md](CHANGELOG.md). La versión publicada y los archivos disponibles
para cada plataforma se consultan en [Releases](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases).

## Descargar y abrir

### Windows 10/11 de 64 bits

[Descargar el ZIP portable para Windows](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/latest/download/AnonimizadorJudicial-Windows.zip)

1. Descargá el ZIP desde Releases y elegí **Extraer todo**.
2. Abrí la carpeta extraída y ejecutá **INICIAR.bat**.
3. Verificá la versión que aparece junto al indicador **100% local**.

No requiere instalar Python ni conectarse a Internet para procesar documentos.
El inicio usa 127.0.0.1:8787 o un puerto libre entre 8788 y 8796. Repetir el
inicio abre la instancia de esa carpeta y conserva las otras copias abiertas.
**VERIFICAR.bat** encuentra el puerto de esa misma versión.

### macOS

La entrega 3.3.12 se verifica en Windows. Una compilación de macOS debe
construirse y probarse en una Mac antes de publicarse. Las descargas anteriores
de macOS permanecen en su [Release correspondiente](https://github.com/CarolinaMMartin/anonimizador_uso_personal/releases/tag/v3.3.11)
y conservan la versión de ese paquete.

**Code → Download ZIP** descarga los fuentes, no la aplicación portable.
Instrucciones completas: [instalación](docs/MANUAL_INSTALACION.md) y
[uso](docs/MANUAL_USUARIO.md).

## Flujo de uso

1. Cargar un Word .docx o PDF digital con texto seleccionable, de hasta 40 MB.
2. Elegir categorías y modo de sustitución, analizar y revisar los hallazgos.
3. Confirmar las variantes que pertenecen a una misma identidad; las ambiguas
   requieren revisar el contexto y pueden permanecer separadas.
4. Abrir el editor, verificar el texto y exportar Word, PDF, CSV o Markdown.

## Funcionalidades

- Personas, DNI, CUIT/CUIL, empresas, emails, teléfonos, domicilios, patentes,
  expedientes y organismos. Expedientes se desactiva por defecto en la interfaz.
- Nombres en mayúsculas, tildes, firmas, compuestos, orden con coma e iniciales.
- Búsqueda de referencias cortas a partir de nombres completos detectados en
  el documento, incluidos apellidos fuera del catálogo.
- Propuestas de identidad con control de ambigüedad, confirmación, separación y
  rechazo; las variantes confirmadas comparten su sustitución.
- Edición de tipos y sustituciones, activación de filas y agregado manual desde
  la selección o la búsqueda de texto en la vista previa.
- Tres modos: categorizado ([PERSONA_1]), genérico ([NOMBRE]) e iniciales.
- Extracción Word de párrafos, tablas, encabezados y pies; PDF digital y mixto.
- Editor final con formato y exportaciones coherentes con la revisión guardada.

La búsqueda a partir de una **persona ingresada por el usuario** es una
propuesta para una próxima versión; no forma parte de 3.3.12. Ver
[el diseño pendiente](docs/propuestas/PERSONAS_CONOCIDAS.md).

## Privacidad

- El servidor escucha solamente en 127.0.0.1.
- El procesamiento no llama a servicios en la nube ni usa CDN o telemetría.
- La instancia de uso personal conserva las sesiones **solo en memoria**;
  no crea una base SQLite ni guarda el texto extraído en disco.
- Cerrar la pestaña del navegador puede dejar el proceso abierto. Al terminar
  ese proceso se pierden sus sesiones: guardá las exportaciones antes de cerrarlo.
- Word, PDF, CSV y Markdown descargados son archivos que el usuario guarda.
  El CSV de equivalencias contiene datos originales y debe tratarse como tal.

## Limitaciones

- No incluye OCR: las páginas de un PDF sin texto digital se omiten. Word con
  texto en imágenes, dibujos, notas o revisiones pendientes requiere verificación.
- La detección es heurística y necesita revisión antes de compartir el resultado.
- Las referencias aprendidas requieren un nombre completo detectado como
  evidencia; no identifican automáticamente menciones ambiguas.
- Las exportaciones reconstruyen el texto y no conservan el diseño original.
  La fuente elegida se aplica a Word; el PDF usa Times Roman. Tamaño,
  interlineado, alineación y márgenes se aplican a ambos formatos.
- Las ediciones del editor no se vuelven a analizar ni cambian el CSV.

## Desarrollo

Python 3.11–3.13. La entrega Windows se valida con Python 3.13.15 de 64 bits.

```powershell
git clone https://github.com/CarolinaMMartin/anonimizador_uso_personal.git
cd anonimizador_uso_personal
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python.exe scripts\install_nlp.py
.venv\Scripts\python.exe scripts\run_dev.py
```

En macOS/Linux, usar .venv/bin/python. También hay lanzadores de desarrollo
INICIAR_DESARROLLO.bat y INICIAR_DESARROLLO.sh. Estos conservan los procesos
abiertos y eligen un puerto disponible. Se puede especificar ANON_PORT.

La respuesta de /health informa app_version, frontend_dir y nlp_layers.
Los estados son nlp_layers.presidio.available, nlp_layers.spacy.available y
nlp_layers.dictionaries; no campos booleanos en la raíz de la respuesta.

```powershell
.venv\Scripts\python.exe -m pytest tests -q
node --test tests/frontend_session.test.cjs
.venv\Scripts\python.exe scripts\audit_repository.py
```

Los tests de estructura del portable se omiten si todavía no se compiló.
Después del build deben ejecutarse con ANON_PKG_DIR apuntando al paquete;
la entrega exige que pasen sin omisiones. Node solo se usa para pruebas.

Arquitectura: FastAPI/Uvicorn; HTML/CSS/JavaScript locales; regex + Presidio +
spaCy es_core_news_md; identidad personal por estructura y candidatos únicos;
similitud RapidFuzz y grafo NetworkX para otras categorías; pdfplumber para
leer PDF y ReportLab/python-docx para exportar.

Para compilar y publicar: [DEPLOY.md](docs/DEPLOY.md) y
[RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md). Dependencias fijadas en
requirements.txt y requirements-dev.txt; inventario del entorno Windows
en [docs/dependencies-frozen.txt](docs/dependencies-frozen.txt).

## Contribuciones y licencias

Ver [CONTRIBUTING.md](CONTRIBUTING.md) y [SECURITY.md](SECURITY.md).

- Código: [Apache 2.0](LICENSE).
- Componentes: [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt) y [LICENSES](LICENSES/).
- Modelo spaCy: GPL-3.0, incluido con su licencia en el portable; sus pesos
  permanecen fuera del historial Git.
- Logo y nombre IALAB: marcas institucionales sujetas a [NOTICE](NOTICE).

Desarrollado por IALAB — Laboratorio de Innovación e Inteligencia Artificial,
Facultad de Derecho, Universidad de Buenos Aires.
