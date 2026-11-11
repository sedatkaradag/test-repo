import json,datetime as dt,os,re,sys
W=sys.argv[1]; R=sys.argv[2]
S=json.load(open(W+"/series.json")); ser,meta=S["ser"],S["meta"]
P=lambda s: dt.datetime.fromisoformat(s.replace("Z","+00:00"))
posted=[json.loads(l) for l in open(R+"/history/posted.jsonl")]
qmeta={}
for r in posted:
    f=f"{R}/queue/{r['slot']}.json"
    if os.path.exists(f):
        q=json.load(open(f)); qmeta[r["media_id"]]=q
cur=json.load(open(R+"/history/insights.json"))
manual={m["media_id"]:m for m in cur.get("manual_posts",[])}
KEYS=["reach","views","likes","comments","saved","shares","total_interactions","ig_reels_avg_watch_time","reels_skip_rate"]
def at_age(mid, age):
    pts=[]
    for fa,pa,st in ser.get(mid,[]):
        a=(P(fa)-P(pa)).total_seconds()/3600; pts.append((a,st))
    pts.sort(key=lambda x:x[0])
    if not pts: return None,None
    lo=[p for p in pts if p[0]<=age]; hi=[p for p in pts if p[0]>=age]
    if lo and hi:
        (a0,s0),(a1,s1)=lo[-1],hi[0]
        if a1-a0>30: return None,None
        out={}
        for k in KEYS:
            if k in s0 and k in s1:
                w=0 if a1==a0 else (age-a0)/(a1-a0)
                out[k]=s0[k]+(s1[k]-s0[k])*w if k not in ("reels_skip_rate","ig_reels_avg_watch_time") else (s0[k]+(s1[k]-s0[k])*w)
        return out, (a0,a1)
    return None,None
rows=[]
for r in posted:
    mid=r["media_id"]; q=qmeta.get(mid,{})
    if r.get("type") not in ("reel",) and not r["slot"].endswith("carousel"):
        kind="photo"
    else:
        kind="reel" if r.get("type")=="reel" else "carousel"
    if r["slot"].endswith("carousel"): kind="carousel"
    content=(q.get("content_type") or r["entry_id"].split(":")[0]) if kind=="reel" else r.get("type")
    cap=q.get("caption","")
    row=dict(media_id=mid, posted_at=r["posted_at"], slot=r["slot"], slot_name=re.sub(r"^\d{4}-\d\d-\d\d_","",r["slot"]),
             kind=kind, content=content, entry=r["entry_id"], theme=r.get("theme",""), hook=cap.split("\n")[0] if cap else "",
             reciter=(r.get("recitation") or {}).get("reciter_name") or (q.get("audio") or {}).get("reciter_name"),
             secs=(q.get("audio") or {}).get("video_seconds"), template=q.get("template"), source="system")
    for A in (24,48):
        st,_=at_age(mid,A); row[f"s{A}"]=st
    rows.append(row)
for mid,m in manual.items():
    row=dict(media_id=mid, posted_at=m["posted_at"], slot="manual", slot_name="manual", kind="reel", content="manual",
             entry="", theme="", hook=m["caption_first_line"], reciter=None, secs=None, template=None, source="manual")
    for A in (24,48):
        st,_=at_age(mid,A); row[f"s{A}"]=st
    row["now"]=m["stats"]; row["now_age"]=(P(cur["fetched_at"])-P(m["posted_at"])).total_seconds()/3600
    rows.append(row)
json.dump(rows,open(W+"/rows.json","w"),ensure_ascii=False,indent=0)
import collections
c=collections.Counter((r["kind"],r["content"],r["s48"] is not None) for r in rows); print(c)
