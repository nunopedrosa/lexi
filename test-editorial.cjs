const assert=require('node:assert/strict');
const fs=require('node:fs');
const crypto=require('node:crypto');
const editorial=require('./editorial.js');
const approved=require('./docs/linguistic-pilots/regional-demo/scenarios.js');
const batch2=require('./docs/linguistic-pilots/regional-batch-2.json');
const batch30=require('./docs/linguistic-pilots/editorial-drafts-30.json');
const audit=require('./editorial-audit.json');
const words=['legal','apelido','propina','fato','camisola','rapariga'].concat(batch30.entries.map(e=>e.word));
assert.equal(words.length,36);
assert.equal(new Set(words).size,36);
assert.equal(audit.editorial_presentation_responses,36);
assert.deepEqual(audit.entries.map(e=>e.word).sort(),words.slice().sort());
for(const word of words){
 const newEntry=batch30.entries.find(e=>e.word===word);
 const proposal=batch2.cases.find(c=>c.word===word);
 const expected=newEntry?newEntry.draft_text:proposal?proposal.initial_text:approved.scenarios.find(s=>s.id==='regional-'+word).initial.text;
 assert.equal(editorial.get(word),expected);
 assert.equal(editorial.get(word.toUpperCase()),expected);
 const record=audit.entries.find(e=>e.word===word);
 const raw=fs.readFileSync(record.original_shard);
 const row=JSON.parse(raw).find(r=>r[0]===word);
 const before=JSON.stringify(row);
 const senses=editorial.sourceSenses(row,false);
 assert.deepEqual(senses.map(s=>s.text),row[2].map(s=>s[0]));
 assert.deepEqual(editorial.sourceSenses(row,true).map(s=>s.text),row[2].filter(s=>s[1]!=='curated').map(s=>(s[3]||{}).original||s[0]));
 assert.equal(JSON.stringify(row),before);
 assert.equal(record.text,expected);
 assert.equal(record.original_shard_sha256,crypto.createHash('sha256').update(raw).digest('hex'));
 assert.equal(record.original_senses,row[2].filter(s=>s[1]!=='curated').length);
 if(proposal){
  assert.equal(proposal.integration_approved,true);
  assert.deepEqual(row,proposal.source.row);
  assert.deepEqual(record.references,proposal.references);
 }
 if(newEntry){
  assert.equal(newEntry.integration_approved,true);
  assert.deepEqual(row,newEntry.source_snapshot.row);
  assert.deepEqual(record.references,newEntry.evidence_source_ids.map(id=>batch30.sources.find(s=>s.id===id)));
 }
}
assert.match(editorial.get('açougue'),/^No português do Brasil/);
assert.match(editorial.get('açougue'),/«talho»/);
assert.equal(editorial.get('ÔNIBUS'),editorial.get('ônibus'));
for(const word of ['casa','légal','constructor','__proto__','toString'])assert.equal(editorial.get(word),null);
const row=['test','n.',[
 ['editorial','curated',[]],
 ['adapted','unmarked',['automatic'],{original:'exact source'}],
 ['Brazilian original','BR',[]]
]];
const original=editorial.sourceSenses(row,true);
assert.deepEqual(original.map(s=>s.text),['exact source','Brazilian original']);
assert.deepEqual(original.map(s=>s.index),[2,3]);
original[0].flags.push('test-only');
assert.deepEqual(row[2][1][2],['automatic']);
console.log('36 approved PT-PT responses, all source senses, exact originals and provenance checked');
