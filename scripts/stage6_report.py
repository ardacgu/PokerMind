"""Regenerate stage 6 statistics/tables/figures from immutable session records."""
import argparse
from collections import Counter, defaultdict
import csv
from hashlib import sha256
import json
from pathlib import Path
import platform
import statistics as st
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
NAMES={'A':'Learned vs rules','B':'Teacher vs rules','C':'Rule target vs rules','D':'Learned in mixed table'}
COLORS=['#2563a6','#159174','#8c6b44','#9154a8']


def interval(values,seed,repetitions):
    if len(values)<2:return None
    rng=np.random.default_rng(seed)
    values=np.array(values,dtype=float)
    sampled=values[rng.integers(len(values),size=(repetitions,len(values)))].mean(axis=1)
    return np.percentile(sampled,[2.5,97.5]).tolist()


def summarize(records,identity,config):
    clean=[r for r in records if r['status']!='error']
    players=[next(p for p in r['players'] if p['identity']==identity) for r in clean]
    values=[p['net_chips'] for p in players]
    blocks=defaultdict(list)
    for r,p in zip(clean,players):blocks[r['seed']].append((r['rotation'],p['net_chips']))
    means={str(seed):st.mean(v for _,v in b) for seed,b in blocks.items() if {r for r,_ in b}==set(range(4))}
    complete=[(r,p) for r,p in zip(clean,players) if r['status']=='tournament_complete']
    actions=Counter();labels=Counter()
    for p in players:actions.update(p['actions']);labels.update(p['labels'])
    counts={key:sum(p[key] for p in players) for key in ('dealt_hands','all_in_actions','all_in_calls','all_in_raises','blind_all_ins','all_in_hands','facing_all_in_decisions','adapter_fallbacks','teacher_fallbacks','raw_illegal','errors')}
    return dict(n=len(clean),error_sessions=len(records)-len(clean),complete_blocks=len(means),
                mean=st.mean(values),median=st.median(values),sd=st.stdev(values) if len(values)>1 else 0,
                minimum=min(values),maximum=max(values),mean_ci95=interval(list(means.values()),config['bootstrap_seed'],config['bootstrap_replicates']),
                block_means=means,eliminations=sum(p['eliminated'] for p in players),
                tournaments=len(complete),caps=sum(r['status']=='hand_limit' for r in clean),
                tournament_wins=sum(p['tournament_win'] for _,p in complete),
                conditional_win_rate=st.mean(p['tournament_win'] for _,p in complete) if complete else None,
                completed_hands=sum(r['completed_hands'] for r in clean),actions=dict(actions),labels=dict(labels),
                seats={str(seat):dict(n=sum(p['seat']==seat for p in players),
                    mean=st.mean(p['net_chips'] for p in players if p['seat']==seat),
                    median=st.median(p['net_chips'] for p in players if p['seat']==seat)) for seat in range(4)},**counts)


def difference(left,right,config):
    shared=sorted(set(left['block_means']) & set(right['block_means']))
    values=[left['block_means'][s]-right['block_means'][s] for s in shared]
    return dict(blocks=len(shared),mean=st.mean(values),ci95=interval(values,config['bootstrap_seed'],config['bootstrap_replicates']),block_differences=dict(zip(shared,values)))


def savefig(fig,folder,name):
    fig.savefig(folder/f'{name}.png',dpi=180,bbox_inches='tight')
    fig.savefig(folder/f'{name}.svg',bbox_inches='tight')
    plt.close(fig)


