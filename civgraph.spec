# -*- mode: python ; coding: utf-8 -*-
"""
CivGraph PyInstaller spec file.

Builds a standalone executable bundling all Python modules,
static web assets, and dependencies.

Usage:
    pyinstaller civgraph.spec
"""

import os

block_cipher = None

# All Python source files to include
py_files = [
    'civgraph_app.py',
    'server.py',
    'model.py',
    'capital.py',
    'economy.py',
    'media.py',
    'health.py',
    'institutions.py',
    'agency.py',
    'transactions.py',
    'emergence.py',
    'environment.py',
    'events.py',
]

a = Analysis(
    ['civgraph_app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('static', 'static'),
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'starlette',
        'starlette.routing',
        'starlette.middleware',
        'starlette.staticfiles',
        'starlette.responses',
        'pydantic',
        'networkx',
        'server',
        'model',
        'capital',
        'economy',
        'media',
        'health',
        'institutions',
        'agency',
        'transactions',
        'emergence',
        'environment',
        'events',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'scipy',
        'pandas',
        'numpy',
        'playwright',
        'selenium',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='civgraph',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
