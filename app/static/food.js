let streaming = true;
const byId = id => document.getElementById(id);
const fmtKg = n => `${n.toFixed(1)} kg`;
function inventoryRow(item) { const cls = item.status === 'Critical' ? 'critical' : item.status === 'Use soon' ? 'soon' : 'safe'; return `<div class="inventory-row"><div><strong>${item.food}</strong><small>${item.category} · ${item.kg} kg</small></div><div class="risk ${cls}">${item.status}<small>${item.risk_score}/100 risk</small></div><div><small>${item.age_days}/${item.fridge_days} fridge days · ${item.temperature_c}°C</small></div><div><div class="bar"><b class="${cls === 'critical' ? 'bad' : cls === 'soon' ? 'warn' : ''}" style="width:${item.risk_score}%"></b></div><small>${item.action}</small></div></div>`; }
function render(data) {
  const {metrics:m, prediction:p, weather:w, calendar:c} = data;
  byId('prepare').textContent = p.recommended_prepare;
  byId('predictionReason').textContent = `${p.confidence}% confidence · ${p.reason}`;
  byId('context').textContent = `${c.day} · ${c.event} · ${w.condition}, ${w.temperature_c}°C · rain probability ${w.rain_probability}% (${w.source})`;
  byId('inventoryKg').textContent = fmtKg(m.inventory_kg); byId('riskKg').textContent = fmtKg(m.at_risk_kg); byId('wasteKg').textContent = fmtKg(m.weekly_waste_kg); byId('reduction').textContent = `${m.waste_reduction_pct}%`;
  byId('inventoryRows').innerHTML = data.inventory.map(inventoryRow).join('');
  byId('agents').innerHTML = data.agents.map(a => `<div class="agent"><strong>${a.agent}</strong><p>${a.finding}</p><p><em>Next action:</em> ${a.action}</p></div>`).join('');
  byId('events').innerHTML = data.events.map(e => `<div class="event"><time>${e.time}</time><span class="${e.level}">${e.agent}</span><div>${e.message}</div></div>`).join('');
  byId('eventCount').textContent = `${data.events.length} events`; byId('source').textContent = data.data_source;
  streaming = data.streaming; byId('status').textContent = streaming ? 'STREAMING' : 'PAUSED'; byId('streamButton').textContent = streaming ? 'Pause stream' : 'Resume stream';
}
async function load(url='/api/dashboard', options) { try { const res = await fetch(url, options); if (!res.ok) throw new Error(); render(await res.json()); } catch { byId('context').textContent = 'Could not reach the local API. Start the app with run.ps1.'; } }
byId('streamButton').onclick = () => load('/api/stream', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:!streaming})});
byId('weatherButton').onclick = () => load('/api/weather/refresh', {method:'POST'});
load(); setInterval(() => load(), 3000);
