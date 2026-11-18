import math
from fastapi import HTTPException
from src.models.entities import Staffing
def build_schedule(future_rows,capacity):
 schedule=[]
 for p in future_rows:
  lower_staff=math.ceil(p['lower']/capacity)
  if p['upper'] is None:
   upper_staff=None;signable=False
   reason='需求上界未知（证据不足/连日触顶），只能给下界人数，留待核对'
  else:
   upper_staff=math.ceil(p['upper']/capacity);signable=lower_staff==upper_staff
   reason='区间换算人数一致，可签核' if signable else f'下界{lower_staff}人、上界{upper_staff}人不一致，留待核对'
  schedule.append({**p,'capacity':capacity,'lower_staff':lower_staff,'upper_staff':upper_staff,'staff':lower_staff,'signable':signable,'signable_reason':reason})
 return schedule
def draft(s,run,data):
 if run.state!='done':raise HTTPException(409,'预测完成后才能生成排班建议')
 if data.model not in run.result['future']:raise HTTPException(422,'该预测版本不包含所选模型')
 schedule=build_schedule(run.result['future'][data.model],data.capacity)
 row=Staffing(**data.model_dump(),schedule=schedule);s.add(row);s.commit();return row
def approve(row):
 if row.status!='draft':raise HTTPException(409,'不可重复签核')
 blocked=[p['day'] for p in row.schedule if not p.get('signable')]
 if blocked:
  raise HTTPException(409,'存在人数区间不一致或上界未知的日期，不能签核：'+','.join(blocked))
 row.status='approved';return row
