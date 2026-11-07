import pytest
from fastapi.testclient import TestClient
from pokermind import server
from pokermind.game import Game

@pytest.fixture
def client():
    server.game=Game(1)
    return TestClient(server.app)

def test_http_hand_raise_duplicate_restart(client):
    assert client.get('/').status_code==200
    s=client.get('/api/state').json()
    def post(action,amount=None,version=None):
        return client.post('/api/command',json={'version':s['version'] if version is None else version,'action':action,'amount':amount})
    s=post('start').json(); old=s['version']
    assert post('raise',s['legal']['raise_min']-1).status_code==400
    s=post('raise',s['legal']['raise_min']).json()
    assert post('call',version=old).status_code==409
    while not s['finished']: s=post('call').json()
    assert s['result'] and client.get('/api/state').json()==s
    s=post('reset').json()
    assert [p['stack'] for p in s['players']]==[2000]*4 and s['hand']==0

def test_api_validation_origin_and_no_debug_leaks(client):
    version=client.get('/api/state').json()['version']
    assert client.post('/api/command',json={'version':version,'action':'raise','amount':1.5}).status_code==422
    assert client.post('/api/command',json={'version':version,'action':'call','seat':1}).status_code==422
    assert client.post('/api/command',json={'version':version,'action':'start'},headers={'origin':'https://other.example'}).status_code==403
    assert client.post('/api/command',json={'version':version,'action':'call'}).status_code==400
