"""
v2_01_ingest_lux_hscrp.py
Stage 1: Programmatic Ingestion of Liver Ultrasound (VCTE FibroScan) & hs-CRP.
Downloads:
- 2017-March 2020: P_LUX.xpt, P_HSCRP.xpt (and documentation .htm)
- 2021-2023: LUX_L.xpt, HSCRP_L.xpt (and documentation .htm)
Verifies SAS transport HEADER RECORD, SEQN uniqueness, and logs SHA-256 manifest.
"""

from pathlib import Path
import hashlib, json, time, requests
import pandas as pd

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
DATA_DIR = ROOT / "data"
SOURCES_DIR = ROOT / "sources"
RESULTS_DIR = BASE / "results"

DATA_DIR.mkdir(parents=True, exist_ok=True)
SOURCES_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

DOWNLOADS = {
    "P_LUX.xpt": ("https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_LUX.xpt", DATA_DIR),
    "LUX_L.xpt": ("https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/LUX_L.xpt", DATA_DIR),
    "P_HSCRP.xpt": ("https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2017/DataFiles/P_HSCRP.xpt", DATA_DIR),
    "HSCRP_L.xpt": ("https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2021/DataFiles/HSCRP_L.xpt", DATA_DIR),
    "P_LUX.htm": ("https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/P_LUX.htm", SOURCES_DIR),
    "LUX_L.htm": ("https://wwwn.cdc.gov/Nchs/Nhanes/2021-2022/LUX_L.htm", SOURCES_DIR),
    "P_HSCRP.htm": ("https://wwwn.cdc.gov/Nchs/Nhanes/2017-2018/P_HSCRP.htm", SOURCES_DIR),
    "HSCRP_L.htm": ("https://wwwn.cdc.gov/Nchs/Nhanes/2021-2022/HSCRP_L.htm", SOURCES_DIR),
}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def download(url: str, dest: Path) -> dict:
    if dest.exists() and dest.stat().st_size > 1000:
        print(f"[EXISTS] {dest.name} ({dest.stat().st_size:,} bytes)")
    else:
        print(f"[DOWNLOAD] Fetching {dest.name} from {url}...")
        for attempt in range(1, 4):
            try:
                r = requests.get(url, timeout=30, stream=True)
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                break
            except Exception as e:
                print(f"  Attempt {attempt} failed: {e}")
                time.sleep(2)
                if attempt == 3:
                    raise RuntimeError(f"Failed to download {dest.name}")

    # Verify header if .xpt
    if dest.suffix.lower() == ".xpt":
        with open(dest, "rb") as f:
            header = f.read(80)
        assert b"HEADER RECORD" in header, f"Invalid SAS transport file: {dest.name}"

    digest = sha256_file(dest)
    info = {
        "filename": dest.name,
        "path": str(dest.relative_to(ROOT)),
        "size_bytes": dest.stat().st_size,
        "sha256": digest,
        "url": url,
        "verified": True
    }
    return info

def main():
    print("=" * 65)
    print("STAGE 1 (V2.0): CDC NHANES VCTE (FIBROSCAN) & hs-CRP INGESTION")
    print("=" * 65)
    manifest = {}
    for name, (url, target_dir) in DOWNLOADS.items():
        dest = target_dir / name
        info = download(url, dest)
        manifest[name] = info

    # Verify uniqueness of SEQN in xpt files
    print("\n--- Verifying Data Integrity & SEQN Uniqueness ---")
    for name in ["P_LUX.xpt", "LUX_L.xpt", "P_HSCRP.xpt", "HSCRP_L.xpt"]:
        path = DATA_DIR / name
        df = pd.read_sas(path, format="xport")
        assert "SEQN" in df.columns, f"SEQN column missing in {name}!"
        assert df["SEQN"].is_unique, f"Duplicate SEQN values detected in {name}!"
        manifest[name]["rows"] = len(df)
        manifest[name]["cols"] = len(df.columns)
        print(f"  {name:<15}: {len(df):>6} rows x {len(df.columns):>2} cols (SEQN 100% unique)")

    out_json = RESULTS_DIR / "v2_download_manifest.json"
    out_json.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest saved to {out_json}")

if __name__ == "__main__":
    main()
