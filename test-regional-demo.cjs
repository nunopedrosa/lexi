const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const demo=require('./docs/linguistic-pilots/regional-demo/scenarios.js');
const audit=JSON.parse(fs.readFileSync(path.join(__dirname,'docs/linguistic-pilots/regional-review.json'),'utf8'));
assert.equal(demo.scenarios.length,3);
assert.equal(demo.initialScenarioId,'regional-legal');
for(const scenario of demo.scenarios){
 assert.equal(scenario.productionApproved,false);
 assert.equal(scenario.initial.kind,'pt_pt_priority');
 assert.doesNotMatch(scenario.initial.text,/Brasil|brasileir|suborno|alcunha|giro|fixe/i);
 for(const choice of scenario.choices){
  const reply=demo.reply(scenario.id,choice.id);
  if(reply.kind==='regional_explanation'){
   assert.equal(choice.explicitBrazilContext,true);
   assert.match(reply.text,/Brasil|brasileir/i);
  }
 }
 assert.equal(demo.reply(scenario.id,'unrecognised-context').kind,'withheld');
}
assert.match(demo.reply('regional-legal').text,/lei/);
assert.match(demo.reply('regional-apelido').text,/família/);
assert.match(demo.reply('regional-propina').text,/ensino superior/);
assert.equal(demo.reply('regional-apelido','nickname').region,'not_established');
assert.doesNotMatch(demo.reply('regional-apelido','nickname').text,/só no Brasil|exclusivamente.*Brasil/i);
assert.match(demo.reply('regional-propina','br_bribe').text,/suborno/);
assert.equal(demo.reply('unknown').kind,'withheld');
assert.equal(audit.production_approved,false);
for(const entry of audit.cases){
 const raw=fs.readFileSync(path.join(__dirname,entry.source.path));
 const row=JSON.parse(raw).find(r=>r[0]===entry.word);
 assert.equal(crypto.createHash('sha256').update(raw).digest('hex'),entry.source.shard_sha256);
 assert.deepEqual(row,entry.source.row);
 assert.ok(entry.references.some(r=>r.kind==='portuguese_institutional_usage'));
 assert.equal(entry.production_approved,false);
}
console.log('3 regional cases: PT-PT priority, contextual variants and source preservation checked');
