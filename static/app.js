// static/app.js — wired to /history + /predict and Chart.js overlay

const symbolInput = document.getElementById('symbol');
const suggestBox = document.getElementById('suggestBox');
const predictBtn = document.getElementById('predictBtn');
const predictAllBtn = document.getElementById('predictAllBtn');
const status = document.getElementById('status');

const stockName = document.getElementById('stockName');
const recPill = document.getElementById('recPill');
const priceChange = document.getElementById('priceChange');
const confidence = document.getElementById('confidence');
const workingTickerEl = document.getElementById('workingTicker');
const predEls = [document.getElementById('d1'),document.getElementById('d2'),document.getElementById('d3'),document.getElementById('d4'),document.getElementById('d5')];
const resultCard = document.getElementById('resultCard');


// Autocomplete (uses STOCK_LIST from static/stocks.js)
function showSuggestions(q){
  if(!q){ suggestBox.style.display='none'; return; }
  const up = q.toUpperCase();
  const matches = (typeof STOCK_LIST !== 'undefined' ? STOCK_LIST : []).filter(s => s.startsWith(up)).slice(0,10);
  if(matches.length===0){ suggestBox.style.display='none'; return; }
  suggestBox.innerHTML = '';
  matches.forEach(m => {
    const div = document.createElement('div');
    div.textContent = m;
    div.onclick = ()=>{ symbolInput.value = m; suggestBox.style.display='none'; };
    suggestBox.appendChild(div);
  });
  suggestBox.style.display='block';
}
symbolInput.addEventListener('input', (e)=> showSuggestions(e.target.value));
symbolInput.addEventListener('focus', (e)=> showSuggestions(e.target.value));
document.addEventListener('click', (e)=> { if(!e.target.closest('.input-wrap')) suggestBox.style.display='none'; });

// Chart setup
const ctx = document.getElementById('priceChart').getContext('2d');
const priceChart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [], // dates
    datasets: [
      { label: 'Historical', data: [], borderColor: '#4da6ff', backgroundColor: 'rgba(77,166,255,0.06)', tension: 0.25, fill: true, pointRadius: 3 },
      // forecast will be plotted as red points (no line), aligned at the end of labels
      { label: 'Forecast (5d)', data: [], borderColor: '#ff6b6b', backgroundColor: 'rgba(255,107,107,0.06)', pointRadius: 6, showLine: false }
    ]
  },
  options: {
    responsive: true,
    plugins: {
      legend: { labels: { color: '#bfe7ff' } },
      tooltip: { mode: 'index', intersect: false }
    },
    scales: { x: { ticks: { color: '#9fc9ff' } }, y: { ticks: { color: '#9fc9ff' } } }
  }
});

function setStatus(txt, isError=false){
  status.textContent = txt;
  status.style.color = isError ? '#ffb4b4' : '#bcdff6';
}

// fetch history (last 1 year) then overlay prediction
async function loadAndPlot(symbol){
  setStatus('Loading history...');
  try{
    // fetch 1-year history
    const hres = await fetch(`/history?symbol=${encodeURIComponent(symbol)}`);
    if(!hres.ok){
      const err = await hres.json().catch(()=>({error:hres.statusText}));
      setStatus('History API Error: ' + (err.error || hres.statusText), true);
      return;
    }
    const hist = await hres.json();
    const dates = hist.dates || [];
    const prices = (hist.prices || []).map(p => Number(p));

    // set chart historical data
    priceChart.data.labels = dates.slice(); // array of ISO dates
    priceChart.data.datasets[0].data = prices.slice();
    // initialize forecast dataset as nulls appended (so axis scales remain correct)
    priceChart.data.datasets[1].data = new Array(dates.length).fill(null);
    priceChart.update();

    setStatus('History loaded — now fetching prediction...');

    // now call predict
    const pres = await fetch(`/predict?symbol=${encodeURIComponent(symbol)}`);
    if(!pres.ok){
      const err = await pres.json().catch(()=>({error:pres.statusText}));
      setStatus('Predict API Error: ' + (err.error || pres.statusText), true);
      return;
    }
    const pdata = await pres.json();

    // update UI panels
    resultCard.style.display = 'block';
    stockName.textContent = pdata.symbol || symbol.toUpperCase();
    recPill.textContent = pdata.recommendation || '—';
    priceChange.textContent = (pdata['pct_change_%'] > 0 ? '+' : '') + pdata['pct_change_%'] + '%';
    confidence.textContent = (pdata.confidence !== undefined ? pdata.confidence + '%' : '—');
    workingTickerEl.textContent = pdata.working_ticker || '—';

    // show 5 day predictions in cards
    const preds = (pdata.predicted_prices || []).map(x => Number(x));
    for(let i=0;i<5;i++){
      predEls[i].textContent = preds[i] ? '₹' + preds[i].toFixed(2) : '—';
    }

    // Compute next 5 dates after last date in history
    const lastDate = priceChart.data.labels.length ? new Date(priceChart.data.labels[priceChart.data.labels.length - 1]) : new Date();
    const nextDates = [];
    for(let i=1;i<=5;i++){
      const d = new Date(lastDate);
      d.setDate(d.getDate() + i);
      nextDates.push(d.toISOString().slice(0,10));
    }

    // Append the prediction labels to chart labels and update datasets:
    // Keep existing historical dataset; append nulls for dataset0 for the new forecast label slots,
    // and append actual pred numbers to dataset1 aligned with those new label slots.
    priceChart.data.labels = priceChart.data.labels.concat(nextDates);
    priceChart.data.datasets[0].data = priceChart.data.datasets[0].data.concat(new Array(nextDates.length).fill(null));
    // dataset[1] may be shorter/empty -> ensure it's same length then append preds
    const currentF = priceChart.data.datasets[1].data || [];
    // extend currentF to match existing label length minus preds length
    const neededPrepend = priceChart.data.labels.length - preds.length - currentF.length;
    if(neededPrepend > 0){
      priceChart.data.datasets[1].data = currentF.concat(new Array(neededPrepend).fill(null)).concat(preds);
    } else {
      priceChart.data.datasets[1].data = (currentF.concat(preds)).slice(0, priceChart.data.labels.length);
    }

    priceChart.update();
    setStatus('Prediction ready!');

  }catch(err){
    console.error(err);
    setStatus('Fetch error (see console)', true);
  }
}


predictBtn.addEventListener('click', ()=> {
  const s = symbolInput.value.trim();
  if(!s){ setStatus('Please enter a symbol', true); return; }
  loadAndPlot(s);
});
predictAllBtn.addEventListener('click', ()=> setStatus('Predict All not implemented in this demo'));
