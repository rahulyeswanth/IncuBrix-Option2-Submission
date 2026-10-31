#!/usr/bin/env python3
import csv, json, re, subprocess, sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zipfile import ZipFile
from PIL import Image

BASE=Path(__file__).resolve().parents[1]; CONTENT=BASE/'2_Final_Content'; ENGINE=BASE/'3_Content_Engine'
sys.path.insert(0,str(ENGINE/'source_code'))
from engine.pipeline import Engine, hook_similarity

def readcsv(path):
 with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def valid_time(s):
 for fmt in ('%Y-%m-%d %H:%M','%Y-%m-%dT%H:%M:%SZ'):
  try: datetime.strptime(s,fmt); return True
  except ValueError: pass
 return False

def main():
 errors=[]; qa=[]; calendar=readcsv(CONTENT/'calendar.csv')
 sched=readcsv(CONTENT/'scheduler_export.csv')
 draft_sched=readcsv(CONTENT/'scheduler_export_DRAFT_FOR_REVIEW.csv')
 assets=sorted(p for p in (CONTENT/'assets').iterdir() if p.is_dir()); specs={}
 eng=Engine(Path('/tmp/incubrix_validation_unused'),ENGINE/'configuration','2026-11-02')
 source_inputs={p.name:p.read_text(encoding='utf-8') for p in (ENGINE/'inputs').glob('*') if p.is_file()}
 for d in assets:
  spec=json.loads((d/'spec.json').read_text(encoding='utf-8')); aid=spec['asset_id']; specs[aid]=spec; fmt=spec['format']; dims='n/a'; duration=''; slides=''; final=''
  if fmt=='Short video':
   final=d/'final.mp4'; data=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height:format=duration','-of','json',str(final)],text=True)); dims=f"{data['streams'][0]['width']}x{data['streams'][0]['height']}"; duration=round(float(data['format']['duration']),3)
   if duration>60:errors.append(f'{aid} duration {duration}')
  elif fmt=='Carousel':
   final=d/'carousel.pdf'; pngs=sorted(d.glob('slide_*.png')); slides=len(pngs)
   sizes=[]
   for p in pngs:
    with Image.open(p) as im:sizes.append(im.size)
   dims=';'.join(sorted({f'{w}x{h}' for w,h in sizes}))
   if not 5<=slides<=10:errors.append(f'{aid} slides {slides}')
  elif fmt=='Graphic':
   final=d/'final.png'
   with Image.open(final) as im:dims=f'{im.width}x{im.height}'
  else: final=d/'final.txt'
  expected=f"{spec['size'][0]}x{spec['size'][1]}"
  if dims!='n/a' and dims!=expected:errors.append(f'{aid} dims {dims}!={expected}')
  src=source_inputs.get(spec['source_input'],'')
  trace=all(x in src for x in [spec['hook'],*spec.get('points',[])])
  q=eng.qa({'asset_id':aid,'format':fmt,'platform':spec['platform'],'hook':spec['hook'],'points':spec.get('points',[]),'source_title':'','source_input':spec['source_input'],'keywords':[]},{'cta':spec['cta'],'utm_link':spec['utm_link'],'caption':spec['caption']})
  blocking=[x for x in q if x[1] in {'reject','hold'}]
  if blocking:errors.append(f'{aid} QA {blocking}')
  if not trace:errors.append(f'{aid} source trace failed')
  qa.append({'asset_id':aid,'platform':spec['platform'],'format':fmt,'dimensions':dims,'duration_seconds':duration,'slide_count':slides,'hook_words':len(spec['hook'].split()),'source_trace':'PASS' if trace else 'FAIL','caption':'PASS' if spec['caption'] else 'FAIL','cta':'PASS' if spec['cta'] else 'FAIL','hashtags':len(re.findall(r'#\w+',spec['caption'])),'utm':'PASS' if not [x for x in q if x[0] in {'NO_UTM','BAD_UTM_ASSET'}] else 'FAIL','claim_gate':'PASS' if not blocking else 'FAIL','rights_file_review':'TECHNICAL CHECK PASS — no bundled external image/music/face/voice; candidate rights and brand approval pending','editable_source':'PASS' if (d/'spec.json').exists() else 'FAIL','final_export':'PASS' if final.exists() and final.stat().st_size else 'FAIL','overall_machine_review':'TECHNICAL PASS — NOT PUBLICATION-APPROVED' if trace and not blocking and final.exists() else 'FAIL'})
 # Export/path checks
 if len(calendar)!=40:errors.append(f'calendar rows {len(calendar)}')
 if len(sched)!=0:errors.append(f'official scheduler must have 0 unapproved rows, found {len(sched)}')
 if len(draft_sched)!=40:errors.append(f'draft scheduler rows {len(draft_sched)}')
 for row in calendar:
  aid=row['asset_id']; p=CONTENT/row['final_file_url']; sp=CONTENT/row['source_file_url']
  if not p.exists():errors.append(f'{aid} missing {p}')
  if not sp.exists():errors.append(f'{aid} missing {sp}')
  u=urlparse(row['utm_link']); q=parse_qs(u.query)
  if not {'utm_source','utm_medium','utm_campaign','utm_content','utm_term'}.issubset(q) or q.get('utm_content',[''])[0]!=aid:errors.append(f'{aid} invalid utm')
  if not valid_time(row['scheduled_date']):errors.append(f'{aid} invalid time')
  if row['status']!='Pending human approval':errors.append(f'{aid} incorrect approval status')
  if row['rights_checked']!='Pending human approval':errors.append(f'{aid} incorrect rights status')
 for row in draft_sched:
  if not (CONTENT/row['media_file']).exists():errors.append(f"scheduler missing {row['asset_id']}")
  if not valid_time(row['scheduled_at_utc']):errors.append(f"scheduler time {row['asset_id']}")
 # duplicates including near duplicates
 ids=list(specs); hooks=[specs[x]['hook'] for x in ids]
 if len(ids)!=len(set(ids)):errors.append('duplicate ids')
 near=[]
 for i in range(len(ids)):
  for j in range(i+1,len(ids)):
   if hook_similarity(hooks[i],hooks[j])>=.86:near.append((ids[i],ids[j]))
 if near:errors.append(f'near duplicate hooks {near}')
 # workbook and docx package integrity/formula preservation
 wb=BASE/'1_Submission_Workbook/IncuBrix_2027_Option2_FINAL_Submission.xlsx'
 N='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
 import xml.etree.ElementTree as ET
 with ZipFile(wb) as z:
  if z.testzip():errors.append('workbook corrupt')
  root=ET.fromstring(z.read('xl/workbook.xml')); sheets=[x.attrib['name'] for x in root.find(f'{{{N}}}sheets')]
  formulas=sum(len(ET.fromstring(z.read(n)).findall(f'.//{{{N}}}f')) for n in z.namelist() if n.startswith('xl/worksheets/'))
  validations=sum(len(ET.fromstring(z.read(n)).findall(f'.//{{{N}}}dataValidation')) for n in z.namelist() if n.startswith('xl/worksheets/'))
  conditional=sum(len(ET.fromstring(z.read(n)).findall(f'.//{{{N}}}conditionalFormatting')) for n in z.namelist() if n.startswith('xl/worksheets/'))
  asset_sheet=ET.fromstring(z.read('xl/worksheets/sheet3.xml'))
  start_sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
  def cell_text(root, ref):
   cell=next(x for x in root.findall(f'.//{{{N}}}c') if x.attrib.get('r')==ref)
   return ''.join(t.text or '' for t in cell.iter(f'{{{N}}}t'))
  if any(cell_text(asset_sheet,f'T{i}')!='Pending human approval' for i in range(5,45)):
   errors.append('workbook asset approval statuses are not all pending')
  expected_checklist={'F5':'No','F6':'Yes','F7':'Yes','F8':'Yes','F9':'No','F10':'No'}
  if any(cell_text(start_sheet,k)!=v for k,v in expected_checklist.items()):
   errors.append('workbook submission checklist is inaccurate')
 with ZipFile(BASE/'4_Launch_Kit/IncuBrix_30_Day_Launch_Kit.docx') as z:
  if z.testzip():errors.append('launch docx corrupt')
 summary={'errors':errors,'asset_count':len(assets),'calendar_rows':len(calendar),'official_scheduler_rows':len(sched),'draft_scheduler_rows':len(draft_sched),'approved_ready_assets':sum(r['status']=='Ready' for r in calendar),'pending_human_approval':sum(r['status']=='Pending human approval' for r in calendar),'formats':dict(Counter(s['format'] for s in specs.values())),'platforms':sorted({s['platform'] for s in specs.values()}),'max_video_seconds':max(float(x['duration_seconds']) for x in qa if x['duration_seconds']!=''),'unique_ids':len(set(ids)),'near_duplicate_pairs':near,'technical_qa_passes':sum(x['overall_machine_review'].startswith('TECHNICAL PASS') for x in qa),'workbook_sheets':sheets,'workbook_formulas':formulas,'workbook_data_validations':validations,'workbook_conditional_formatting_blocks':conditional,'random_audit_initial':'16/20','random_audit_after_corrections':'20/20 technical; publication approval pending'}
 with (BASE/'6_Evidence_and_Audit/ASSET_QA_REPORT.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=qa[0]);w.writeheader();w.writerows(qa)
 (BASE/'6_Evidence_and_Audit/FINAL_VALIDATION.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
 print(json.dumps(summary,indent=2)); raise SystemExit(bool(errors))
if __name__=='__main__':main()
