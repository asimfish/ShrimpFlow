import time
from db import SessionLocal, engine
from sqlalchemy import text

with engine.connect() as conn:
    r = conn.execute(text('SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM event_atoms')).fetchone()
    min_ts, max_ts, count = r[0], r[1], r[2]
    print(f'atoms count={count}')
    fmt = '%Y-%m-%d %H:%M'
    print('atoms min time:', time.strftime(fmt, time.localtime(min_ts)))
    print('atoms max time:', time.strftime(fmt, time.localtime(max_ts)))

    now = int(time.time())
    cutoff_72h = now - 72 * 3600
    cutoff_720h = now - 720 * 3600
    print('cutoff_72h:', time.strftime(fmt, time.localtime(cutoff_72h)))
    print('cutoff_720h:', time.strftime(fmt, time.localtime(cutoff_720h)))

    c1 = conn.execute(text(f'SELECT COUNT(*) FROM event_atoms WHERE timestamp > {cutoff_72h}')).fetchone()[0]
    c2 = conn.execute(text(f'SELECT COUNT(*) FROM event_atoms WHERE timestamp > {cutoff_720h}')).fetchone()[0]
    print(f'atoms > 72h cutoff: {c1}')
    print(f'atoms > 720h cutoff: {c2}')

    # check episodes
    ep = conn.execute(text('SELECT MIN(start_ts), MAX(end_ts), COUNT(*) FROM episodes')).fetchone()
    print(f'episodes count={ep[2]}')

db = SessionLocal()
from services.episode_slicer import slice_episodes
# force lookback_hours=8760 (1 year) to bypass cutoff
result = slice_episodes(db, lookback_hours=8760)
print(f'episodes sliced (1y lookback): {result}')
db.close()
