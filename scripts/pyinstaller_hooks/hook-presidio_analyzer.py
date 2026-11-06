"""Keep Presidio configs and modules without duplicating Python source files."""
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all(
    'presidio_analyzer', include_py_files=False,
    filter_submodules=lambda name: not name.startswith(('presidio_analyzer.tests', 'presidio_analyzer.benchmarks')),
    exclude_datas=['**/tests/**', '**/benchmarks/**'],
)
