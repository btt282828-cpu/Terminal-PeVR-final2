import pandas as pd,numpy as np,sys
H='../historico_seguimiento_NO_BORRAR/historiales/'
c=pd.read_csv(H+'universo_close.csv.gz',index_col=0,parse_dates=True)
v=pd.read_csv(H+'cboe_vix.csv');v.index=pd.to_datetime(v.DATE);v=v.CLOSE
thr={'SPY':-5,'RSP':-5,'DIA':-5,'QQQ':-10,'IWM':-10}
rows=[]
for t,th in thr.items():
    p=c[t].dropna();dd=(p/p.rolling(252,min_periods=200).max()-1)*100
    ma=p.rolling(200).mean();last=-999
    for i in range(1,len(p)-121):
        if dd.iloc[i]<=th and dd.iloc[i-1]>th and i-last>=60:
            last=i;d=p.index[i];vx=v.get(d,np.nan)
            e=p.iloc[i+1]
            rows.append(dict(t=t,d=d,vix=vx,ma=p.iloc[i]<ma.iloc[i],r60=p.iloc[i+61]/e-1,r120=p.iloc[i+121]/e-1))
df=pd.DataFrame(rows).dropna(subset=['vix'])
def tr(d):return 'aprender' if d.year<=2018 else 'comprobar' if d.year<=2022 else 'caja'
df['tr']=df.d.map(tr)
for k in (20,25,30):
    df['A']=(df.vix>=k)&df.ma
    print('VIX>=',k)
    for s in ('aprender','comprobar'):
        x=df[df.tr==s]
        for r in ('r60','r120'):
            a,b=x[x.A][r],x[~x.A][r]
            dif=a.mean()-b.mean()
            t=dif/np.sqrt(a.var()/len(a)+b.var()/len(b)) if len(a)>1 and len(b)>1 else np.nan
            print(s,r,'nA',len(a),'nB',len(b),'A %.1f%% B %.1f%% dif %.1f t %.2f peorA %.1f'%(a.mean()*100,b.mean()*100,dif*100,t,a.min()*100 if len(a) else np.nan))
