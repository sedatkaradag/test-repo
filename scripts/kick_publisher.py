"""Start the publisher now, after a hand-made post was queued from the panel.

The publisher's open run may be sleeping in "Chain the next run" until the next regular
post (up to 15 minutes, or hours). If so, cancel it and start a new run: the new run
publishes the queued post at its time. If the run is doing anything else (publishing,
or waiting for a post due within 15 minutes), leave it alone: when it finishes, its chain
step sees the past-due post (next_due.py) and starts the next run within 5 minutes.

The new run is started FIRST (it waits as "pending"), and the sleeping run is cancelled only
after that succeeded, so a failed start never leaves the publisher without a run.

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
    """Start a publish run; GitHub sometimes answers with a transient 500, so retry."""
    err = None
    for d in (0, 20, 40, 80, 160):
        time.sleep(d)
        try:
            gh("workflow", "run", WF, "--ref", "main")
            return
        except subprocess.CalledProcessError as e:
            err = e
    raise err


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
    try:
        dispatch()  # first: the new run waits as pending behind the sleeping one
    except subprocess.CalledProcessError as e:
        return {"action": "none", "why": "could not start a new run, the sleeping run was left alone: "
                + (e.stderr or str(e)).strip()[:200], "run": rid}
    # The chain step runs with `if: always()`, which a normal cancel does not stop: force-cancel it.
    # Safe here because the run is only sleeping (nothing is being published).
    gh("api", "-X", "POST", f"repos/{{owner}}/{{repo}}/actions/runs/{rid}/force-cancel")
    for _ in range(60):  # check that the new run really starts
        time.sleep(3)
        if runs("in_progress") and runs("in_progress")[0]["databaseId"] != rid:
            return {"action": "restarted", "cancelled": rid}
    return {"action": "error", "why": f"run {rid} was cancelled but no new run started in 3 min: "
            "WARNING, check the publisher", "cancelled": rid}


if __name__ == "__main__":
    try:
        print(json.dumps(main()))
    except subprocess.CalledProcessError as e:
        print(json.dumps({"action": "error", "why": (e.stderr or str(e)).strip()[:300]}))
        sys.exit(1)
