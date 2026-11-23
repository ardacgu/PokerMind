"""Optional real-browser regression. Resets only the dedicated loopback QA table.

Start the normal application on a spare port, then run this script with --url.
Requires Node/npm and Chrome. The CLI is pinned; no frontend build is required.
"""
import argparse
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url',default='http://127.0.0.1:8002')
args=parser.parse_args()
assert urlsplit(args.url).hostname in {'127.0.0.1','localhost','::1'}, 'Local QA only'
assert urlsplit(args.url).port!=8000, 'Use a separate QA port, not the playing table'
cli=['npx','--yes','--package','@playwright/cli@0.1.23','playwright-cli','-s=pokermind-pace-regression']
output=ROOT/'output/playwright/pace-regression';output.mkdir(parents=True,exist_ok=True)
def invoke(*arguments):
 result=subprocess.run([*cli,*arguments],cwd=ROOT,capture_output=True,text=True)
 if result.returncode or '### Error' in result.stdout:
  raise RuntimeError(result.stdout+result.stderr)
 return result.stdout

CODE=r'''async page=>{
 const results=[];
 for(const [speed,width,height] of [['fast',1280,800],['instant',768,1024],['normal',390,844]]){
  const context=await page.context().browser().newContext({viewport:{width,height},hasTouch:width===390,isMobile:width===390});const p=await context.newPage();
  await p.goto('http://127.0.0.1:8002/');await p.locator('#reset').click();await p.getByRole('button',{name:'Neue Partie starten',exact:true}).click();await p.locator('#start:not(:disabled)').waitFor();
  await p.locator('#preferences summary').click();await p.locator('#speed').selectOption(speed);await p.locator('#preferences summary').click();
  await p.evaluate(()=>{
   window.__m={replacements:0,enabled:0,min:Infinity,max:0,ymin:Infinity,ymax:0,scrollChangesDuringBot:0};
   const nodes=[...document.querySelectorAll('#actions button,#actions input')];let oldY=scrollY,oldPhase='';
   const sample=()=>{const b=document.querySelector('#controls').getBoundingClientRect(),m=window.__m,phase=document.querySelector('.arena').dataset.phase;
    m.min=Math.min(m.min,b.height);m.max=Math.max(m.max,b.height);m.ymin=Math.min(m.ymin,b.y+scrollY);m.ymax=Math.max(m.ymax,b.y+scrollY);
    if(nodes.some(n=>!n.isConnected))m.replacements++;
    if(document.querySelector('#controls').dataset.mode!=='human'&&nodes.filter(n=>!['start','new-tournament'].includes(n.id)).some(n=>!n.disabled))m.enabled++;
    if(phase==='thinking'&&oldPhase==='thinking'&&Math.abs(scrollY-oldY)>1)m.scrollChangesDuringBot++;
    oldY=scrollY;oldPhase=phase;if(!window.__done)requestAnimationFrame(sample);
   };sample();
  });
  const start=Date.now();await p.locator('#start').click();
  for(let i=0;i<35;i++){
   await p.waitForFunction(()=>!document.querySelector('#call').disabled||!document.querySelector('#start').disabled||!document.querySelector('#new-tournament').disabled,{},{timeout:60000});
   if(await p.locator('#victory').isVisible())break;
   if(width===390)await p.locator('#call').tap();else await p.locator('#call').click();
  }
  await p.evaluate(()=>window.__done=true);
  const metrics=await p.evaluate(()=>window.__m);results.push({speed,width,height,elapsed:Date.now()-start,...metrics});
  if(metrics.replacements||metrics.enabled||metrics.max-metrics.min>1||metrics.ymax-metrics.ymin>1||metrics.scrollChangesDuringBot)throw Error(JSON.stringify(results));
  await p.screenshot({path:`output/playwright/pace-regression/${speed}-hand-${width}.png`,fullPage:true});
  // Next hand removes only settled presentation, not any action input nodes.
  if(await p.locator('#start').isVisible()){await p.locator('#start').click();await p.waitForFunction(()=>document.querySelector('#victory').hidden);}
  await p.locator('#reset').click();await p.getByRole('button',{name:'Neue Partie starten',exact:true}).click();await p.locator('#start:not(:disabled)').waitFor();
  await context.close();
 }
 await page.evaluate(x=>window.__modeProof=x,results);
}'''
invoke('open',args.url,'--headed')
try:
 transcript=invoke('run-code',CODE.replace('http://127.0.0.1:8002',args.url.rstrip('/')))
 (output/'steps.txt').write_text(transcript)
 raw=invoke('eval','JSON.stringify(window.__modeProof)')
 data=json.loads(json.loads(raw.split('### Result\n',1)[1].splitlines()[0]))
 (output/'results.json').write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps(data,indent=2))
finally:
 invoke('close')
