const test = require('node:test');
const assert = require('node:assert');
const D = require('../src/decisions');

test('parses DECISION: prefix in plain text', () => {
  assert.strictEqual(D.parseDecision('DECISION: use Postgres for billing'), 'use Postgres for billing');
  assert.strictEqual(D.parseDecision('Decided - ship on Friday'), 'ship on Friday');
  assert.strictEqual(D.parseDecision('just a normal comment'), null);
});

test('finds decision on a later line', () => {
  assert.strictEqual(D.parseDecision('Talked with Sam.\nAgreed: drop IE11 support'), 'drop IE11 support');
});

test('flattens ADF', () => {
  const adf = {
    type: 'doc',
    content: [{ type: 'paragraph', content: [{ type: 'text', text: 'DECISION: ' }, { type: 'text', text: 'OAuth via Okta' }] }],
  };
  assert.strictEqual(D.parseDecision(D.adfToText(adf)), 'OAuth via Okta');
});

test('keywords drop stopwords and dupes', () => {
  assert.deepStrictEqual(D.keywords('We will use the Postgres database, Postgres!'), ['postgres', 'database']);
});

test('search ranks related decisions and skips superseded/excluded', () => {
  const a = D.makeDecision({ issueKey: 'KAN-1', text: 'Use Postgres for the billing database' });
  const b = D.makeDecision({ issueKey: 'KAN-2', text: 'Frontend uses React and Vite' });
  const c = D.makeDecision({ issueKey: 'KAN-3', text: 'Billing database backups nightly' });
  c.superseded = true;
  const hits = D.search([a, b, c], 'which database for billing?');
  assert.deepStrictEqual(hits.map((h) => h.issueKey), ['KAN-1']);
  assert.strictEqual(D.search([a], 'billing database', { excludeIssue: 'KAN-1' }).length, 0);
});

test('flags opposite decisions on the same topic', () => {
  const a = D.makeDecision({ issueKey: 'KAN-1', text: 'Use Mongo for billing database' });
  const b = D.makeDecision({ issueKey: 'KAN-2', text: 'Do not use Mongo for billing database' });
  const c = D.makeDecision({ issueKey: 'KAN-3', text: 'Mobile app ships in March' });
  assert.ok(D.looksConflicting(a, b));
  assert.ok(!D.looksConflicting(a, c));
});

test('makeDecision normalizes fields', () => {
  const d = D.makeDecision({ issueKey: 'kan-9', text: '  Ship it  ' });
  assert.strictEqual(d.issueKey, 'KAN-9');
  assert.strictEqual(d.text, 'Ship it');
  assert.strictEqual(d.superseded, false);
});

test('does not flag agreeing decisions that merely contain a negation', () => {
  const a = D.makeDecision({ issueKey: 'PAY-2', text: 'Use Okta SSO for all internal dashboards. No custom password auth.' });
  const b = D.makeDecision({ issueKey: 'PAY-6', text: 'Merchant portal SSO goes through Okta, same as internal tools.' });
  assert.ok(!D.looksConflicting(a, b));
});

test('flags adopting something an earlier decision ruled out', () => {
  const a = D.makeDecision({ issueKey: 'PAY-1', text: 'Use Postgres for the billing database, not Mongo.' });
  const b = D.makeDecision({ issueKey: 'PAY-5', text: 'Use Mongo for the billing refund database' });
  assert.ok(D.looksConflicting(a, b));
  assert.deepStrictEqual([...D.negatedTerms('not Mongo')], ['mongo']);
});
