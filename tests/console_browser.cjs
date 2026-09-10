// Browser-platform doubles exercise the shipped inline script, not a copied renderer.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../src/rightsrelay/console.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const elements = new Map();
const element = id => {
  if (!elements.has(id)) elements.set(id, {textContent:'', innerHTML:'', dataset:{},
    classList:{add(){},remove(){},toggle(){}},addEventListener(){},disabled:false});
  return elements.get(id);
};
const buttons = Array.from({length:6}, (_, i) => element(`button-${i}`));
const intervals = [];
let failed = false;
let now = Date.parse('2026-09-10T16:00:00Z');
const data = {utc:'2026-09-10T16:00:00Z',pid:100,git:'test',db_path:'/local/memory',
  entity_name:'campaign-aurora:neon-drive',entity_found:true,memory_available:true,
  status:'CLEARED',reasons:[],channels:['instagram'],paid:true,territories:['US','UK'],
  expires_on:'2026-10-31',acp_job_id:null,x402_tx:null,x402_explorer:null,
  acp_contract_explorer:'https://basescan.org/',journal:[],packet_written:true,
  packet_state:'current',packet_path:'/local/release-packets/packet.json',current_attempt:{paid:true}};
const context = vm.createContext({
  document:{getElementById:element,querySelectorAll:()=>buttons,
    querySelector:()=>({content:'offline-browser-fixture'})},
  window:{setInterval:fn=>{intervals.push(fn);return intervals.length;},
    setTimeout,clearTimeout},
  AbortController, Date:class extends Date {static now(){return now;}},
  fetch:async()=>{if(failed)throw new Error('offline');return {ok:true,json:async()=>data};},
});
(async()=>{
  vm.runInContext(script, context);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(element('gate-status').textContent,'CLEARED');
  failed=true;
  await context.poll();
  assert.equal(element('gate-status').textContent,'UNVERIFIED');
  assert.equal(element('packet-state').textContent,'packet: unverified');
  assert.equal(element('utc').textContent,'—');
  assert.ok(buttons.every(button=>button.disabled));
  now+=10000;
  for(const tick of intervals)tick();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(element('utc').textContent,'—','disconnected clock must not appear live');
  failed=false;
  await context.poll();
  assert.equal(element('gate-status').textContent,'CLEARED');
  assert.ok(buttons.every(button=>!button.disabled));
  // Even a hung fetch must lose the green display once the last observation ages out.
  context.fetch=()=>new Promise(()=>{});
  now+=10000;
  for(const tick of intervals)tick();
  assert.equal(element('gate-status').textContent,'UNVERIFIED');
  console.log('console disconnect, recovery and stale-observation checks passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
