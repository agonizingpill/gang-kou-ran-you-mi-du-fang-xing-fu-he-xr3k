ROLES=('admin','chemist','viewer')
SAMPLE_STATES=('received','queued','qualified','anomaly','retested','rejected','failed')
GRADES={'VLSFO':{'density_min':925,'density_max':1010,'viscosity_min':10,'viscosity_max':380,'sulfur_max':.5},'MGO':{'density_min':820,'density_max':890,'viscosity_min':1,'viscosity_max':12,'sulfur_max':.1}}

RECEIPT_STATES=('planned','inspected','received')
RECONCILIATION_STATES=('matched','variance','closed')

LINE_STATES=('idle','busy')
PERMIT_STATES=('planned','permitted','in_use','completed')
WINDOW_STATES=('planned','confirmed','in_use','completed')
RETEST_STATES=('commissioned','reported','closed')
