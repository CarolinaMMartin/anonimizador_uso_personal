"""Collect thinc runtime resources while leaving development tests out."""
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all(
    'thinc', include_py_files=False,
    filter_submodules=lambda name: not name.startswith(('thinc.tests', 'thinc.benchmarks')),
    exclude_datas=['**/tests/**', '**/benchmarks/**'],
)
