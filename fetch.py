import re,json,urllib.request,datetime,html as H
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36','Accept-Language':'he'}
OFF='https://votes26.bechirot.gov.il/nationalresults?lang=he'
FB='https://thestateofisrael.com/he/election-2026/results'
def get(u):
    r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30);return r.status,r.read().decode('utf8','ignore')
KEYS=[('עמך ישראל','winter'),('המילואימניקים','hendel'),('הליכוד','likud'),('ישראל ביתנו','yb'),('ישר','yashar'),('ביחד','beyachad'),('יהדות התורה','utj'),('המשותפת','joint'),('עוצמה','otzma'),('הדמוקרטים','dem'),('ש״ס','shas'),('הציונות הדתית','rz'),('רע״ם','raam'),('המילואימניקים','hendel'),('עמך ישראל','winter'),('כחול לבן','bw')]
BLOC={'likud':'c','shas':'c','utj':'c','otzma':'c','rz':'c','yashar':'e','beyachad':'e','yb':'e','dem':'e','joint':'a','raam':'a'}
PAIRS=[('likud','rz'),('beyachad','yb'),('yashar','dem'),('shas','utj'),('joint','raam')]
def key(n):
    for k,v in KEYS:
        if k in n: return v
    return None
def parse_fb(h):
    t=re.sub(r'<script.*?</script>|<style.*?</style>','',h,flags=re.S);t=re.sub(r'<[^>]+>','|',t);t=H.unescape(re.sub(r'\|[\s|]*','|',t))
    t=t.split('תוצאות הבחירות|הספירה',1)[1].split('|המדגמים|')[0]
    d={'asof':re.search(r'נכון ל-([^.]*?)\s*GMT',t).group(1).strip(),
       'counted':int(re.search(r'קולות שנספרו\|([\d,]+)',t).group(1).replace(',','')),
       'valid':int(re.search(r'קולות כשרים\|([\d,]+)',t).group(1).replace(',',''))}
    ps=[]
    for n,v in re.findall(r'\|([^|]+)\|[\d.]+% מהקולות הכשרים \(([\d,]+)\)',t): ps.append((n,int(v.replace(',',''))))
    for n,v in re.findall(r'\|([^|]+)\|[\d.]+%\|קולות: ([\d,]+)',t):
        if 'כל שאר' not in n: ps.append((n,int(v.replace(',',''))))
    o=re.search(r'כל שאר הרשימות\|[\d.]+%\|קולות: ([\d,]+)',t)
    d['others']=int(o.group(1).replace(',','')) if o else 0
    d['parties']=[{'name':n,'id':key(n) or n,'votes':v} for n,v in ps]
    return d
def bader_ofer(parties,valid):
    th=valid*0.0325;q=[p for p in parties if p['votes']>=th]
    seats={p['id']:0 for p in q};V={p['id']:p['votes'] for p in q}
    units={};[units.setdefault(i,[i]) for i in V]
    for a,b in PAIRS:
        if a in V and b in V: units.pop(a);units.pop(b);units[a+'+'+b]=[a,b]
    U={u:sum(V[i] for i in m) for u,m in units.items()};S={u:0 for u in U}
    for _ in range(120): u=max(U,key=lambda u:U[u]/(S[u]+1));S[u]+=1
    for u,m in units.items():
        if len(m)==1: seats[m[0]]=S[u]
        else:
            s={i:0 for i in m}
            for _ in range(S[u]): i=max(m,key=lambda i:V[i]/(s[i]+1));s[i]+=1
            seats.update(s)
    return seats,th
def main():
    src=None;err=''
    try:
        st,h=get(OFF)
        if st==200 and 'awsWafCookie' not in h: err='official page loaded but no parser'  # JS challenge normally
        else: err=f'official site returned {st} (AWS WAF challenge)'
    except Exception as e: err='official: '+str(e)[:80]
    st,h=get(FB);d=parse_fb(h);d['source']=FB;d['source_label']='thestateofisrael.com (מציג את נתוני ועדת הבחירות)';d['official_error']=err
    seats,th=bader_ofer(d['parties'],d['valid'])
    for p in d['parties']:
        p['pct']=round(100*p['votes']/d['valid'],2);p['seats']=seats.get(p['id'],0);p['bloc']=BLOC.get(p['id'],'o')
    d['parties'].sort(key=lambda p:-p['votes']);d['threshold_votes']=round(th)
    d['blocs']={b:sum(p['seats'] for p in d['parties'] if p['bloc']==b) for b in 'ceao'}
    d['eligible']=7331981  # CEC official figure (verified on votes26.bechirot.gov.il)
    d['pct_counted']=round(100*d['counted']/d['eligible'],2)
    d['fetched']=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=2))).strftime('%d.%m.%Y %H:%M')
    old={}
    try: old=json.load(open('data.json'))
    except: pass
    if {k:v for k,v in old.items() if k!='fetched'}=={k:v for k,v in d.items() if k!='fetched'}: print('nochange');return
    json.dump(d,open('data.json','w'),ensure_ascii=False,indent=1);print('updated',d['counted'],d['blocs'])
main()
