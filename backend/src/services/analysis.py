import math,json,hashlib
from datetime import date,timedelta
from src.constants.enums import UPPER_EVIDENCE_DAYS,UPPER_EVIDENCE_MIN_NORMAL
def holt(values,horizon,alpha,beta):
 if len(values)<2:raise ValueError('Holt至少需要2天数据')
 level=float(values[0]);trend=float(values[1]-values[0])
 for value in values[1:]:
  previous=level;level=alpha*value+(1-alpha)*(level+trend);trend=beta*(level-previous)+(1-beta)*trend
 return [level+h*trend for h in range(1,horizon+1)]
def seasonal(values,horizon):return [float(values[-7+i%7]) for i in range(horizon)]
def normalize_rows(rows):
 # 旧日结无 mark 键按 unknown 处理；显式录入的新数据始终带标记
 out=[]
 for r in sorted(rows,key=lambda r:r['day']):
  nr=dict(r);mark=nr.get('mark')
  nr['mark']=mark if mark in ('normal','capped','unknown') else 'unknown'
  out.append(nr)
 return out
def score(actual,predicted,window_capped,window_unknown):
 pairs=[(a,p) for a,p in zip(actual,predicted) if a!=0]
 if not actual:
  return {'mae':None,'mape':None,'mape_used':0,'zero_actual':0,'scored_days':0,'capped_days':window_capped,'unknown_days':window_unknown}
 errors=[abs(a-p) for a,p in zip(actual,predicted)]
 return {'mae':sum(errors)/len(errors),'mape':sum(abs(a-p)/a for a,p in pairs)/len(pairs)*100 if pairs else None,'mape_used':len(pairs),'zero_actual':len(actual)-len(pairs),'scored_days':len(actual),'capped_days':window_capped,'unknown_days':window_unknown}
def forecast(rows,backtest_days,alpha,beta):
 rows=normalize_rows(rows);days=[date.fromisoformat(r['day']) for r in rows]
 if len(rows)<backtest_days+28:raise ValueError(f'至少需要{backtest_days+28}个连续日量，保证回测前28天训练窗口')
 if len(set(days))!=len(days):raise ValueError('同网点存在重复日期，请先核对')
 gaps=[(a.isoformat(),b.isoformat()) for a,b in zip(days,days[1:]) if b-a!=timedelta(days=1)]
 if gaps:raise ValueError('日期不连续，缺口：'+str(gaps[:3])+'；不可将缺日当作零量')
 values=[r['volume'] for r in rows];marks=[r['mark'] for r in rows];start=len(values)-backtest_days
 predictions={'seasonal_naive':[],'holt':[]};clipped={'seasonal_naive':0,'holt':0}
 # walk-forward：每个回测日只用此前记录重新拟合；触顶/未知日的记录量仍作为可得历史参与训练
 for i in range(start,len(values)):
  train=values[:i]
  for model,raw in [('seasonal_naive',seasonal(train,1)[0]),('holt',holt(train,1,alpha,beta)[0])]:
   if raw<0:clipped[model]+=1
   predictions[model].append(max(0,raw))
 # 两法在同一组正常日上计算误差；触顶日只是下界、未知日标记不可信，均排除出评分
 normal_index=[j for j in range(backtest_days) if marks[start+j]=='normal']
 window_capped=sum(1 for m in marks[start:] if m=='capped');window_unknown=sum(1 for m in marks[start:] if m=='unknown')
 metrics={}
 for model,ps in predictions.items():
  actual=[values[start+j] for j in normal_index];pred=[ps[j] for j in normal_index]
  metrics[model]=score(actual,pred,window_capped,window_unknown)
 if normal_index:
  selected=min(metrics,key=lambda m:(metrics[m]['mae'],m!='seasonal_naive'))
  selection_reason=f'两法在相同的{len(normal_index)}个正常日上比较回测MAE，取较低者；同分选周季节朴素。触顶{window_capped}日、未知{window_unknown}日不参与评分。'
 else:
  selected='seasonal_naive'
  selection_reason=f'回测窗口没有正常日（触顶{window_capped}日、未知{window_unknown}日），无法按MAE选模，默认周季节朴素；结果需人工核对。'
 # 上界证据：预测原点前最近 UPPER_EVIDENCE_DAYS 个自然日内的正常日量
 origin=days[-1];window_start=origin-timedelta(days=UPPER_EVIDENCE_DAYS-1)
 evidence_volumes=[r['volume'] for r in rows if window_start<=date.fromisoformat(r['day'])<=origin and r['mark']=='normal']
 evidence_max=max(evidence_volumes) if len(evidence_volumes)>=UPPER_EVIDENCE_MIN_NORMAL else None
 upper_evidence={'window_days':UPPER_EVIDENCE_DAYS,'normal_days':len(evidence_volumes),'max_normal_volume':evidence_max,'window_start':window_start.isoformat(),'window_end':origin.isoformat(),'basis':'上界取近%d个自然日内正常日最大到达量；触顶量只是下界、未知日不参与上界证据。'%(UPPER_EVIDENCE_DAYS,) if evidence_max is not None else '近%d个自然日内正常日证据不足，需求上界保留未知（null），仅给下界参考。'%(UPPER_EVIDENCE_DAYS,)}
 capped_tail_streak=0
 for r in reversed(rows):
  if r['mark']=='capped':capped_tail_streak+=1
  else:break
 marks_summary={m:marks.count(m) for m in ('normal','capped','unknown')}
 future={m:[] for m in predictions}
 for model,raw in [('seasonal_naive',seasonal(values,7)),('holt',holt(values,7,alpha,beta))]:
  for h,p in enumerate(raw,1):
   lower=max(0,int(math.floor(p+.5)));upper=max(lower,evidence_max) if evidence_max is not None else None
   day=(origin+timedelta(days=h)).isoformat()
   basis='下界=模型预测四舍五入非负整数；上界=max(预测, 近%d日正常日最大量%d)'%(UPPER_EVIDENCE_DAYS,evidence_max) if upper is not None else '下界=模型预测四舍五入非负整数；上界未知（正常日证据不足），下界可作排班最低参考'
   future[model].append({'day':day,'raw':p,'prediction':lower,'lower':lower,'upper':upper,'clipped':p<0,'basis':basis})
 return dict(branch=rows[0]['branch'],n=len(rows),train_initial=start,backtest_days=backtest_days,alpha=alpha,beta=beta,marks_summary=marks_summary,capped_tail_streak=capped_tail_streak,metrics=metrics,selected_model=selected,selection_reason=selection_reason,upper_evidence=upper_evidence,backtest=[{'day':rows[start+j]['day'],'actual':values[start+j],'mark':marks[start+j],'scored':marks[start+j]=='normal',**{m:predictions[m][j] for m in predictions}} for j in range(backtest_days)],future=future,history=[{'day':r['day'],'volume':r['volume'],'mark':r['mark']} for r in rows],backtest_clipped=clipped,checksum=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),warning='按时间顺序滚动一步回测，每个预测只用此前数据；α/β为提交前指定，不用回测真值调参。触顶日记录量只是实际需求下界，仍作为可得历史参与训练，但不参与误差评分；两法只在相同正常日上比较MAE，MAPE跳过实际值0并报告数量，无正常日时MAE未定义并默认季节朴素。负预测先截为0，未来值四舍五入为非负整数。需求区间下界为模型预测，上界取近期正常日最大量，证据不足时上界为null（未知），连日触顶也至少给出下界排班参考。')
