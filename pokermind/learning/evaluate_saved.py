"""Re-evaluate the locked artifacts without training or reselection."""
import argparse,json
from pathlib import Path
import joblib
from .experiment import read,hashfile,verify,evaluate
from ..teacher import TeacherConfig

def main():
 p=argparse.ArgumentParser();p.add_argument('--model',default='models/imitation-v1');p.add_argument('--data',default='data/main-v1');a=p.parse_args()
 root=Path(a.model);lock=read(root/'selection.json');meta=read(root/'metadata.json')
 assert hashfile(root/'experiment.json')==lock['configuration_hash']
 assert hashfile(root/'validation.json')==lock['validation_hash']
 for name,h in lock['artifacts'].items():assert hashfile(root/name)==h
 for name,h in meta['data_hashes'].items():assert hashfile(Path(a.data)/name)==h
 splits,obs,m=verify(a.data);result={}
 for name in lock['finalists']:
  score,_=evaluate(joblib.load(root/(name+'.joblib')),splits['test'],obs,TeacherConfig(**meta['teacher_config']))
  result[name]={k:score[k] for k in ('raw','filtered','raw_illegal_rate','fallback_rate')}
 print(json.dumps(dict(unchanged_winner=lock['winner'],test=result),indent=2))
if __name__=='__main__':main()
