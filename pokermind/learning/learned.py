"""Process-local read-only model resource; independent per-seat agent state."""
from dataclasses import dataclass
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path
import json,platform
from .inference import ModelAgent

PROJECT_ROOT=Path(__file__).resolve().parents[2]

@dataclass(frozen=True)
class ModelResource:
    estimator: object
    config: object
    name: str

@lru_cache(maxsize=None)
def load_resource(directory):
    path=Path(directory).resolve()
    try:
        meta=json.loads((path/'metadata.json').read_text())
        if platform.python_version_tuple()[:2]!=tuple(meta['python'].split('.')[:2]):
            raise ValueError('Python major/minor version mismatch')
        for library,required in meta['versions'].items():
            if version(library)!=required:raise ValueError(f'Library version mismatch: {library}')
        agent=ModelAgent(path)
        from sklearn.ensemble import RandomForestClassifier
        from ..data.schema import CLASSES
        if not isinstance(agent.model,RandomForestClassifier) or not set(agent.model.classes_)<=set(CLASSES):
            raise ValueError('Expected selected Random Forest with compatible classes')
        if any(agent.model.get_params()[k]!=v for k,v in meta['selected']['params'].items()):
            raise ValueError('Selected model parameters do not match metadata')
        return ModelResource(agent.model,agent.config,meta['package'])
    except Exception as exc:
        raise RuntimeError(f'PokerMind-Modell konnte nicht geladen werden: {path}. Artefakte, Schema und requirements.txt prüfen ({type(exc).__name__}).') from None

class LearnedAgent(ModelAgent):
    def __init__(self,resource):
        self.model=resource.estimator;self.config=resource.config
        self.last_prediction=None
        self.decisions=0;self.fallbacks=0;self.errors=0

    def decide(self,observation):
        try:
            decision=super().decide(observation)
        except Exception:
            self.errors+=1
            raise
        self.decisions+=1
        self.fallbacks+=int(self.last_prediction['fallback'])
        return decision
