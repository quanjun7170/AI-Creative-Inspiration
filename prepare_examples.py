"""Create explicitly labeled candidate examples and a final-sample-only demonstration."""
from pathlib import Path
import json
import shutil
import re
import pandas as pd
from pipeline import save, compile_plan

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
COMMON=[
 ('c_curios','Expressed desire to learn more about the content, meaning or events of the artifact.','Clear request for more information about its content.','Requests about production tools or techniques.'),
 ('p_curios','Expressed desire to understand the tools, techniques or process used to make the artifact.','Explicit and strong interest in learning how it was made.','Claims about actual expertise or mere praise.'),
 ('enjoy','Expressed pleasure or enjoyment from experiencing the artifact.','Strong, unambiguous pleasure in the experience.','Curiosity or an intention to create without expressed pleasure.'),
 ('try_des','Expressed wish to personally try making a similar type of creative artifact.','Strong, explicit wish to try creation personally.','Past creation, general praise, hypothetical ability, or advice to others.')]
FEATURES={
 'video':[
  ('v_real','Resemblance of depicted visuals to real camera footage in lighting, materials, anatomy and motion.','Strong resemblance to real camera footage.','Narrative plausibility, authenticity of authorship, or audience belief.'),
  ('v_compl','Density of concurrent visual elements, independent actions and changes to track.','Many simultaneous distinct visual elements and actions to track.','Technical production difficulty or audience cognitive load.'),
  ('v_unexp','Departure of depicted events from ordinary expectations established by the scene.','Marked departure from the scene-established expectations.','Algorithm controllability or a particular viewer\'s surprise.')],
 'music':[
  ('m_compl','Density of simultaneous distinct audible musical layers and rhythmic patterns.','Many distinguishable concurrent layers and patterns.','Difficulty of producing the music or listener mental effort.'),
  ('m_unexp','Audible departures from a rhythmic or melodic pattern established within the excerpt.','Strong changes that depart from the established pattern.','Universal novelty, artist intentions, or listener surprise.'),
  ('m_change','Extent of audible variation in dynamics, instrumentation or texture across the excerpt.','Frequent, pronounced changes in dynamics and texture.','Emotions experienced by the listener.')],
 'image':[
  ('i_compl','Density of distinct visual elements and spatial relations within the image.','Many visually distinct elements and relations.','Viewer cognitive load or production difficulty.'),
  ('i_real','Resemblance of depicted objects, materials and lighting to a photograph.','Strong photographic resemblance.','Truthfulness of the scene or identity of the creator.'),
  ('i_incong','Presence of visibly incongruous combinations of objects or settings.','Highly incongruous visible combinations.','Temporal continuity or events outside the still image.')],
 'writing':[
  ('t_compl','Structural complexity of syntax and embedding of ideas in the supplied text.','Extensive syntactic embedding and interconnected ideas.','Reader intelligence or subjective cognitive load.'),
  ('t_coher','Understandability of connections between propositions or narrated events.','Clear, consistent connections across the supplied text.','Literary merit or audience enjoyment.'),
  ('t_unexp','Departure of textual developments from expectations established by the passage.','Strong departures from text-established expectations.','Corpus-wide originality or author intentions.')]
}

def dimension(x, source):
    key,definition,high,exclude=x
    return dict(id=key,source=source,definition=definition,anchor_1='No expressed evidence of this response.' if source=='comment' else 'Minimum observable degree of this property.',
       anchor_5='Moderate, clear evidence of the defined dimension.',anchor_10=high,exclusions=exclude,
       rationale='Candidate operationalization for artifact exposure and creative motivation; requires construct review.',
       citation='',citation_status='not_provided')

