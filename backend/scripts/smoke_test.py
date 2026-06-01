import os
# ensure the app uses local sqlite for this test
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///C:/Users/Admin/Desktop/VEKTRA/backend/test.db'
from sqlalchemy import create_engine
from app.db.models import Base
# create a sync sqlite DB for metadata
engine = create_engine('sqlite:///C:/Users/Admin/Desktop/VEKTRA/backend/test.db')
Base.metadata.create_all(bind=engine)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# register
resp = client.post('/api/v1/auth/register', json={'username':'smoketest','email':'smoketest@example.com','password':'secret'})
print('register', resp.status_code, resp.json() if resp.status_code==200 else resp.text)

# token
resp2 = client.post('/api/v1/auth/token', data={'username':'smoketest','password':'secret'})
print('token', resp2.status_code, resp2.json() if resp2.status_code==200 else resp2.text)

if resp2.status_code==200:
    token = resp2.json().get('access_token')
    headers = {'Authorization': f'Bearer {token}'}
    me = client.get('/api/v1/users/me', headers=headers)
    print('me', me.status_code, me.json() if me.status_code==200 else me.text)
else:
    print('token request failed; skipping /users/me')
