import unittest
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from pipeline import validate_scores, compile_plan, load_compiled, read
from analysis import merge_data, corr, fit

class Tests(unittest.TestCase):
    def setUp(self):
        self.p=read(Path(__file__).parent/'examples/video_candidate.json')
    def test_score_validation(self):
        for bad in [True,0,11,1.2,'NA']:
            with self.assertRaises(ValueError):validate_scores({'x':bad,'description':''},['x'])
        validate_scores({'x':None,'description':''},['x'])
    def test_lock_detects_edit(self):
        # tempfile cleanup is confined to this explicitly verified workspace directory.
        workspace=Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(dir=workspace) as t:
            assert Path(t).resolve().parent==workspace
            out=Path(t)/'compiled';compile_plan(Path(__file__).parent/'examples/video_candidate.json',out)
            p=out/'plan.json';p.write_text(p.read_text().replace('Which artifact','What artifact'),encoding='utf-8')
            with self.assertRaises(ValueError):load_compiled(out)
    def frames(self):
        c=pd.DataFrame({'comment_id':['1','2'],'artifact_id':['a','a'],'status':['ok','ok']})
        a=pd.DataFrame({'artifact_id':['a'],'status':['ok']})
        for d in self.p['dimensions']:
            (a if d['source']=='artifact' else c)[d['id']]=1
        return c,a
    def test_duplicate_parent_rejected(self):
        c,a=self.frames()
        with self.assertRaises(ValueError):merge_data(c,pd.concat([a,a]),self.p)
    def test_unmatched_rejected(self):
        c,a=self.frames();c.loc[0,'artifact_id']='missing'
        with self.assertRaises(ValueError):merge_data(c,a,self.p)
    def test_missing_and_failed_are_not_zero(self):
        c,a=self.frames();c.loc[0,'try_des']=-999
        m,_=merge_data(c,a,self.p);self.assertTrue(pd.isna(m.loc[0,'try_des']))
        a['status']='error';m,_=merge_data(c,a,self.p);self.assertEqual(len(m),0)
    def test_known_slope(self):
        x=np.arange(10.);self.assertAlmostEqual(fit(x[:,None],3*x)[0],3)
        self.assertTrue(np.isnan(corr(x,np.ones(10))))

if __name__=='__main__':unittest.main()
