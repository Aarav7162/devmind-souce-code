# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run_devmind.py'],
    pathex=[],
    binaries=[],
    datas=[('devmind/ui', 'devmind/ui')],
    hiddenimports=['click', 'psutil', 'webview', 'ecdsa', 'rich', 'pygame', 'ctypes', 'hashlib', 'uuid', 'msvcrt', 'json', 'math', 'subprocess'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='devmind',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['release/logo.ico'],
)
