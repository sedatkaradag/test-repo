import json,datetime as dt,re,statistics as st,collections,sys
W=sys.argv[1]
rows=json.load(open(W+"/rows.json"))
P=lambda s: dt.datetime.fromisoformat(s.replace("Z","+00:00"))
CAT={
 "Prophets' duas & stories":["20:25","21:87","7:23","21:83","12:86","19:2","28:7","12:92","28:24","18:10","15:55","31:17","9:128"],
 "Short, well-known surahs":["112:1","113:1","114:1","108:1","103:1","93:1","67:1"],
 "Comfort, hope & anxiety":["4:28","35:2","64:11","50:16","42:19","33:3","47:7","28:73","39:53"],
 "Practical ethics (people)":["49:6","17:23","49:13","49:12","41:34"],
 "Dua, dhikr & worship":["2:186","2:201","7:55","2:152","33:56","18:46","6:162","59:18"],
 "Allah's names & knowledge":["59:24","6:59","16:18"],
 "Death & the hereafter":["29:57"],
}
def cat(r):
    if r["content"]=="hadith": return "Hadith (silent)"
    if r["source"]=="manual": return "Hand-made formats"
    e=r["entry"].replace("quran:","")
    for c,L in CAT.items():
        if any(e.startswith(x) for x in L): return c
    return "Other"
def hook(h):
    h=h or ""
    if "?" in h: return "Question"
    if re.match(r"^(For the|For anyone|If you)",h): return "Names a feeling / addresses someone"
    if re.match(r"^(Before|Read|Try|Say|Make|Answer|Start)",h): return "Instruction / moment of the day"
    if re.search(r"(Surah|dua|Dua|du'a)",h): return "Names the surah / dua"
    return "Statement / curiosity"
for r in rows: r["cat"]=cat(r); r["hooktype"]=hook(r["hook"])
reels=[r for r in rows if r["kind"]=="reel" and r["source"]=="system"]
def M(L,key,A):
    v=[r[f"s{A}"].get(key) for r in L if r[f"s{A}"] and r[f"s{A}"].get(key) is not None]
    return v
def summ(L,A=24):
    L=[r for r in L if r[f"s{A}"] and r[f"s{A}"].get("reach")]
    if not L: return None
    reach=[r[f"s{A}"]["reach"] for r in L]
    sv=sum(r[f"s{A}"].get("saved",0) for r in L); sh=sum(r[f"s{A}"].get("shares",0) for r in L); rc=sum(reach)
    w=M(L,"ig_reels_avg_watch_time",A); sk=M(L,"reels_skip_rate",A); cm=M(L,"comments",A)
    return dict(n=len(L), reach_med=round(st.median(reach)), reach_mean=round(st.mean(reach)),
                save_pct=round(100*sv/rc,2), share_pct=round(100*sh/rc,2),
                watch=round(st.mean(w)/1000,1) if w else None, skip=round(st.mean(sk),1) if sk else None,
                comments=round(st.mean(cm),1) if cm else None)
def table(title, groups, A=24):
    print(f"\n== {title} (at {A}h) ==")
    out={}
    for g,L in sorted(groups.items(), key=lambda kv:-(summ(kv[1],A) or {"reach_med":0})["reach_med"]):
        s=summ(L,A)
        if s: print(f"{g[:42]:42} {s}"); out[g]=s
    return out
res={}
after=[r for r in reels if P(r["posted_at"])>=P("2026-10-27T00:00:00+00:00")]
# 1 slot x content
g=collections.defaultdict(list)
for r in after: g[f"{r['slot_name']} / {r['content']}"].append(r)
res["slot"]=table("Slot (Oct 27+)", g); res["slot48"]=table("Slot (Oct 27+)", g, 48)
# 2 category (quran reels all dates)
g=collections.defaultdict(list)
for r in reels: g[r["cat"]].append(r)
res["cat"]=table("Category", g); res["cat48"]=table("Category", g, 48)
# 3 hook type (quran reels)
g=collections.defaultdict(list)
for r in reels:
    if r["content"]=="quran": g[r["hooktype"]].append(r)
res["hook"]=table("Hook type (verse Reels)", g)
# 4 duration
g=collections.defaultdict(list)
for r in reels:
    if r["content"]=="quran" and r["secs"]:
        b="<18s" if r["secs"]<18 else "18-25s" if r["secs"]<25 else "25-32s" if r["secs"]<32 else "32s+"
        g[b].append(r)
res["dur"]=table("Duration (verse Reels)", g)
# 5 reciter
g=collections.defaultdict(list)
for r in reels:
    if r["content"]=="quran" and r["reciter"]: g[r["reciter"]].append(r)
res["rec"]=table("Reciter (verse Reels)", g)
# 6 weekday
g=collections.defaultdict(list)
for r in after:
    if r["content"]=="quran": g[P(r["posted_at"]).strftime("%a")].append(r)
res["dow"]=table("Weekday (verse Reels, Oct 27+)", g)
# top / bottom list
L=[r for r in reels if r["s24"] and r["s24"].get("reach")]
L.sort(key=lambda r:-r["s24"]["reach"])
res["top"]=[(r["entry"],r["slot_name"],r["hook"],round(r["s24"]["reach"]),r["s24"].get("saved"),r["s24"].get("shares"),r["cat"]) for r in L[:10]]
res["bottom"]=[(r["entry"],r["slot_name"],r["hook"],round(r["s24"]["reach"]),r["s24"].get("saved"),r["s24"].get("shares"),r["cat"]) for r in L[-8:]]
# share leaders
L2=sorted(L,key=lambda r:-(r["s24"].get("shares",0)/r["s24"]["reach"]))
res["sharelead"]=[(r["entry"],r["hook"],round(100*r["s24"].get("shares",0)/r["s24"]["reach"],2),round(r["s24"]["reach"])) for r in L2[:8]]
L3=sorted(L,key=lambda r:-(r["s24"].get("saved",0)/r["s24"]["reach"]))
res["savelead"]=[(r["entry"],r["hook"],round(100*r["s24"].get("saved",0)/r["s24"]["reach"],2),round(r["s24"]["reach"])) for r in L3[:8]]
print("\nTOP",*res["top"],sep="\n"); print("\nBOTTOM",*res["bottom"],sep="\n"); print("\nSHARE",*res["sharelead"],sep="\n"); print("\nSAVE",*res["savelead"],sep="\n")
json.dump(res,open(W+"/res.json","w"),ensure_ascii=False,indent=1)