def main():
    for modality, features in FEATURES.items():
        dims=[dimension(x,'artifact') for x in features]+[dimension(x,'comment') for x in COMMON]
        plan={'modality':modality,'question':'Which artifact properties accompany production curiosity and expressed desire to create?',
          'status':'assistant_authored_candidate_not_api_generated','dimensions':dims,'correspondence':[],
          'analysis':{'predictors':['c_curios','p_curios','enjoy'],'outcomes':['try_des']}}
        if modality=='video':
            for key,definition in [('realism','Expressed perception that the narrative world reflects the real world.'),
                                   ('novelty','Expressed encounter with something different from what is regularly encountered.'),
                                   ('unpred','Expressed algorithmic or artificial unpredictability and events exceeding expectations; historical definition mixes these targets.')]:
                dims.append(dimension((key,definition,'Strong, explicit expression of this perception.','Unexpressed reactions and external knowledge.'),'comment'))
            plan['correspondence']=[{'artifact':'v_real','comment':'realism','rationale':'Related but distinct visual and narrative realism targets.'},
                                   {'artifact':'v_unexp','comment':'unpred','rationale':'Partial content overlap; historical unpredictability also includes generation-related meanings.'}]
        save(ROOT/'examples'/f'{modality}_candidate.json',plan)
        save(ROOT/'examples'/f'{modality}_brief.json',{'modality':modality,'research_question':plan['question'],'literature_excerpts':[],
             'scope':'Artifact properties and comment-expressed curiosity, enjoyment and creative trial desire.'})
        compile_plan(ROOT/'examples'/f'{modality}_candidate.json',ROOT/'compiled'/modality)
    # Derive only the historical final analysis sample; no authors or unused comments released.
    folder=PROJECT/'analyses/Study 1 comment analysis'
    mapping=pd.read_csv(folder/'variable_map_v3.csv')
    names=mapping.mplus_variable.tolist()
    d=pd.read_csv(folder/'comments_video_mplus_v3.csv',header=None,names=names).replace(-999,float('nan'))
    d=d[(d.v_stat==1)&(d.v_error==0)&(d.v_play==1)]
    d=d.dropna(subset=['c_score','realism','novelty','unpred','p_ncomm','p_score','v_real','v_unexp','v_compl'])
    d=d.dropna(subset=['c_curios','p_curios','enjoy','try_des'],how='all')
    assert len(d)==13598 and d.post_uid.nunique()==1191
    dest=ROOT/'examples/study1_final_sample';dest.mkdir(parents=True,exist_ok=True)
    c=d[['com_uid','post_uid','c_curios','p_curios','enjoy','try_des','realism','novelty','unpred']].rename(columns={'com_uid':'comment_id','post_uid':'artifact_id'})
    a=d[['post_uid','v_real','v_compl','v_unexp']].drop_duplicates().rename(columns={'post_uid':'artifact_id'})
    assert a.artifact_id.is_unique
    c['status']='ok';a['status']='ok'
    c.to_csv(dest/'comments.csv',index=False);a.to_csv(dest/'artifacts.csv',index=False)
    rich=PROJECT/'data/reddit/analysis_dataset_final_v3/comments_video_merged_v3.csv'
    text=pd.read_csv(rich,usecols=['comment_uid','post_uid','body'])
    text=text[text.comment_uid.isin(d.com_uid)].rename(columns={'comment_uid':'comment_id','post_uid':'artifact_id','body':'text'})
    assert len(text)==len(d) and text.comment_id.is_unique
    text.to_csv(dest/'comment_texts.csv',index=False)
    # Preserve exact historical model and full output; dataset contains final rows only.
    model=ROOT/'study1_reference';model.mkdir(exist_ok=True)
    keep=['com_uid','post_uid','c_score','realism','novelty','unpred','c_curios','p_curios','enjoy','try_des','p_ncomm','p_score','v_real','v_unexp','v_compl']
    d[keep].fillna(-999).to_csv(model/'comments_video_mplus_v3.csv',header=False,index=False)
    for name in ['iv med dv level2.out']:
        shutil.copy2(folder/name,model/name)
    selected=mapping.set_index('mplus_variable').loc[keep].reset_index()
    selected['position']=range(1,len(selected)+1)
    selected.to_csv(model/'variable_map_v3.csv',index=False)
    s=(folder/'IV Med DV level2.inp').read_text()
    s=re.sub(r'NAMES ARE.*?;', 'NAMES ARE\n '+' '.join(keep)+';',s,flags=re.S)
    s=re.sub(r'USEOBSERVATION ARE.*?;', '! Input contains final analysis rows only.',s,flags=re.S)
    (model/'IV Med DV level2.inp').write_text(s)
    save(dest/'provenance.json',{'source':'Historical existing ratings, not newly generated by prototype','comments':len(d),
         'posts':int(d.post_uid.nunique()),'new_api_calls':0,'candidate_prompts_are_historical_prompts':False})

if __name__=='__main__':main()
