"""Single local table. A lock and version token reject duplicate/stale commands."""
from pathlib import Path
from contextlib import asynccontextmanager
from threading import Lock
from typing import Literal
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, StrictInt
from .game import Game, BotExecutionError
from .agents import Decision
from .views import observe
from .presentation import table_details

@asynccontextmanager
async def lifespan(app):
    yield
    log_telemetry()

app = FastAPI(title='PokerMind', docs_url=None, redoc_url=None, lifespan=lifespan)
app.mount('/static', StaticFiles(directory=Path(__file__).parent / 'static'), name='static')
def configured_game():
    import os
    from .teacher import TeacherAgent, TeacherConfig
    from .learning.learned import LearnedAgent, load_resource, PROJECT_ROOT
    mode=os.environ.get('POKERMIND_BOTS','learned')
    if mode not in ('baseline','teacher','learned'):
        raise ValueError('POKERMIND_BOTS must be baseline, teacher or learned')
    policies=None
    info=dict(mode=mode,label='Regelbasierte Vergleichsgegner',version=None)
    if mode=='teacher':
        config=TeacherConfig(samples=int(os.environ.get('POKERMIND_SAMPLES','128')))
        seed=int(os.environ.get('POKERMIND_TEACHER_SEED','1'))
        policies=[TeacherAgent(seed+i,config) for i in range(4)]
        info=dict(mode=mode,label='Teacher · Beispielstrategie',version=TeacherAgent.version)
    elif mode=='learned':
        path=Path(os.environ.get('POKERMIND_MODEL','models/imitation-v1')).expanduser()
        if not path.is_absolute():path=PROJECT_ROOT/path
        resource=load_resource(str(path.resolve()))
        policies=[None]+[LearnedAgent(resource) for _ in range(3)]
        info=dict(mode=mode,label='Trainierte KI · Random Forest',version=resource.name)
    result=Game(policies=policies)
    result.bot_info=info
    return result

def public_state():
    result=observe(game)
    result['opponents']=dict(game.bot_info)
    result['table']=table_details(game)
    result['halted']=game.halted
    result['message']=game.failure_message if game.halted else None
    if game.halted:
        result['legal']=dict(fold=False,call=None,raise_min=None,raise_max=None,all_in=None)
        result['can_start']=False
    return result

game = configured_game()
lock = Lock()

class Command(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: StrictInt
    action: Literal['start', 'reset', 'fold', 'call', 'raise']
    amount: StrictInt | None = None

@app.get('/')
def index():
    return FileResponse(Path(__file__).parent / 'static' / 'index.html')

@app.get('/api/state')
def state():
    with lock:
        return public_state()

@app.post('/api/command')
def command(body: Command, request: Request):
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'Fremder Ursprung ist nicht erlaubt.')
    with lock:
        if body.version != game.version:
            raise HTTPException(409, 'Veralteter Spielstand. Ansicht wurde aktualisiert.')
        if game.halted and body.action!='reset':
            raise HTTPException(503,game.failure_message)
        try:
            if body.action == 'reset':
                game.reset()
            elif body.action == 'start':
                game.start_hand()
            else:
                game.act(0, Decision(body.action, body.amount))
            game.advance_bots()
        except BotExecutionError:
            raise HTTPException(503,game.failure_message) from None
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None
        return public_state()

def log_telemetry():
    import logging
    totals={key:sum(getattr(p,key,0) for p in game.policies if p is not None) for key in ('decisions','fallbacks','errors')}
    logging.getLogger('uvicorn.error').info('PokerMind aggregate inference counters: %s',totals)
