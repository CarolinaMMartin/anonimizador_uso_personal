# Desarrollo del anonimizador

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

Para compilar y publicar: [DEPLOY.md](DEPLOY.md) y
[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md). Dependencias fijadas en
requirements.txt y requirements-dev.txt; inventario del entorno Windows
en [dependencies-frozen.txt](dependencies-frozen.txt).

