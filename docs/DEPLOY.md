# Guía de despliegue empaquetado (ZIP portable)

Esta guía describe cómo construir y entregar el Anonimizador Judicial
como un **ZIP portable**, listo para usuarios que no pueden (o no
quieren) instalar Python, pip, spaCy ni dependencias en su PC.

El paquete publicado y probado es **Windows 10/11 de 64 bits**. El build
de macOS existe para desarrollo, pero no se publica como descarga para
usuarios finales mientras no haya un paquete probado.

**Versión vigente:** ver `app_version` en <http://127.0.0.1:8787/health>.
Para el flujo completo de publicación, ver
[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

---

## 1. Qué recibe el usuario final

Un único archivo ZIP. **No requiere instalar nada en la PC.**

Contenido principal del paquete descomprimido:

| Elemento | Función |
|----------|---------|
| `INICIAR.bat` (Windows) / `INICIAR.command` (macOS dev) | Inicia la aplicación |
| `AnonimizadorJudicial-NLP.exe` | Motor empaquetado (PyInstaller) |
| `_internal/` | Librerías embebidas |
| `models/es_core_news_md/` | Modelo spaCy + `LICENSE` (GPL-3.0) |
| `LICENSE` | Apache 2.0 del código de la app |
| `NOTICE` | Copyright + nota de marca registrada |
| `THIRD_PARTY_NOTICES.txt` | Inventario de licencias |
| `LICENSES/` | Textos completos de licencias de terceros |
| `LEEME_INSTALACION.txt` | Guía rápida (3 pasos) |
| `MANUAL_INSTALACION.md` | Guía detallada + problemas frecuentes |
| `MANUAL_USUARIO.md` | Cómo usar la herramienta |

---

## 2. Instalación en la PC del usuario (3 pasos)

1. Descomprimir el ZIP en una carpeta fija (por ejemplo, `Documentos\Anonimizador`). **No** ejecutar desde dentro del ZIP.
2. Doble clic en **`INICIAR.bat`** (Windows). En el build de desarrollo para macOS, **`INICIAR.command`**.
3. Abrir el navegador en <http://127.0.0.1:8787>.

**No hay pasos de consola, ni pip, ni permisos de administrador**, salvo
que el antivirus exija una excepción la primera vez.

---

## 3. Verificación IT (post-instalación)

1. Abrir <http://127.0.0.1:8787/health>.
2. Confirmar que el JSON devuelva:
   - `presidio.available`: `true`
   - `spacy.available`: `true`
3. **Probar en red aislada (sin Internet).** La app no debe colgarse al
   detectar emails ni intentar resolver `publicsuffix.org` (ver
   [COMPLIANCE.md](COMPLIANCE.md#presidio-y-red-tldextract--resuelto)).
4. Confirmar presencia de:
   - `THIRD_PARTY_NOTICES.txt`
   - `models/es_core_news_md/LICENSE`
   - `NOTICE`

Checklist completo de cumplimiento: [COMPLIANCE.md](COMPLIANCE.md).

---

## 4. Generación del ZIP (sólo equipo de desarrollo)

Estos comandos **no** van en el manual del usuario final; son para quien
construye el paquete.

```powershell
# 0) Entorno limpio (recomendado para builds reproducibles).
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

# 1) Bajar el modelo spaCy local.
.venv\Scripts\python scripts\install_nlp.py

# 2) Compilar el .exe portable con PyInstaller + recursos embebidos.
.venv\Scripts\python scripts\build_portable_full.py

# 3) Empaquetar el ZIP final con sufijo de versión / plataforma.
.venv\Scripts\python scripts\package_release.py --suffix v3.3.10-Windows-x64
```

El sufijo `--suffix` se usa para identificar la entrega (por versión, por
cliente o por entorno). Ejemplos:

- `--suffix v3.3.10-Windows-x64` → `AnonimizadorJudicial-NLP-v3.3.10-Windows-x64.zip`
- `--suffix interno-2026Q2` → para releases internas
- `--suffix demo` → versión de prueba

El ZIP queda en `dist/`.

---

## 5. Personalización para cada organización

Cosas que conviene revisar/ajustar antes de entregar el ZIP a una
organización específica:

- **Logo y marca.** El logo `IALAB` está en `frontend/logo-ialab.svg/.png`.
  Si tu organización tiene autorización para usarlo, puede quedar; si
  no, reemplazalo (ver [NOTICE](../NOTICE)).
- **Email de contacto / soporte.** Editar `MANUAL_USUARIO.md` y
  `LEEME_INSTALACION.txt` con el canal de soporte del área que recibe la
  herramienta.
- **Diccionarios locales.** Si la organización tiene listas propias de
  nombres / apellidos / fórmulas, agregarlas en `data/dictionaries/` antes
  de empaquetar.
- **Regex específicos.** El catálogo `regex_limpio_v2.json` se puede
  extender con patrones internos (número de expediente con prefijo
  particular, código de tribunal, etc.) sin tocar código fuente.
- **Texto del README institucional.** Si la entrega es a un organismo
  con identidad propia, generar un `README_<organismo>.md` que se
  copia a la raíz del ZIP en `package_release.py`.

---

## 6. Distribución y soporte

- **Tamaño del ZIP.** Medir el tamaño real de descarga y descomprimido
  del build verificado e indicarlo en cada Release (no fijar un número
  en la documentación para evitar datos contradictorios).
- **Hash de verificación.** Calcular y publicar el SHA-256 del ZIP junto
  al binario para que IT pueda verificar integridad.
- **Updates.** Para actualizar, el usuario descomprime el ZIP nuevo en
  otra carpeta y usa esa carpeta (ver `MANUAL_INSTALACION.md`).
- **Soporte de incidentes.** Ver [SECURITY.md](../SECURITY.md) para
  reporte de vulnerabilidades y `MANUAL_INSTALACION.md` para
  troubleshooting de usuario.
