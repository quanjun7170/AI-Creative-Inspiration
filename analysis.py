"""Exploratory post-level correspondence and within/between association analysis."""
from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd

def corr(x,y):
    if len(x)<4 or np.std(x)==0 or np.std(y)==0:return float('nan')
    return float(np.corrcoef(x,y)[0,1])

def interval(draws):
    x=np.asarray(draws); x=x[np.isfinite(x)]
    return list(np.quantile(x,[.025,.975])) if len(x)>=100 else [float('nan')]*2

def merge_data(comments, artifacts, plan):
    c=comments.copy(); a=artifacts.copy()
    for frame, key in [(c,'comment_id'),(a,'artifact_id')]:
        if frame[key].isna().any() or frame[key].duplicated().any() or frame[key].astype(str).str.strip().eq('').any():
            raise ValueError('Missing or duplicate '+key)
    if c.artifact_id.isna().any():raise ValueError('Missing comment parent IDs')
    c['artifact_id']=c.artifact_id.astype(str); a['artifact_id']=a.artifact_id.astype(str)
    if not set(c.artifact_id)<=set(a.artifact_id):raise ValueError('Unmatched comment parent IDs')
    counts={'input_comments':len(c),'input_artifacts':len(a)}
    for frame, source in [(a,'artifact'),(c,'comment')]:
        if 'status' not in frame:raise ValueError('Explicit status column required')
        for d in plan['dimensions']:
            if d['source']==source:
                col=d['id']; frame[col]=pd.to_numeric(frame[col],errors='raise').replace(-999,np.nan)
                v=frame[col].dropna()
                if not (v.between(1,10)&(v%1==0)).all():raise ValueError('Invalid rating '+col)
    # A failed artifact cannot be treated as an all-1 artifact; preserve its exclusion count.
    a=a[a.status.eq('ok')].drop(columns='status')
    c=c[c.status.eq('ok')].drop(columns='status')
    overlap=(set(c)&set(a))-{'artifact_id'}
    if overlap:raise ValueError('Ambiguous overlapping fields '+str(overlap))
    merged=c.merge(a,on='artifact_id',how='inner',validate='many_to_one')
    counts.update(retained_comments=len(merged),retained_artifacts=int(merged.artifact_id.nunique()))
    return merged,counts

def fit(x,y):
    if len(y)<=x.shape[1] or np.linalg.matrix_rank(x)<x.shape[1]:return None
    return np.linalg.lstsq(x,y,rcond=None)[0]

def run_analysis(plan, comments, artifacts, out, bootstrap=2000, seed=20261028):
    if bootstrap<100:raise ValueError('Use at least 100 bootstrap replicates')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    c=pd.read_csv(comments,dtype={'comment_id':str,'artifact_id':str})
    a=pd.read_csv(artifacts,dtype={'artifact_id':str})
    m, flow=merge_data(c,a,plan)
    m.to_csv(out/'analysis_sample.csv',index=False)
    ds=plan['dimensions'];ac=[d['id'] for d in ds if d['source']=='artifact'];cc=[d['id'] for d in ds if d['source']=='comment']
    posts=m.groupby('artifact_id')[ac+cc].mean()
    posts.to_csv(out/'post_aggregates.csv')
    rng=np.random.default_rng(seed)
    descriptives=[]
    for d in ds:
        series=posts[d['id']] if d['source']=='artifact' else m[d['id']]
        x=series.dropna()
        descriptives.append({'variable':d['id'],'source':d['source'],'n':len(x),'missing':int(series.isna().sum()),
          'mean':x.mean(),'sd':x.std(),'floor_percent':100*x.eq(1).mean()})
    pd.DataFrame(descriptives).to_csv(out/'descriptives.csv',index=False)
    correspondence=[]
    planned={(p['artifact'],p['comment']) for p in plan.get('correspondence',[])}
    for x in ac:
        for y in cc:
            t=posts[[x,y]].dropna();arr=t.to_numpy(); n=len(arr)
            draws=[corr(*(arr[rng.integers(0,n,n)].T)) for _ in range(bootstrap)] if n>=4 else []
            lo,hi=interval(draws)
            correspondence.append({'artifact_variable':x,'comment_variable':y,'planned_pair':(x,y) in planned,'n_posts':n,
              'r':corr(*arr.T),'ci_low':lo,'ci_high':hi})
    pd.DataFrame(correspondence).to_csv(out/'correspondence.csv',index=False)
    # Within regression: demean X and Y on each model's complete cases; resample entire artifacts.
    # Between regression: equal-weight post means on artifact properties. Not multilevel SEM.
    paths=[]
    for outcome in plan['analysis']['outcomes']:
        for level,predictors in [('within',plan['analysis']['predictors']),('between',ac)]:
            if not predictors:continue
            cols=predictors+[outcome]
            t=(m[['artifact_id']+cols].dropna() if level=='within' else posts[cols].dropna().reset_index())
            if level=='within':
                z=t[cols]-t.groupby('artifact_id')[cols].transform('mean')
                X=z[predictors].to_numpy();Y=z[outcome].to_numpy();names=predictors
            else:
                X=np.column_stack([np.ones(len(t)),t[predictors].to_numpy()]);Y=t[outcome].to_numpy();names=['intercept']+predictors
            beta=fit(X,Y)
            if beta is None:
                paths.append({'level':level,'outcome':outcome,'predictor':'not_estimable','b':np.nan,'ci_low':np.nan,'ci_high':np.nan,
                              'n':len(t),'n_posts':t.artifact_id.nunique(),'valid_bootstraps':0});continue
            groups=[np.flatnonzero(t.artifact_id.to_numpy()==k) for k in t.artifact_id.unique()]
            draws=[]
            for _ in range(bootstrap):
                ix=np.concatenate([groups[j] for j in rng.integers(0,len(groups),len(groups))])
                b=fit(X[ix],Y[ix])
                if b is not None:draws.append(b)
            for j,name in enumerate(names):
                lo,hi=interval([b[j] for b in draws])
                paths.append({'level':level,'outcome':outcome,'predictor':name,'b':beta[j],'ci_low':lo,'ci_high':hi,
                             'n':len(t),'n_posts':len(groups),'valid_bootstraps':len(draws)})
    pd.DataFrame(paths).to_csv(out/'exploratory_paths.csv',index=False)
    meta={'sample_flow':flow,'bootstrap_replicates':bootstrap,'seed':seed,'coefficient_scale':'unstandardized',
          'comments_sha256':hashlib.sha256(Path(comments).read_bytes()).hexdigest(),
          'artifacts_sha256':hashlib.sha256(Path(artifacts).read_bytes()).hexdigest(),
          'method':'Post-level Pearson; within fixed effects OLS; between equal-weight post-mean OLS; artifact bootstrap',
          'missing':'Pairwise complete correspondence; modelwise complete regressions; null retained in merged sample',
          'cautions':['Exploratory, no multiplicity adjustment','No causal mediation or coding accuracy claim',
                      'Post means are observed aggregates, not latent between components',
                      'Repeated authors across posts are not modeled','No controls unless explicitly added in a separate model',
                      'This analysis does not reproduce the historical Mplus SEM']}
    (out/'analysis_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    (out/'REPORT.md').write_text('# Exploratory analysis\n\n'+json.dumps(meta,indent=2)+'\n\nSee correspondence.csv and exploratory_paths.csv. Confidence intervals resample artifacts, not independent comments.\n',encoding='utf-8')
    print(json.dumps(flow))
