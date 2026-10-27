"""Rebuild v1.0.7.7 using unchanged v1.0.7.6 resources, except tNVSE."""
import argparse, copy, hashlib, json, shutil, subprocess, sys, zipfile
from pathlib import Path
from tools.prepare_key_prompt_release import resources

VERSION = "1.0.7.7"
SOURCE_ZIP = "tNVSE-71-KR-UI-source.zip"
def sha(b): return hashlib.sha256(b).hexdigest()

def build(a):
    from vnvkr import VERSION as code_version
    if code_version != VERSION: raise ValueError("Code/release version mismatch")
    old_exe = a.base.read_bytes()
    expected = [s.split()[0].lower() for s in a.checksums.read_text(encoding="utf-8-sig").splitlines()
                if s.split()[-1].lstrip("*") == a.base.name]
    if expected != [sha(old_exe)]: raise ValueError("Base release SHA256 mismatch")
    if a.work.exists() or a.out.exists(): raise FileExistsError("Use fresh build directories")
    old = resources(a.base)
    if not old or "TranslationData/catalog.json" not in old: raise ValueError("Base payloads missing")
    stage = a.work / "resources"
    stage.mkdir(parents=True)
    for name, data in old.items():
        dst = (stage / name).resolve()
        if not dst.is_relative_to(stage.resolve()): raise ValueError("Unsafe resource path")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
    catalog_path = "TranslationData/catalog.json"
    before = json.loads(old[catalog_path].decode("utf-8-sig"))
    after = copy.deepcopy(before)
    runtime = after["font_bundle"]["runtime_patch"]
    dll_path = "TranslationData/" + runtime["payload"]
    original = old[dll_path]
    if sha(original) != runtime["payload_sha256"]: raise ValueError("Base DLL hash mismatch")
    new_dll = a.dll.read_bytes()
    if not new_dll.startswith(b"MZ") or len(new_dll) < 100000 or new_dll == original:
        raise ValueError("New Win32 DLL missing, invalid, or unchanged")
    (stage / dll_path).write_bytes(new_dll)
    runtime["payload_sha256"] = sha(new_dll)
    notices = runtime["notices"]
    source_match = [n for n in notices if n["path"].endswith(SOURCE_ZIP)]
    notice_match = [n for n in notices if n["path"].endswith("tNVSE-KR-UI-fix.txt")]
    if len(source_match) != 1 or len(notice_match) != 1:
        raise ValueError("Unexpected source archive or notice declaration")
    source = source_match[0]
    source_path = "TranslationData/" + source["payload"]
    if sha(old[source_path]) != source["payload_sha256"]: raise ValueError("Old source checksum mismatch")
    with zipfile.ZipFile(stage / source_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        excluded = {".git", ".vs", "out", "packages", "__pycache__"}
        for p in sorted(a.tnvse.rglob("*")):
            rel = p.relative_to(a.tnvse)
            if p.is_file() and not excluded.intersection(rel.parts) and p.suffix.lower() not in {".ttf",".otf",".woff",".woff2"}:
                z.write(p, "tNVSE/" + rel.as_posix())
        for name in ("tools/build_tnvse_patch.ps1","tools/tnvse/ui-replacement-encoding.patch",
                     "tools/tnvse/strict-lossless-encoding.patch"):
            z.write(a.repo / name, "build/" + name)
    with zipfile.ZipFile(stage / source_path) as z:
        if z.testzip() or not any(n.endswith("strict-lossless-encoding.patch") for n in z.namelist()):
            raise ValueError("Source ZIP validation failed")
    source["payload_sha256"] = sha((stage / source_path).read_bytes())
    notice = notice_match[0]
    notice_path = "TranslationData/" + notice["payload"]
    if sha(old[notice_path]) != notice["payload_sha256"]: raise ValueError("Old notice mismatch")
    notice_text = old[notice_path] + (
        "\nVNV v1.0.7.7: strict UTF-8 and lossless CP949 conversion; new Win32 DLL.\n"
        "Corresponding updated source and patches are supplied in source ZIP.\n").encode("utf-8")
    (stage / notice_path).write_bytes(notice_text)
    notice["payload_sha256"] = sha(notice_text)
    (stage / catalog_path).write_text(json.dumps(after,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    new = {k:(stage/k).read_bytes() for k in old}
    changed = {k for k in old if old[k] != new[k]}
    allowed = {catalog_path,dll_path,source_path,notice_path}
    if changed != allowed: raise ValueError(f"Unapproved changes: {changed ^ allowed}")
    print("PASS: all other translation, font, UI and worker bytes preserved")
    a.out.mkdir(parents=True)
    opts=[sys.executable,"-m","PyInstaller","--noconfirm","--onefile","--windowed",
        "--name","VNVKoreanPatcher","--distpath",str((a.work/"dist").resolve()),
        "--workpath",str((a.work/"temp").resolve()),"--specpath",str((a.work/"spec").resolve()),
        "--add-data",str((stage/"TranslationData").resolve())+";TranslationData",
        "--add-binary",str((stage/"VNVKRXEditWorker.exe").resolve())+";.",
        "--add-binary",str((stage/"Backend/XEditLib.dll").resolve())+";Backend"]
    for name in ("FalloutNV.Hardcoded.dat","icudtl.dat","LICENSE"):
        opts += ["--add-data",str((stage/"Backend"/name).resolve())+";Backend"]
    subprocess.run(opts+["vnvkr_gui.py"],check=True)
    built = a.work/"dist/VNVKoreanPatcher.exe"
    actual=resources(built)
    if actual.keys()!=new.keys() or any(actual[k]!=v for k,v in new.items()):
        raise ValueError("Repack changed verified resources")
    subprocess.run([str(built.resolve()),"--package-check"],check=True,timeout=120,
                   creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    exe=a.out/f"VNVKoreanPatcher-v{VERSION}.exe"
    shutil.copyfile(built,exe)
    zipout=a.out/SOURCE_ZIP
    shutil.copyfile(stage/source_path,zipout)
    (a.out/"SHA256SUMS.txt").write_text(
        "".join(f"{sha(p.read_bytes())}  {p.name}\n" for p in (exe,zipout)),encoding="ascii")
    print("PASS: release verified",VERSION)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    for name in ("base","checksums","dll","tnvse","repo","work","out"):
        parser.add_argument("--"+name,required=True,type=Path)
    build(parser.parse_args())
