import{heading}from'../components/logbook.js';import{esc,formData,localTime}from'../utils/format.js';import{api}from'../utils/api.js';import{BLIND_STATES,BLIND_VERDICTS,BLIND_OUTCOMES}from'../constants.js';
const pct=x=>x==null?'—':(x*100).toFixed(1)+'%';
const outcomeTag=o=>`<span class="tag blind-outcome ${esc(o)}">${BLIND_OUTCOMES[o]||esc(o)}</span>`;
export function render(s,u){
  const list=s.blindSessions||[];
  const cur=list.find(x=>x.id===s.blindSelected)||list[0]||null;
  return heading('10','密度比对盲测：让KDE先交卷。','主管封存人工判定与参考范围，化验员凭盲码录读数；揭榜前任何人看不到判定与分数，按等级分别统计漏判与误报。')
  +`<div class="supply-layout"><aside>
      <h2>盲测场次</h2>
      <div class="receipt-index">${list.map(x=>`<button class="receipt-pick ${cur&&cur.id===x.id?'picked':''}" data-session="${x.id}"><b>${esc(x.code)}</b><small>${BLIND_STATES[x.state]||esc(x.state)} · ${x.samples.length}个考样</small></button>`).join('')||'<p class="note">暂无场次。</p>'}</div>
      ${u.role==='admin'?`
      <h2>主管开场</h2>
      <form id="blind-session-create">
        <label>场次编号<input name="code" minlength="2" maxlength="60" placeholder="BLIND-2026B" required></label>
        <label>场次名称<input name="title" minlength="4" maxlength="200" placeholder="2026冬季密度比对盲测" required></label>
        <button class="copper">开场（日常化验照常进行）</button>
      </form>
      ${cur&&cur.state==='open'?`
      <h2>封存考样（揭榜前不可见）</h2>
      <form id="blind-sample-create" data-session="${cur.id}">
        <label>盲码<input name="blind_code" minlength="2" maxlength="40" placeholder="BC-A07" required></label>
        <label>油级<select name="grade"><option>VLSFO</option><option>MGO</option></select></label>
        <label>15℃密度 kg/m³（人工参考样范围）<input name="density_15" type="number" min="700" max="1100" step=".001" required></label>
        <label>人工判定<select name="human_verdict"><option value="normal">正常放行</option><option value="anomaly">异常</option></select></label>
        <label>判定依据<textarea name="human_basis" maxlength="600" placeholder="封存字段，揭榜后展示"></textarea></label>
        <button>封存该考样</button>
      </form>`:''}`:''}
      ${cur&&cur.state!=='revealed'?`
      <h2>化验员盲码读数</h2>
      <form id="blind-reading" data-session="${cur.id}">
        <label>盲码（来自纸质盲码单）<input name="blind_code" minlength="2" maxlength="40" required></label>
        <label>测得15℃密度 kg/m³<input name="density_read" type="number" min="700" max="1100" step=".001" required></label>
        <button ${u.role==='viewer'||cur.state==='revealed'?'disabled':''}>提交读数</button>
        <p class="tiny">收卷前受理计入成绩；封卷后提交自动标记补录，单列不计分。同一盲码重复提交覆盖并累计次数。</p>
      </form>`:''}
    </aside>
    <section>${cur?sessionSheet(cur,u):'<div class="sheet"><p class="note">左侧开场后，这里显示盲测进度。</p></div>'}</section>
  </div>`;
}
function sessionSheet(x,u){
  const revealed=x.state==='revealed';
  const snap=x.reference_snapshot;
  return `<div class="sheet">
    <div class="transfer-head"><h2>${esc(x.code)} · ${esc(x.title)}</h2><span class="tag blind-state ${esc(x.state)}">${BLIND_STATES[x.state]||esc(x.state)}</span></div>
    <p class="tiny">封卷 ${x.sealed_at?localTime(x.sealed_at):'—'} · ${esc(x.sealed_by||'')}　|　揭榜 ${x.revealed_at?localTime(x.revealed_at):'—'} · ${esc(x.revealed_by||'')}</p>
    ${snap?`<p class="tiny">封卷参考样：${Object.entries(snap).map(([g,v])=>`${g} ${v.reference_count}条`).join('；')}（编号与密度范围已封存，仅按级KDE拟合，考样不入模）</p>`:''}
    ${x.score_error?`<div class="variance-proof"><strong>计分中断：${esc(x.score_error)}</strong><p>成绩已保留到断点，重试只补未出分考样，不会重复出成绩。</p></div>`:''}
    ${u.role==='admin'?`<div class="actions">
      ${x.state==='open'?`<form id="blind-seal" data-session="${x.id}" class="inline"><button class="copper">收卷封卷（冻结人工判定与参考范围）</button></form>`:''}
      ${x.state==='sealed'?`<form id="blind-score" data-session="${x.id}" class="inline"><button class="copper">计分 / 断点续算</button></form>`:''}
      ${x.state==='scoring'?`<form id="blind-score" data-session="${x.id}" class="inline"><button>重试续算</button></form>`:''}
      ${x.state==='sealed'?`<form id="blind-reveal" data-session="${x.id}" class="inline"><button>揭榜公布成绩</button></form>`:''}
    </div>`:`<p class="tiny">${revealed?'成绩已揭榜，全员可查。':'等待主管操作，当前仅可凭盲码录读数。'}</p>`}
  </div>
  ${revealed&&x.summary_snapshot?summary(x.summary_snapshot):''}
  <div class="sheet"><h2>${revealed?'揭榜成绩册':'盲码读数台账（封存内容隐藏中）'}</h2>
  <table class="journal blind-table"><thead><tr><th>盲码</th><th>油级</th><th>化验员读数</th>${revealed?'<th>考样密度</th><th>人工判定</th><th>KDE判定</th><th>对数分/阈值</th><th>结论</th>':'<th>受理状态</th>'}</tr></thead><tbody>
  ${x.samples.map(z=>row(z,revealed)).join('')}
  </tbody></table>
  ${!revealed?'<p class="note">🔒 人工判定、考样密度与成绩已封存；本页只显示盲码、油级和你提交的读数，揭榜前无分数。</p>':''}
  </div>`;
}
function row(z,revealed){
  const r=z.reading;
  const reading=r?`<b>${r.density_read}</b><small>${esc(r.chemist)} · ${localTime(r.accepted_at)} · 第${r.attempts}次${r.late?' · <em class="late-flag">补录</em>':''}</small>`:'<span class="note">缺交</span>';
  if(!revealed)return `<tr><td>${esc(z.blind_code)}</td><td>${esc(z.grade)}</td><td>${reading}</td><td>${r?(r.late?'<span class="tag blind-outcome late">补录单列</span>':'<span class="tag blind-state sealed">已受理</span>'):'<span class="tag blind-outcome missing">缺交单列</span>'}</td></tr>`;
  const sc=z.score;
  return `<tr><td>${esc(z.blind_code)}</td><td>${esc(z.grade)}</td><td>${reading}</td>
    <td>${z.density_15}</td>
    <td>${BLIND_VERDICTS[z.human_verdict]||esc(z.human_verdict)}<small>${esc(z.human_basis||'')}</small></td>
    <td>${sc&&sc.algo_verdict?(sc.algo_verdict==='anomaly'?'<span class="tag anomaly">判异</span>':'<span class="tag qualified">放行</span>'):'—'}</td>
    <td>${sc&&sc.kde_score!=null?`${sc.kde_score.toFixed(3)} / ${sc.kde_threshold.toFixed(3)}`:'—'}</td>
    <td>${sc?outcomeTag(sc.outcome):'—'}</td></tr>`;
}
function summary(sm){
  const card=(t,b)=>`<div class="blind-stat"><span>${t}</span><b>${b}</b></div>`;
  const gradeBlock=g=>{const b=sm.by_grade[g];return `<div class="sheet"><h2>${g} 等级</h2><div class="blind-grid">
    ${card('漏判率（漏判/人工异常）',pct(b.miss_rate))}${card('误报率（误报/人工正常）',pct(b.false_alarm_rate))}
    ${card('漏判数',b.miss)}${card('误报数',b.false_alarm)}${card('判定一致',b.correct)}
    ${card('缺交单列',b.missing)}${card('补录单列',b.late)}${card('计分样本',b.scored+'/'+b.total)}</div></div>`};
  return `<div class="sheet"><h2>全场汇总 · ${esc(sm.note)}</h2><div class="blind-grid">
    ${card('漏判率',pct(sm.overall.miss_rate))}${card('误报率',pct(sm.overall.false_alarm_rate))}
    ${card('人工异常样',sm.overall.human_anomaly)}${card('人工正常样',sm.overall.human_normal)}
    ${card('被KDE放行的异常',sm.overall.algo_pass_on_anomaly)}${card('被KDE判异的正常',sm.overall.algo_flag_on_normal)}
    ${card('缺交',sm.overall.missing)}${card('补录',sm.overall.late)}</div></div>
    ${Object.keys(sm.by_grade).map(gradeBlock).join('')}`;
}
export function bind(refresh,render,s){
  document.querySelectorAll('button.receipt-pick[data-session]').forEach(b=>b.onclick=()=>{s.blindSelected=+b.dataset.session;render()});
  const post=(form,path,msg,after)=>{if(!form)return;form.onsubmit=e=>{e.preventDefault();let d=formData(form);for(let k of['density_15','density_read'])if(k in d)d[k]=+d[k];refresh(async()=>{let x=await api(path,'POST',d);if(after)await after(x)},msg)}};
  post(document.getElementById('blind-session-create'),'/blind/sessions','盲测已开场',async x=>{s.blindSelected=x.id});
  const f2=document.getElementById('blind-sample-create');
  post(f2,`/blind/sessions/${f2?f2.dataset.session:''}/samples`,'考样已封存，字段封存至揭榜');
  const f3=document.getElementById('blind-reading');
  post(f3,`/blind/sessions/${f3?f3.dataset.session:''}/readings`,'读数已受理');
  for(let[id,part,msg]of[['blind-seal','seal','已封卷：人工判定与参考范围冻结'],['blind-score','score','计分完成（中断会从断点续算）'],['blind-reveal','reveal','已揭榜，漏判与误报成绩公布']]){
    let f=document.getElementById(id);if(f)f.onsubmit=e=>{e.preventDefault();refresh(()=>api(`/blind/sessions/${f.dataset.session}/${part}`,'POST'),msg)};
  }
}
