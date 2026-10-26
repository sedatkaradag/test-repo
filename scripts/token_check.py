"""Nightly: refresh the Instagram token and record the result. Runs in GitHub Actions.

Writes history/token_status.json (never the token itself): when it was checked, whether the
refresh worked, when the token expires, and whether Instagram returned the same token or a new
one. A new token can only be saved back to the repository secret when a GH_PAT secret exists;
otherwise, and on any failure, an open issue is recorded (scripts/issues.py) so the owner sees it
in the panel.

Environment: IG_ACCESS_TOKEN, optional GH_TOKEN (= secrets.GH_PAT), GITHUB_REPOSITORY.
"""
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "history" / "token_status.json"


def issue(title, detail):
    subprocess.run([sys.executable, str(ROOT / "scripts" / "issues.py"), "add", "--kind", "publish",
                    "--source", "Gece token kontrolü", "--ref", "IG_ACCESS_TOKEN",
                    "--title", title, "--detail", detail], check=False)


def main():
    old = os.environ["IG_ACCESS_TOKEN"]
    pat = os.environ.get("GH_TOKEN", "")
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    status = {"checked_at": now.isoformat().replace("+00:00", "Z"), "ok": False}
    try:
        r = requests.get("https://graph.instagram.com/refresh_access_token",
                         params={"grant_type": "ig_refresh_token", "access_token": old}, timeout=60)
        data = r.json() if r.content else {}
    except Exception as e:  # noqa: BLE001
        data = {"error": {"message": str(e)[:200]}}
    new = data.get("access_token", "")
    if new:
        print(f"::add-mask::{new}")
    if not new:
        status["error"] = (data.get("error") or {}).get("message", f"HTTP {getattr(r, 'status_code', '?')}")[:300]
        issue("Instagram token yenilenemedi",
              "Gece yenilemesi başarısız oldu: " + status["error"] + ". Token düşerse paylaşım durur; "
              "Meta panelinden yeni token alıp GitHub'da IG_ACCESS_TOKEN'a girmek gerekebilir.")
    else:
        expires_in = int(data.get("expires_in", 0))
        status.update(ok=True, same_token=(new == old), expires_in_days=round(expires_in / 86400, 1),
                      expires_at=(now + dt.timedelta(seconds=expires_in)).isoformat().replace("+00:00", "Z"))
        if new == old:
            status["stored"] = True          # same token, now valid longer; nothing to save
        elif pat:
            res = subprocess.run(["gh", "secret", "set", "IG_ACCESS_TOKEN", "--body", new,
                                  "--repo", os.environ["GITHUB_REPOSITORY"]], capture_output=True, text=True)
            status["stored"] = res.returncode == 0
            if not status["stored"]:
                status["error"] = "could not save the new token: " + res.stderr[:200]
        else:
            status["stored"] = False
            status["note"] = ("Instagram returned a new token, but without a GH_PAT secret it cannot be "
                              "saved; the stored token keeps its own expiry date.")
        if status.get("stored") is False:
            issue("Yenilenen Instagram token'ı kaydedilemiyor",
                  "Instagram yenilemede yeni bir token döndü, ama GitHub'a kaydedecek GH_PAT anahtarı yok "
                  "(ya da kayıt başarısız oldu). Kayıtlı token kendi süresi dolunca düşer. Çözüm: bu repo için "
                  "'Secrets: Read and write' yetkili bir fine-grained GitHub token oluşturup GH_PAT adıyla eklemek.")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print({k: v for k, v in status.items()})


if __name__ == "__main__":
    main()