def generate(directory):
    directory=Path(directory);config=json.loads((directory/'config.json').read_text())
    manifest=json.loads((directory/'manifest.json').read_text())
    records=[]
    for ident,expected in sorted(manifest['sessions'].items()):
        path=directory/'sessions'/f'{ident}.json'
        assert sha256(path.read_bytes()).hexdigest()==expected
        r=json.loads(path.read_text());assert r['id']==ident
        assert r['config_hash']==manifest['config_hash'] and r['provenance_hash']==manifest['provenance_hash']
        records.append(r)
    assert len({r['id'] for r in records})==len(records)
    groups={s:[r for r in records if r['scenario']==s] for s in config['scenarios']}
    summary={s:summarize(rs,'target',config) for s,rs in groups.items()}
    mixed={i:summarize(groups['D'],i,config) for i in ('target','teacher','rule2','rule3')}
    contrasts={f'{a}-{b}':difference(summary[a],summary[b],config) for a,b in [('A','B'),('A','C'),('B','C')]}
    contrasts['D learned-teacher']=difference(mixed['target'],mixed['teacher'],config)
    total=dict(sessions=len(records),hands=sum(r['completed_hands'] for r in records),
        statuses=dict(Counter(r['status'] for r in records)),
        wall_seconds=sum(i['wall_seconds'] for i in manifest['invocations'] if i['scheduled']),
        all_invocations_wall_seconds=sum(i['wall_seconds'] for i in manifest['invocations']),
        summed_session_seconds=sum(r['elapsed_seconds'] for r in records),
        action_count=sum(sum(p['actions'].values()) for r in records for p in r['players']),
        adapter_fallbacks=sum(p['adapter_fallbacks'] for r in records for p in r['players']),
        teacher_fallbacks=sum(p['teacher_fallbacks'] for r in records for p in r['players']),
        raw_illegal=sum(p['raw_illegal'] for r in records for p in r['players']),
        errors=sum(len(r['errors']) for r in records),
        missing_sessions=manifest['missing_sessions'])
    result=dict(total=total,scenarios=summary,mixed=mixed,paired_contrasts=contrasts,
        bootstrap=dict(seed=config['bootstrap_seed'],replicates=config['bootstrap_replicates'],unit='complete four-rotation seed block',method='percentile 95%, NumPy default_rng PCG64'),
        report_runtime=dict(python=platform.python_version(),numpy=np.__version__,matplotlib=matplotlib.__version__))
    (directory/'summary.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    with (directory/'sessions.jsonl').open('w') as f:
        for r in records:f.write(json.dumps(r,sort_keys=True)+'\n')
    with (directory/'players.csv').open('w',newline='') as f:
        rows=[]
        for r in records:
            for p in r['players']:
                row={k:r[k] for k in ('id','scenario','seed','rotation','status','completed_hands')}
                row.update({k:v for k,v in p.items() if k not in ('actions','labels')})
                row.update({'actions_'+k:p['actions'].get(k,0) for k in ('fold','check','call','raise')})
                row.update({'labels_'+k:p['labels'].get(k,0) for k in ('fold','check','call','raise','small','large','all_in','other')})
                rows.append(row)
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (directory/'block-means.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['scenario','seed','target_mean_net_chips'])
        for s,v in summary.items():
            for seed,mean in v['block_means'].items():w.writerow([s,seed,mean])
    folder=ROOT/'docs/stage6';folder.mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(9,4.6))
    means=[summary[s]['mean'] for s in 'ABCD'];cis=np.array([summary[s]['mean_ci95'] for s in 'ABCD']).T
    ax.bar(range(4),means,color=COLORS,width=.6)
    ax.errorbar(range(4),means,yerr=[np.array(means)-cis[0],cis[1]-np.array(means)],fmt='none',ecolor='#222222',capsize=5)
    ax.axhline(0,color='#333333',linewidth=.8);ax.set_xticks(range(4),[f'{s}: {NAMES[s]}\n{summary[s]["n"]} sessions / {summary[s]["complete_blocks"]} blocks' for s in 'ABCD'],fontsize=9)
    ax.set_ylabel('Mean net chips per session');ax.set_title('Frozen policies: terminal or 100-hand bankroll\n95% block bootstrap; C cancels exactly by rotation; D has a different lineup')
    savefig(fig,folder,'mean-chips')
    fig,ax=plt.subplots(figsize=(9,4.6))
    vals=[[next(p['net_chips'] for p in r['players'] if p['identity']=='target') for r in groups[s] if r['status']!='error'] for s in 'ABCD']
    ax.boxplot(vals,positions=range(4),showfliers=False,widths=.4)
    rng=np.random.default_rng(42)
    for i,ys in enumerate(vals):ax.scatter(i+rng.uniform(-.16,.16,len(ys)),ys,color=COLORS[i],alpha=.5,s=17)
    ax.axhline(0,color='#333333',linewidth=.8);ax.set_xticks(range(4),list('ABCD'));ax.set_ylabel('Target net chips per session')
    ax.set_title('Session outcome dispersion\nDots are dependent within blocks; boxes show median and quartiles')
    savefig(fig,folder,'dispersion')
    fig,ax=plt.subplots(figsize=(8,4.6))
    for s,color in zip('ABCD',COLORS):ax.plot(range(4),[summary[s]['seats'][str(i)]['mean'] for i in range(4)],'o-',label=f'{s}: {NAMES[s]}',color=color)
    ax.axhline(0,color='#333333',linewidth=.8);ax.set_xticks(range(4));ax.set_xlabel('Physical target seat (0–3)');ax.set_ylabel('Mean net chips per session')
    ax.set_title('Seat comparison (descriptive)\n12 observations per seat for A/B/C; 8 for D');ax.legend(fontsize=9)
    savefig(fig,folder,'seats')
    fig,ax=plt.subplots(figsize=(8,4.6));bottom=np.zeros(3)
    for category,color in zip(('fold','check','call','raise'),('#a33a4b','#5598ad','#d4a447','#5467ac')):
        percentages=np.array([100*summary[s]['actions'].get(category,0)/sum(summary[s]['actions'].values()) for s in 'ABC'])
        ax.bar(range(3),percentages,bottom=bottom,color=color,label=category)
        for i,v in enumerate(percentages):
            if v>4:ax.text(i,bottom[i]+v/2,f'{v:.1f}%',ha='center',va='center',color='white',weight='bold')
        bottom+=percentages
    ax.set_xticks(range(3),['Learned (A)','Teacher (B)','Rule target (C)']);ax.set_ylim(0,108);ax.set_ylabel('% of observed target decisions')
    ax.set_title('Action distributions on each policy’s visited states\nPooled descriptive proportions; not identical decision opportunities');ax.legend(ncol=4,loc='upper center',bbox_to_anchor=(.5,-.09))
    savefig(fig,folder,'actions')
    fig,ax=plt.subplots(figsize=(8,4.6));identities=list(mixed);means=[mixed[i]['mean'] for i in identities];cis=np.array([mixed[i]['mean_ci95'] for i in identities]).T
    ax.bar(range(4),means,color=[COLORS[0],COLORS[1],COLORS[2],'#b58a57'])
    ax.errorbar(range(4),means,yerr=[np.array(means)-cis[0],cis[1]-np.array(means)],fmt='none',ecolor='#222222',capsize=5)
    ax.axhline(0,color='#333333',linewidth=.8);ax.set_xticks(range(4),['Learned','Teacher','Rule (budget 220)','Rule (budget 360)']);ax.set_ylabel('Mean net chips per session')
    ax.set_title('D: direct mixed table (32 sessions / 8 blocks)\n95% block bootstrap intervals; outcomes within a table are coupled')
    savefig(fig,folder,'mixed')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',default='evaluations/stage6-v1');a=p.parse_args()
    print(json.dumps(generate(ROOT/a.input),indent=2))
