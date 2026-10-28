from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from qros.api.app import create_app
from qros.config.settings import Settings, load_firm_profiles
from qros.config.schemas import InternalLimits
from qros.db.session import session_factory, session_scope
from qros.risk.drawdown import AccountState
from qros.risk.sizing import ContractSpec

@pytest.fixture
def firm():
    return load_firm_profiles()["example_100k_static"]

@pytest.fixture
def limits():
    return InternalLimits()

@pytest.fixture
def account():
    return AccountState(100000,100000,100000,100000,100000,105000,103000)

@pytest.fixture
def spec():
    return ContractSpec("EURUSD",0.00001,1,0.00001,0.01,50,0.01,10)

@pytest.fixture
def factory(tmp_path):
    return session_factory(f"sqlite:///{(tmp_path/'test.db').as_posix()}")

@pytest.fixture
def client(tmp_path):
    settings = Settings(database_url=f"sqlite:///{(tmp_path/'api.db').as_posix()}",api_token="test-owner-secret",_env_file=None)
    with TestClient(create_app(settings)) as client:
        client.headers.update({"Authorization": "Bearer test-owner-secret"})
        yield client

