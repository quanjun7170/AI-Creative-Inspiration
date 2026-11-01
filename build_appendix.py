"""Build the technical appendix and figures from the saved Mplus output."""
from pathlib import Path
import csv
import json
import re
import math
from xml.sax.saxutils import escape
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'OS_technical_appendix';OUT.mkdir(exist_ok=True)
text=(ROOT/'study1_reference/iv med dv level2.out').read_text(encoding='utf-8')
block=text.split('\nMODEL RESULTS\n')[1].split('\nQUALITY OF NUMERICAL RESULTS')[0]
names={'MED1':'Content curiosity','MED2':'Production curiosity','MED3':'Enjoyment','DV1':'Creative trial desire',
       'L1IV1':'Perceived realism','L1IV2':'Perceived novelty','L1IV3':'Perceived unpredictability',
       'L2IV1':'Video visual realism','L2IV2':'Video event unexpectedness','L2IV3':'Video visual complexity',
       'CTRL1':'Comment score','CTRL2':'Post comment count','CTRL3':'Post score / 100'}
rows=[];extra=[];level=None;target=None;op=None
for line in block.splitlines():
    if line.strip()=='Within Level':level='Within'
    elif line.strip()=='Between Level':level='Between'
    elif line.strip()=='New/Additional Parameters':level='Additional';target=None
    m=re.match(r'\s*(\w+)\s+(ON|WITH)\s*$',line)
    if m:target,op=m.groups();continue
    m=re.match(r'\s*(\w+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(\d+\.\d+)\s*$',line)
    if m:
        var,b,se,z,p=m.groups()
        r=dict(level=level,target=target,predictor=var,b=float(b),se=float(se),z=float(z),p=float(p))
        if level=='Additional':extra.append(r)
        elif op=='ON' and target:rows.append(r)
    elif line.strip() and not m and ('Variances' in line or 'Intercepts' in line):target=None;op=None
assert len(rows)==42, len(rows)
pd.DataFrame(rows).to_csv(OUT/'Study1_path_coefficients.csv',index=False)
pd.DataFrame(extra).to_csv(OUT/'Study1_indirect_effects_and_contrasts.csv',index=False)

def pf(p):return '< .001' if p==0 else f'{p:.3f}'
def bf(b):return f'{b:.3f}'
def star(p):return '***' if p<.001 else '**' if p<.01 else '*' if p<.05 else ''

