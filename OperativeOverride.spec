# Portable source-review build; identical release configuration.
from pathlib import Path
root = Path(SPECPATH)
a = Analysis(
    [str(root / 'studio.py')],
    pathex=[str(root)], binaries=[], datas=[], hiddenimports=[],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['subprocess', 'socket', 'ssl', 'http', 'csv', 'unittest',
              'multiprocessing', '_wmi', 'decimal', '_decimal',
              'bz2', '_bz2', 'lzma', '_lzma'],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name='OperativeOverride', debug=False, bootloader_ignore_signals=False,
          strip=False, upx=False, console=False, disable_windowed_traceback=False,
          argv_emulation=False, target_arch=None, codesign_identity=None,
          entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False,
               upx_exclude=[], name='OperativeOverride')
