const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const demo = require('./docs/linguistic-pilots/demo/scenarios.js');
const root = path.join(__dirname, 'docs/linguistic-pilots');
const pilot = JSON.parse(fs.readFileSync(path.join(root, 'semantic-pilot.json'), 'utf8'));
const proposals = JSON.parse(fs.readFileSync(path.join(root, 'editorial-decisions.json'), 'utf8'));
const sample = JSON.parse(fs.readFileSync(path.join(root, 'syllable-sample.json'), 'utf8'));
const byId = new Map(pilot.cases.map(c => [c.id, c]));

assert.equal(demo.scenarios.length, 10);
for (const scenario of demo.scenarios) {
  assert.ok(byId.has(scenario.caseId), scenario.caseId);
  assert.equal(scenario.productionApproved, false);
  assert.equal(scenario.initial.kind, scenario.choices.length ? 'clarification' : 'withheld');
  for (const choice of scenario.choices) {
    const reply = demo.reply(scenario.id, choice.id);
    assert.equal(reply, choice.reply);
    if (reply.kind === 'answer') {
      assert.equal(byId.get(reply.sourceCaseId).decision, 'retain_in_pilot');
      assert.equal(reply.relation, byId.get(reply.sourceCaseId).relation);
    }
  }
}
assert.equal(demo.reply('sem-06', 'garden').relation, 'hyponym');
assert.equal(demo.reply('sem-06', 'finance').kind, 'scope_exclusion');
assert.equal(demo.reply('sem-05', 'colour').kind, 'scope_exclusion');
assert.equal(demo.reply('sem-01', 'lucky').kind, 'withheld');
assert.equal(demo.reply('sem-07').kind, 'withheld');
assert.equal(demo.reply('sem-09').kind, 'withheld');
// Unknown context cannot silently select the first/retained answer.
assert.equal(demo.reply('sem-06', 'unrecognised-context').kind, 'unavailable');
assert.equal(demo.reply('unknown', 'garden').kind, 'unavailable');
assert.equal(demo.reply('sem-06').kind, 'clarification');
assert.equal(proposals.production_approved, false);
assert.equal(proposals.user_approved, false);
assert.equal(proposals.syllables.length, 28);
assert.equal(proposals.syllables.filter(c => c.eligible_for_phonological_reference).length, 10);
for (const item of proposals.syllables) {
  const original = sample.cases.find(c => c.id === item.case_id);
  assert.ok(original);
  assert.equal(item.word, original.word);
  assert.equal(item.profile, original.profile);
  assert.deepEqual(item.analyses, original.analyses);
  assert.equal(item.user_approved, false);
  assert.equal(item.production_approved, false);
  if (item.eligible_for_phonological_reference) {
    assert.ok(['explicit_syllabification', 'phonological_awareness'].includes(item.profile));
  }
}
for (const [name, digest] of Object.entries(proposals.basis_sha256)) {
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root, name))).digest('hex'), digest);
}
console.log('Editorial proposals and 10 fixed semantic scenarios checked');
