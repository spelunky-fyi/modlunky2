# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['pyinstaller-cli.py'],
             pathex=['.'],
             binaries=[],
             datas=[('src/modlunky2/tilecodes.txt', '.'), ('VERSION', '.'), ('src/modlunky2/static', 'static')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='modlunky2',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False , icon='src\\modlunky2\\static\\images\\icon.ico')
