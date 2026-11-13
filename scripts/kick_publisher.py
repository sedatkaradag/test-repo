"""Start the publisher now, after a hand-made post was queued from the panel.

The publisher's open run may be sleeping in "Chain the next run" until the next regular
post (up to 15 minutes, or hours). If so, cancel it and start a new run: the new run
publishes the queued post at its time. If the run is doing anything else (publishing,
or waiting for a post due within 15 minutes), leave it alone: when it finishes, its chain
step sees the past-due post (next_due.py) and starts the next run within 5 minutes.

    python3 scripts/kick_publisher.py      -> prints one JSON line: {"action": ...}
"""
import json
import subprocess
import sys
import time

WF = "publish.yml"
SLEEP_STEP = "Chain the next run"


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def runs(status):
    return json.loads(gh("run", "list", "--workflow", WF, "--status", status, "--json", "databaseId", "--limit", "5"))


def current_step(run_id):
    jobs = json.loads(gh("api", f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}/jobs"))["jobs"]
    for job in jobs:
        for st in job.get("steps", []):
            if st["status"] == "in_progress":
                return st["name"]
    return None


def dispatch():
    gh("workflow", "run", WF, "--ref", "main")


def main():
    active = runs("in_progress")
    if not active:
        if runs("queued") or runs("pending"):
            return {"action": "none", "why": "a publish run is already waiting to start"}
        dispatch()
        return {"action": "dispatched", "why": "no publish run was open"}
    rid = active[0]["databaseId"]
    step = current_step(rid)
    if step != SLEEP_STEP:
        return {"action": "none", "why": f"run {rid} is busy: {step}", "run": rid}
    # The chain step runs with `if: always()`, which a normal cancel does not stop: force-cancel it.
    # Safe here because the run is only sleeping (nothing is being published).
    gh("api", "-X", "POST", f"repos/{{owner}}/{{repo}}/actions/runs/{rid}/force-cancel")
    for _ in range(45):  # let the cancel land (force-cancel took ~35 s) so the new run is not queued behind it
        time.sleep(2)
        if json.loads(gh("run", "view", str(rid), "--json", "status"))["status"] == "completed":
            break
    dispatch()
    return {"action": "restarted", "cancelled": rid}


if __name__ == "__main__":
    try:
        print(json.dumps(main()))
    except subprocess.CalledProcessError as e:
        print(json.dumps({"action": "error", "why": (e.stderr or str(e)).strip()[:300]}))
        sys.exit(1)
