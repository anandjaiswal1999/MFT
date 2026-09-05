const $ = id => document.getElementById(id);
const money = new Intl.NumberFormat('en-IN', {style:'currency', currency:'INR', maximumFractionDigits:0});

for (const [id,label,suffix] of [['cash','cashLabel','money'],['vol','volLabel','%'],['dd','ddLabel','%']]) {
  $(id).addEventListener('input', () => $(label).textContent = suffix === 'money' ? money.format($(id).value) : $(id).value + suffix);
}

function draw(curve) {
  const svg=$('chart'), w=900, h=330, p=8, vals=curve.map(x=>x.value);
  const min=Math.min(...vals), max=Math.max(...vals), span=max-min||1;
  const points=curve.map((x,i)=>`${p+i/(curve.length-1)*(w-2*p)},${h-p-(x.value-min)/span*(h-2*p)}`).join(' ');
  svg.querySelector('.line').setAttribute('d', `M${points.replaceAll(' ',' L')}`);
  svg.querySelector('.area').setAttribute('d', `M${p},${h} L${points.replaceAll(' ',' L')} L${w-p},${h} Z`);
  svg.querySelector('.area').setAttribute('fill','#5cf2aa');
  let grid=''; for(let i=0;i<5;i++) grid+=`<line x1="0" y1="${i*h/4}" x2="${w}" y2="${i*h/4}"/>`;
  svg.querySelector('.grid').innerHTML=grid; $('empty').style.display='none';
}

function showDecision(data) {
  $('decision').classList.remove('hidden');
  $('verdict').textContent = data.qualified ? 'Qualified for paper testing' : 'Not ready for paper testing';
  $('verdict').className = data.qualified ? 'positive' : 'negative';
  $('verdictCopy').textContent = data.qualified ? 'The strategy passed every check on data it did not use for initial evaluation.' : 'Do not use real money. Improve the strategy, then run the workflow again.';
  $('validationReturn').textContent = data.validation.returnPct.toFixed(2)+'%';
  $('benchmark').textContent = data.validation.benchmarkPct.toFixed(2)+'%';
  $('validationHours').textContent = data.validation.hours;
  $('checks').innerHTML = data.checks.map(c=>`<div class="check ${c.passed?'pass':'fail'}">${c.passed?'✓':'×'} ${c.label}</div>`).join('');
  document.querySelectorAll('.workflow span').forEach((step,i)=>step.classList.toggle('active', i <= (data.qualified ? 3 : 2)));
}

$('run').addEventListener('click', async () => {
  const button=$('run'); button.disabled=true; button.textContent='Running workflow…'; $('status').textContent='Fetching data and validating strategy';
  try {
    const response=await fetch('/api/backtest',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({market:'india',symbol:$('symbol').value,cash:+$('cash').value,fast:+$('fast').value,slow:+$('slow').value,volTarget:+$('vol').value,maxDrawdown:+$('dd').value,bars:+$('bars').value})});
    const data=await response.json(); if(!response.ok) throw Error(data.error); const s=data.summary;
    $('equity').textContent=money.format(s.endingEquity); $('returns').textContent=s.returnPct.toFixed(2)+'%';
    $('returns').className=s.returnPct>=0?'positive':'negative'; $('drawdown').textContent=s.maxDrawdownPct.toFixed(2)+'%';
    $('sharpe').textContent=s.sharpe.toFixed(2); $('trades').textContent=s.trades+' trades · '+data.symbol+' · '+data.hoursTested+' market hours';
    draw(data.curve); showDecision(data); $('status').textContent='Workflow complete';
  } catch(e) { $('status').textContent='Error: '+e.message; }
  finally { button.disabled=false; button.innerHTML='Run workflow <span>→</span>'; }
});
