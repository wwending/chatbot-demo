# Build with:
# python -m PyInstaller chatbot-demo.spec --clean --noconfirm

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


ROOT = Path.cwd()


datas = []
knowledge_dir = ROOT / "knowledge"
if knowledge_dir.exists():
    datas.append((str(knowledge_dir), "knowledge"))

hiddenimports = collect_submodules("app")


a = Analysis(
    ["launch_desktop.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="chatbot-demo",
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
)
