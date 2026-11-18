ROLES=('admin','analyst','viewer')
STATES=('queued','running','done','failed')
BRANCHES=('川北','川南','东河','西浦','新城','临港','山前','湖滨')
MODELS=('seasonal_naive','holt')
# 日结标记：normal=正常日量；capped=网点限流触顶，系统记录量仅为实际需求下界；unknown=旧日结无标记
MARKS=('normal','capped','unknown')
# 上界证据窗口：取预测原点之前最近若干个自然日中的正常日量作为上界证据
UPPER_EVIDENCE_DAYS=14
# 证据窗口内至少需要的正常日数量，不足则上界保留未知
UPPER_EVIDENCE_MIN_NORMAL=1
