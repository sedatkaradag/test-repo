"""Write one JSON file per queue item (and the config state) for the control
panel, so the agent can push them with ArtifactData using `file_path`.

    python scripts/panel_rows.py <out_dir>

Output: <out_dir>/queue/<slot>.json and <out_dir>/meta/state.json.
image_url is not included: the agent uploads the JPEG as a panel asset and
adds the returned url.
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["slot", "entry_id", "type", "reference", "publish_at", "local_slot", "status",
          "theme", "caption", "review", "error", "media_id", "posted_at"]


def main(out):
    out = Path(out)
    (out / "queue").mkdir(parents=True, exist_ok=True)
    (out / "meta").mkdir(parents=True, exist_ok=True)
    for p in sorted((ROOT / "queue").glob("*.json")):
        item = json.loads(p.read_text(encoding="utf-8"))
        row = {k: item[k] for k in FIELDS if k in item}
        (out / "queue" / f"{p.stem}.json").write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    state = {k: cfg.get(k) for k in ("dry_run", "paused", "slots", "jitter_minutes")}
    (out / "meta" / "state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    print(f"rows written to {out}")


if __name__ == "__main__":
    main(sys.argv[1])