def figure(level):
    # A coefficient map avoids nine crossing a-path arrows while displaying every focal path.
    W,H=1800,970
    im=Image.new('RGB',(W,H),'white'); draw=ImageDraw.Draw(im)
    fontfile='C:/Windows/Fonts/arial.ttf';boldfile='C:/Windows/Fonts/arialbd.ttf'
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="white"/>']
    def txt(x,y,s,size=27,bold=False,color='#111111',anchor='left'):
        f=ImageFont.truetype(boldfile if bold else fontfile,size)
        width=draw.textlength(s,font=f);xx=x-width/2 if anchor=='middle' else x
        draw.text((xx,y),s,font=f,fill=color)
        svg.append(f'<text x="{x}" y="{y+size*.86}" font-family="Arial" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}" text-anchor="{"middle" if anchor=="middle" else "start"}">{escape(s)}</text>')
    def rect(x,y,w,h,fill='#ffffff'):
        draw.rectangle((x,y,x+w,y+h),fill=fill,outline='#c4c8cc',width=2)
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="#c4c8cc" stroke-width="2"/>')
    def arrow(x1,y1,x2,y2,color):
        draw.line((x1,y1,x2,y2),fill=color,width=4)
        angle=math.atan2(y2-y1,x2-x1)
        pts=[(x2,y2),(x2-17*math.cos(angle-.5),y2-17*math.sin(angle-.5)),(x2-17*math.cos(angle+.5),y2-17*math.sin(angle+.5))]
        draw.polygon(pts,fill=color)
        svg.append(f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{color}" stroke-width="4"/><polygon points="'+ ' '.join(f'{x},{y}' for x,y in pts)+f'" fill="{color}"/>')
    rr=[r for r in rows if r['level']==level]
    def get(t,x):return next(r for r in rr if r['target']==t and r['predictor']==x)
    iv=['L1IV1','L1IV2','L1IV3'] if level=='Within' else ['L2IV1','L2IV2','L2IV3']
    txt(55,28,f'{"A" if level=="Within" else "B"}  {level}-post paths',43,True)
    txt(55,90,'Unstandardized coefficients from the joint two-level Mplus model',25)
    txt(55,160,'Predictors to parallel responses',30,True)
    # Each row is a response, each column a predictor.
    short=['Realism','Novelty','Unpredictability'] if level=='Within' else ['Visual realism','Unexpectedness','Complexity']
    for j,label in enumerate(short):txt(465+j*210,220,label,25,True,anchor='middle')
    med=['MED1','MED2','MED3']
    yy=[335,485,635]
    for i,(target,y) in enumerate(zip(med,yy)):
        txt(65,y-14,names[target],27,True)
        for j,x in enumerate(iv):
            r=get(target,x);sig=r['p']<.05;color='#16677a' if sig else '#666666'
            rect(365+j*210,y-48,200,96,'#edf4f5' if sig else '#fafafa')
            txt(465+j*210,y-23,bf(r['b'])+star(r['p']),33,sig,color,anchor='middle')
        arrow(1005,y,1320,485,'#16677a' if get('DV1',target)['p']<.05 else '#999999')
        r=get('DV1',target)
        # Labels remain near the arrow origins, away from intersections.
        rect(1020,y-43,210,46)
        txt(1125,y-37,bf(r['b'])+star(r['p']),30,r['p']<.05,anchor='middle')
    txt(1050,220,'Response to desire',25,True)
    rect(1330,420,410,130,'#f4f6f7')
    txt(1535,449,'Creative trial',32,True,anchor='middle');txt(1535,490,'desire',32,True,anchor='middle')
    txt(55,755,'Direct predictor to desire paths',28,True)
    for j,x in enumerate(iv):
        r=get('DV1',x);txt(55+j*580,810,short[j]+': '+bf(r['b'])+star(r['p']),28)
    txt(55,890,'* p < .05    ** p < .01    *** p < .001. All focal paths are shown; gray indicates p >= .05.',23)
    txt(55,927,'Controls and response residual covariances are estimated but omitted here. Arrows indicate associations.',23)
    path=OUT/f'Study1_paths_{level.lower()}'
    im.save(path.with_suffix('.png'),dpi=(300,300));svg.append('</svg>');path.with_suffix('.svg').write_text('\n'.join(svg),encoding='utf-8')
    return path.with_suffix('.png')

within=figure('Within');between=figure('Between')
doc=Document();sec=doc.sections[0];sec.page_width=Inches(8.5);sec.page_height=Inches(11)
sec.top_margin=sec.bottom_margin=Inches(.7);sec.left_margin=sec.right_margin=Inches(.75)
normal=doc.styles['Normal'];normal.font.name='Times New Roman';normal.font.size=Pt(11)
normal.paragraph_format.space_after=Pt(6);normal.paragraph_format.line_spacing=1.08
for s in ['Title','Heading 1','Heading 2']:
    doc.styles[s].font.name='Times New Roman';doc.styles[s].font.color.rgb=RGBColor(0,0,0)
for style in doc.styles:
    for border in list(style.element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
doc.styles['Title'].font.size=Pt(21);doc.styles['Heading 1'].font.size=Pt(15)
footer=sec.footer.paragraphs[0];footer.alignment=2
run=footer.add_run();fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');run._r.append(fld)
def para(t):doc.add_paragraph(t)
def head(t):doc.add_heading(t,1)
def page(t):doc.add_page_break();head(t)
def table(headers,data,widths=None):
    t=doc.add_table(rows=1,cols=len(headers));t.autofit=False
    if widths:
        for col,w in zip(t.columns,widths):col.width=Inches(w)
    for c,s in zip(t.rows[0].cells,headers):c.text=s
    repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
    for row in data:
        for c,s in zip(t.add_row().cells,row):c.text=str(s)
    for i,row in enumerate(t.rows):
        for j,cell in enumerate(row.cells):
            if widths:cell.width=Inches(widths[j])
            pr=cell._tc.get_or_add_tcPr();borders=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'4');el.set(qn('w:color'),'D9D9D9');borders.append(el)
            pr.append(borders)
            if i==0:
                shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E7ECEF');pr.append(shade)
            for p in cell.paragraphs:
                p.paragraph_format.space_after=Pt(3);p.paragraph_format.space_before=Pt(3);p.paragraph_format.line_spacing=1
                for r in p.runs:r.font.size=Pt(9.5);r.bold=(i==0)
    return t

doc.add_heading('Technical Appendix',0)
para('From Appreciating Creativity to Wanting to Create')
para('Study 1 and the multimodal research prototype | 28 October 2026')
head('Scope and evidence status')
para('This appendix documents the existing Reddit study, its two-level path model, and a working local prototype for extending artifact and comment coding across media. Historical results are distinguished from newly compiled candidate measurement plans. The prototype has been exercised offline using existing Study 1 ratings. Its live API adapters, newly proposed measures and applications to other media have not been empirically validated.')
head('Sample and linkage')
para('The existing cleaned corpus contains 18,654 comments linked to 1,596 posts from r/aivideo and r/aivideos, targeting posts and comments dated December 2025. This starting corpus is not restricted to verified playable videos. The analysis retains records with video status equal to 1, no video-rating error, and a playable-video flag equal to 1. These conditions retain 17,287 comments. Excluding 3,689 records with missing exogenous variables yields 13,598 comments nested within 1,191 posts.')
para('Numeric comment and post identifiers provide the linkage. Each comment belongs to one post; artifact ratings are constant within a post. The release contains only final-analysis comments and associated posts. Original-poster replies were excluded during earlier cleaning using the submitter flag, with author matching as a fallback when the flag was unavailable. This identifies the posting account, not necessarily the creator of the artifact. The prototype does not reapply or independently validate all earlier raw-data cleaning steps.')
head('Historical AI coding')
para('Video and comment inputs were coded independently. Historical run records identify Gemini 3.8 Flash for video coding and GPT-6 Luna for comment coding. The video workflow used agentic video inspection. Comment coding occurred in two passes: the v2 pass coded the broader psychological variable set, and the v3 supplement added content curiosity, production curiosity, creative trial desire and creative trial intention. Final analysis variables therefore do not all come from one joint prompt.')
para('Both sources used integer ratings from 1 to 10. Comment anchors were 1 = not at all, 2–3 = slightly, 4–5 = moderately, 6–8 = quite a bit, and 9–10 = to a great extent. Video anchors were 1 = minimum, 2–3 = low, 4–5 = moderate, 6–7 = high, 8–9 = very high, and 10 = maximum. Insufficient evidence was recorded as missing and exported as −999 for Mplus. These are AI-coded expressions and artifact assessments, not participant-completed validated scales.')

page('Measures and interpretation')
mapping=pd.read_csv(ROOT/'study1_reference/variable_map_v3.csv').set_index('mplus_variable')
selected=['v_real','v_compl','v_unexp','realism','novelty','unpred','c_curios','p_curios','enjoy','try_des']
defs={x:str(mapping.loc[x,'coding_definition']) for x in selected}
table(['Variable','Source','Historical coding definition'],[(x,'Video' if x.startswith('v_') else 'Comment',defs[x]) for x in selected],[.85,.85,5.3])
para('Definitions above are taken from the existing variable map. Historical definitions differ from the new cross-media candidate plans. In particular, comment unpredictability combines algorithmic unpredictability with events exceeding expectations; it should not be treated as a pure measure of production-process unpredictability. Video visual realism and comment-expressed narrative realism are related but distinct targets.')
para('Creative trial desire denotes an expressed wish to try creation. It does not establish actual creative behavior, successful learning, or a temporal transition from consumer to producer. Minimum ratings can reflect a lack of expressed evidence in a short comment rather than an absence of the corresponding internal state.')

page('Statistical specification')
para('The historical model was estimated in Mplus 8.11 using TYPE = TWOLEVEL and robust maximum likelihood (MLR), with post_uid as the cluster identifier. Ratings were treated as continuous. Within-post predictors were perceived realism, perceived novelty and perceived unpredictability. These variables and comment score were group-mean centered. Between-post predictors were video visual realism, event unexpectedness and visual complexity. Video predictors, post comment count and post score divided by 100 were grand-mean centered. The historical model did not log-transform these controls.')
para('At each level, content curiosity, production curiosity and enjoyment were modeled as parallel responses. Creative trial desire was regressed on all three responses and the level-specific predictors and controls. Residual covariances among the three responses were freely estimated at each level. The between-post paths concern between components of comment outcomes; they are not estimates of within-post slopes. All figure and table coefficients are unstandardized.')
para('Mplus excluded cases missing any exogenous variable. Missing outcomes were handled through the likelihood under the model’s missing-at-random assumptions. The model terminated normally. It has zero degrees of freedom, so global fit indices cannot validate its theoretical structure. The reported information-matrix condition number is approximately 1.47 × 10⁻⁷. Within-post constancy warnings and strong floor concentration warrant caution when interpreting the estimates.')
para('Specific indirect associations were defined as products of same-level, unstandardized path coefficients in MODEL CONSTRAINT. Table 4 reports the original Mplus delta-method standard errors and p values. Monte Carlo confidence intervals are not reported here. Any subsequent Monte Carlo analysis must use coefficient estimates and their covariance matrix on the same scale. No causal mediation claim follows from the contemporaneous observational comments.')
para('Production curiosity is positively associated with trial desire within posts (b = .121, p < .001) and between posts (b = .348, p = .002). The corresponding coefficient contrasts with content curiosity and enjoyment are reported alongside the indirect associations. Nonsignificant enjoyment paths do not demonstrate a zero effect or establish that enjoyment prevents creation.')
head('Distribution and selection limitations')
para('Creative trial desire is observed for 13,036 final-sample comments. Of these, 199 have scores above 1, leaving 98.47% at the minimum. Production curiosity is also strongly concentrated at the minimum. A continuous-rating model should therefore be regarded as preliminary; a presence-versus-intensity sensitivity analysis is appropriate. Commenters are a self-selected subset of viewers, and the model does not account for the same author appearing across multiple posts. Text-based variables may share linguistic evidence and coding errors.')

page('Prototype design and current capabilities')
para('The prototype accepts a research question, a modality and optional literature excerpts. A structured-output model proposes artifact-level dimensions and comment-level responses, with definitions, exclusions, scale anchors, rationale and tentative correspondence pairs. The proposal prompt prohibits invented references and limits citation use to material supplied in the brief. Citations remain unverified until independently checked. No autonomous literature search is implemented.')
para('A deterministic compiler validates the plan and creates separate artifact and comment prompts, JSON schemas and runnable Python wrappers. AI-generated content is treated as configuration rather than executable code. A plan hash detects subsequent edits. The compiled example plans cover video, music, still images and writing. They were authored as candidate examples in this development session, not returned by a paid API execution or established as validated measures.')
para('The coding adapters accept text comments independently of the artifact. Writing is submitted as text; video, audio and image files use a Gemini inline-media adapter with a conservative 15 MB limit. The OpenAI adapter supports text tasks. Live execution requires an explicit command flag, model identifier and a locally configured key. Requests are sequential, completed records can be resumed, input hashes detect changed content, and errors remain distinct from missing or minimum ratings. Large-file uploads, URL retrieval and agentic video exploration are not implemented in the new generic adapter.')
para('The analysis engine verifies unique IDs and many-to-one joins, excludes failed records with counts, preserves missing ratings, and exports descriptive distributions. Correspondence tests use equal-weight post-level Pearson correlations with 2,000 artifact bootstrap draws. Exploratory within-artifact regressions use group-demeaned complete cases; between-artifact regressions use observed post means. These regressions are separate demonstrations and do not reproduce the historical joint Mplus SEM. They do not perform automatic significance-based path selection, causal mediation or measurement-invariance tests.')
para('The demonstration uses the 13,598-comment final sample and existing ratings without new API charges. Six offline tests check score validation, version integrity, duplicate and unmatched IDs, missing/error handling, and recovery of a known regression slope. Live provider execution and new-media coding accuracy remain untested. This release is a proof of concept for a reusable research workflow, not evidence that automatically generated dimensions are valid or comparable across modalities.')
head('Cross source correspondence')
cp=ROOT/'results/study1_demo/correspondence.csv'
if cp.exists():
    cs=pd.read_csv(cp)
    for x,y in [('v_real','realism'),('v_unexp','unpred')]:
        r=cs[(cs.artifact_variable==x)&(cs.comment_variable==y)].iloc[0]
        para(f'{x} and post-mean {y}: r = {r.r:.3f}, percentile 95% CI [{r.ci_low:.3f}, {r.ci_high:.3f}], across {int(r.n_posts):,} posts. This is an unadjusted association between distinct measurement sources, not an accuracy estimate.')

page('Study 1 path coefficient maps')
para('Figure 1. All focal paths in the historical two-level model. Each matrix cell is a predictor-to-response coefficient. Arrows show the response-to-desire paths. Direct predictor-to-desire paths appear beneath each panel. Between-post responses represent latent between components, not raw post averages.')
doc.add_picture(str(within),width=Inches(7))
doc.add_picture(str(between),width=Inches(7))
para('Controls and residual covariances are omitted from the figures for readability and retained in the estimated model. Values reflect the output’s three-decimal rounding. Stars use the printed p values. Gray paths remain in the model.')

for level in ['Within','Between']:
    page(f'{level} post path estimates')
    para(f'Table {2 if level=="Within" else 3}. Unstandardized coefficients from the historical Mplus model. All regression paths, including controls, are reported.')
    data=[]
    for r in rows:
        if r['level']==level:data.append([names[r['target']],names[r['predictor']],bf(r['b']),bf(r['se']),pf(r['p'])])
    table(['Outcome','Predictor','b','SE','p'],data,[1.75,2.65,.8,.8,1])
    para('A printed coefficient or SE of 0.000 reflects rounding rather than an exact zero. P values are taken from the original output; 0.000 is reported as p < .001. The sample comprises 13,598 comments nested within 1,191 posts, with outcome-specific missingness retained.')

page('Indirect associations and coefficient contrasts')
para('Table 4. Original Mplus MODEL CONSTRAINT estimates, with delta-method standard errors. These are associational products, not causal mediation effects. No Monte Carlo confidence intervals are reported in this appendix.')
descriptions={}
for prefix,ivs in [('IW',{'R':'Realism','N':'Novelty','U':'Unpredictability'}),('IB',{'R':'Visual realism','U':'Event unexpectedness','X':'Visual complexity'})]:
    for middle,med in [('C','content curiosity'),('P','production curiosity'),('E','enjoyment')]:
        for suffix,label in ivs.items():descriptions[prefix+middle+suffix]=label+' via '+med
descriptions.update(DWPC='Production minus content slope',DWPE='Production minus enjoyment slope',DBPC='Production minus content slope',DBPE='Production minus enjoyment slope')
table(['Level','Indirect path or contrast','Estimate','SE','p'],[
 ['Within' if r['predictor'].startswith(('IW','DW')) else 'Between',descriptions[r['predictor']],bf(r['b']),bf(r['se']),pf(r['p'])] for r in extra],[.65,3.7,.9,.8,.95])
para('Source: iv med dv level2.out, generated 23 October 2026. Products and contrasts use the same unstandardized model parameters. Effects that print as 0.000 may be small positive or negative values. Confidence intervals should not be reconstructed from rounded standard errors.')

page('Reproducibility and references')
para('The accompanying multimodal_research_prototype directory contains pipeline.py, analysis.py, the proposal prompt, candidate plans, generated wrappers, tests, final-sample data and the historical Mplus reference files. README.md provides commands. No API keys are included. The demonstration’s inputs are existing ratings; running the generic coder would create a new measurement version and should not overwrite historical scores.')
para('The final-sample-only Mplus input retains the model specification but updates the variable list to the retained analysis columns and removes the already applied selection filter. Its exclusion count will differ from the archived full-input output if rerun. The original output is retained as the source of the appendix coefficients; a new Mplus run was not required for figure extraction.')
para('Further development should evaluate the proposed dimensions against independently assessed evidence, assess construct overlap and cross-domain comparability, and test provider execution on representative media. Experiments that manipulate artifact characteristics and observe actual creative choices remain future work. Neither automatic dimension proposal nor cross-source correlation alone establishes measurement validity.')
refs=[
'Gilardi, F., Alizadeh, M., and Kubli, M. (2023). ChatGPT outperforms crowd workers for text-annotation tasks. Proceedings of the National Academy of Sciences, 120(30), e2305016120. https://doi.org/10.1073/pnas.2305016120',
'Ziems, C., Held, W., Shaikh, O., Chen, J., Zhang, Z., and Yang, D. (2024). Can large language models transform computational social science? Computational Linguistics, 50(1), 237–291. https://doi.org/10.1162/coli_a_00502',
'Preacher, K. J., Zyphur, M. J., and Zhang, Z. (2010). A general multilevel SEM framework for assessing multilevel mediation. Psychological Methods, 15(3), 209–233. https://doi.org/10.1037/a0020141',
'Preacher, K. J., and Selig, J. P. (2012). Advantages of Monte Carlo confidence intervals for indirect effects. Communication Methods and Measures, 6(2), 77–98. https://doi.org/10.1080/19312458.2012.679848',
'Muthén, L. K., and Muthén, B. O. (1998–2017). Mplus User’s Guide (8th ed.). Muthén & Muthén.',
'Google AI for Developers. Structured outputs and video understanding documentation. https://ai.google.dev/gemini-api/docs/structured-output and https://ai.google.dev/gemini-api/docs/video-understanding. Accessed 28 October 2026.',
'OpenAI. Structured model outputs documentation. https://developers.openai.com/api/docs/guides/structured-outputs. Accessed 28 October 2026.']
for r in refs:para(r)
doc.save(OUT/'Technical_Appendix_Study1_and_Prototype.docx')
print(str(OUT/'Technical_Appendix_Study1_and_Prototype.docx'))
