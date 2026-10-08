# Build and source review

This contains the source of Operative Override v1.0's audited Nexus release candidate. All five Python code modules were compared with their code objects extracted from the released executable and matched. No game binaries, personal saves, presets, backup history, experiments or packaged executable are included.

## Prerequisites

- Windows x64.
- 64-bit CPython 3.12; the release used 3.12.14.
- Internet access for installing the pinned build dependencies from PyPI.
- Tkinter support (included in the normal Windows Python installer).

## Build

Extract the entire source archive. From that folder, run `./build.ps1` in PowerShell. It creates a local virtual environment and builds a folder distribution, with UPX and debug mode disabled. It does not install into the game or change its files. No administrator rights are requested.

If local script policy prevents running the script, use the equivalent commands below rather than changing that policy:

```
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm --distpath dist --workpath build OperativeOverride.spec
```

Then copy catalog.json, build-profile.json and HOW-TO.txt beside `dist/OperativeOverride/OperativeOverride.exe`. Keep its `_internal` folder. Build dependencies are tools for packaging, not dependencies installed by the released app.

This reproduces the source and build configuration; byte-for-byte executable hashes are not guaranteed across environments, paths and timestamps. The original release was built on Windows 11 x64, CPython 3.12.14, PyInstaller 6.22.3, hooks 2026.8. Pinned dependency versions are included. No signing certificate was used.

## Source map

- studio.py: Tk GUI, HOW TO, inactive confirmation and edit actions.
- studio_backend.py: game build fingerprint, bounded process access, cosmetic transactions, backup/Undo/Restore.
- process_lookup.py: native Windows process and module enumeration; no PowerShell/subprocess.
- wardrobe.py: preset validation, same-operative/body checks and clothing bit editing.
- field_guide.py: unchanged in-app field guide text.
- catalog.json: factual game identifiers and labels used by controls.
- build-profile.json: supported DX11 module fingerprint and lookup offsets.

## Required process access

The tool discovers WatchDogsLegion.exe and its DX11 module using Toolhelp snapshots. It verifies the DLL fingerprint. Read-only connections request 0x410 (QUERY_INFORMATION | VM_READ); edit connections request 0x438 (those plus VM_OPERATION | VM_WRITE). ReadProcessMemory and WriteProcessMemory are required for live customization. The code does not request ALL_ACCESS or enable debug privileges, inject DLLs, create remote threads, patch executable code or contact a network service.

Supported writes affect appearance/defaults, gender and general/NPC voice data. Wardrobe transactions change known clothing bits. Recovery data is stored locally. Supported transactions create verified backup copies, verify writes and roll back failures. No encrypted save rewriting is implemented.

Current release candidate EXE SHA256:
e5db596975cd4177da28b3b4a45ff6cd753724af9ba30fcd9be6800dbb972a4d

## Review limitations and references

The latest supplied VirusTotal screenshot reported 4/71 findings: Arctic Wolf Unsafe; SecureAge Malicious; Skyhigh BehavesLike.Win64.Backdoor.tc; Zillya Trojan.Blank.Script.2228. We do not claim a clean scan or prove these are false positives. A live regression check of native game discovery remains appropriate before broader distribution. Build/source checks alone do not prove every runtime behavior.

Factual structure/signature research used the Watch Dogs: Legion community SDK (https://github.com/Serofix-code/watch-dogs-legion-community-sdk) and registrator2000's editor reference (https://www.nexusmods.com/watchdogslegion/mods/18). No Cheat Engine runtime or scripts are included. The identifier catalog is provided for review; no license or ownership of Ubisoft assets is asserted here.

The source is ready to upload to a public repository. Supply its actual public URL to Nexus support. A local ZIP is not a public source link.
