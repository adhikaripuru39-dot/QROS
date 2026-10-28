"""Chronological selection and durable single-use holdout records."""
from __future__ import annotations
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False,default=str).encode()).hexdigest()


def chronological_split(n, embargo=0):
    if n<100 or embargo<0: raise ValueError("At least 100 observations and nonnegative embargo required")
    a,b=int(n*.6),int(n*.8)
    if min(a, b-a, n-b)<=embargo: raise ValueError("Embargo empties partition")
    return {"development":(0,a),"validation":(a+embargo,b),"oos":(b+embargo,n)}


class HoldoutConsumed(RuntimeError): pass


class EscrowLedger:
    """Local audit discipline, not a protection against an administrator copying data.

    Key is actual holdout bar digest, not candidate ID. A failed/interrupted
    evaluation remains consumed. Changing parameters cannot reset this record.
    """
    def __init__(self,path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS holdouts (holdout_hash TEXT PRIMARY KEY, binding TEXT NOT NULL, consumed_at TEXT NOT NULL, report_hash TEXT)")

    def consume(self,holdout_hash,binding):
        with sqlite3.connect(self.path,timeout=30) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("INSERT INTO holdouts VALUES (?,?,?,NULL)",(holdout_hash,json.dumps(binding,sort_keys=True),datetime.now(timezone.utc).isoformat()))
            except sqlite3.IntegrityError as exc:
                raise HoldoutConsumed("This holdout has already been consumed; new candidates require genuinely new unseen data") from exc

    def seal(self,holdout_hash,report_hash):
        with sqlite3.connect(self.path) as db:
            row=db.execute("SELECT report_hash FROM holdouts WHERE holdout_hash=?",(holdout_hash,)).fetchone()
            if row is None or row[0] is not None: raise HoldoutConsumed("Holdout missing or already sealed")
            db.execute("UPDATE holdouts SET report_hash=? WHERE holdout_hash=?",(report_hash,holdout_hash))


def walk_forward_windows(n,train=120,test=40,anchored=True,embargo=0):
    if min(train,test)<=0 or embargo<0: raise ValueError("Invalid windows")
    end=train
    while end+embargo+test<=n:
        yield (0 if anchored else end-train,end,end+embargo,end+embargo+test)
        end+=test


def walk_forward_optimize(observations,candidates,score,train=120,test=40,anchored=True,embargo=0):
    """score(candidate, partition) must fit exclusively on passed observations.

    The callback is rerun on each chronological train partition; test partitions
    never influence that fold's selected candidate. Outcomes retain all trials.
    """
    if not candidates: raise ValueError("Candidates required")
    output=[]
    for a,b,c,d in walk_forward_windows(len(observations),train,test,anchored,embargo):
        ranked=[(float(score(p,observations[a:b])),i,p) for i,p in enumerate(candidates)]
        import math
        if any(not math.isfinite(s) for s,_,_ in ranked): raise ValueError("Nonfinite fold score")
        best=max(ranked,key=lambda x:(x[0],-x[1]))
        output.append({"train":[a,b],"test":[c,d],"candidate":best[2],"train_score":best[0],"test_score":float(score(best[2],observations[c:d])),"training_trials":[x[0] for x in ranked]})
    return output
