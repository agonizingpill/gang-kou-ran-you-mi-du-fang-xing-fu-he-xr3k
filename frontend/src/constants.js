export const ROLES={admin:'调拨主管',chemist:'化验员',viewer:'船代观察员'};
export const SAMPLE_STATES={received:'待比对',queued:'比对中',qualified:'原样合格',anomaly:'异常待复检',retested:'复检合格',rejected:'复检未过',failed:'计算失败'};
export const AUDIT_ACTIONS={tank_registered:'储罐登记',tank_state:'储罐状态调整',sample_received:'油样收件',sample_compared:'密度分布比对',sample_retested:'化验复检',transfer_requested:'调拨申请',transfer_released:'主管调拨放行',permit_planned:'清线计划',line_registered:'管线登记',line_permitted:'清线许可',window_planned:'受油窗口计划',window_confirmed:'泊位窗口确认',berth_registered:'泊位登记',harbor_occupied:'放行占用资源',harbor_completed:'输油完工释放',retained_sealed:'燃油留样封存',retest_commissioned:'封样复检委托',retest_reported:'委托检验报告',retest_closed:'委托复检结案'};

export const RECEIPT_STATES={planned:'计划到港',inspected:'化验核对通过',received:'已入罐冻结'};
export const RECONCILIATION_STATES={matched:'容差内待签',variance:'超差待调查',closed:'主管已结案'};

export const BLIND_STATES={open:'开场受理中',sealed:'已封卷待揭榜',scoring:'计分中（可断点续算）',revealed:'已揭榜'};
export const BLIND_VERDICTS={normal:'人工：正常放行',anomaly:'人工：异常'};
export const BLIND_OUTCOMES={correct:'判定一致',hit:'命中异常',miss:'漏判（异常被放行）',false_alarm:'误报（正常被判异）',missing:'缺交（单列）',late:'补录（单列）',noscore:'不计分'};
export const BLIND_AUDIT={blind_session_opened:'盲测开场',blind_sample_sealed_in:'考样封存',blind_session_sealed:'收卷封卷',blind_reading_accepted:'盲码读数受理',blind_reading_late:'封卷后补录',blind_scoring_done:'盲测计分完成',blind_scoring_failed:'盲测计分中断',blind_session_revealed:'盲测揭榜'};
