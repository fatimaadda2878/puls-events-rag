from app.openagenda import fetch_all_events
class Resp:
 def __init__(self,p): self.p=p
 def raise_for_status(self): pass
 def json(self): return self.p
class Fake:
 def __init__(self): self.calls=[]
 def get(self,url,params,timeout):
  self.calls.append(params.copy()); o=params["offset"]
  return Resp({"total_count":3,"results":[{"uid":str(i),"title_fr":f"E{i}","location_city":"Paris","firstdate_begin":"2099-01-01T00:00:00+00:00"} for i in range(o,min(o+2,3))]})
def test_pagination(monkeypatch):
 import app.openagenda as oa; monkeypatch.setattr(oa,"OPENAGENDA_PAGE_SIZE",2)
 f=Fake(); ev=fetch_all_events(session=f); assert len(ev)==3; assert [c["offset"] for c in f.calls]==[0,2]
