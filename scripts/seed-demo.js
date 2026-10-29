// Seeds a demo Jira project. Usage: FORGE_EMAIL=.. FORGE_API_TOKEN=.. SITE=x.atlassian.net node scripts/seed-demo.js
const SITE = process.env.SITE;
const AUTH = 'Basic ' + Buffer.from(`${process.env.FORGE_EMAIL}:${process.env.FORGE_API_TOKEN}`).toString('base64');
const KEY = 'PAY';

async function j(method, path, body) {
  const res = await fetch(`https://${SITE}${path}`, {
    method,
    headers: { Authorization: AUTH, Accept: 'application/json', 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${method} ${path} -> ${res.status} ${text.slice(0, 400)}`);
  return text ? JSON.parse(text) : {};
}
const adf = (t) => ({ type: 'doc', version: 1, content: [{ type: 'paragraph', content: [{ type: 'text', text: t }] }] });

const ISSUES = [
  ['Choose primary database for billing service', 'We need a datastore for invoices, payments and refunds in the billing service.',
    'DECISION: Use Postgres for the billing database, not Mongo. Invoices need transactions and strong consistency.'],
  ['Pick authentication provider for internal tools', 'Dashboards and admin tools need single sign-on.',
    'DECISION: Use Okta SSO for all internal dashboards. No custom password auth.'],
  ['Public API versioning strategy', 'How do we version the public payments REST API?',
    'Agreed: version the public REST API in the URL path (/v1, /v2), not in request headers.'],
  ['Frontend framework for merchant portal', 'Pick the stack for the new merchant portal.',
    'DECISION: Build the merchant portal in React with Vite and TypeScript.'],
  ['Store refund ledger for billing in MongoDB', 'Proposal: keep the refund ledger for the billing service in MongoDB collections so we can iterate on the schema quickly.', null],
  ['Add SSO login to the merchant portal', 'Merchants want single sign-on into the React merchant portal.', null],
];

(async () => {
  const me = await j('GET', '/rest/api/3/myself');
  console.log('as', me.displayName);
  const projects = await j('GET', '/rest/api/3/project/search?maxResults=50');
  console.log('projects:', projects.values.map((p) => p.key).join(', ') || '(none)');
  if (!projects.values.find((p) => p.key === KEY)) {
    await j('POST', '/rest/api/3/project', {
      key: KEY, name: 'Payments Platform', projectTypeKey: 'software',
      projectTemplateKey: 'com.pyxis.greenhopper.jira:gh-simplified-kanban-classic',
      leadAccountId: me.accountId, assigneeType: 'UNASSIGNED',
    });
    console.log('created project', KEY);
  }
  const existing = await j('POST', '/rest/api/3/search/jql', { jql: `project = ${KEY} ORDER BY key ASC`, fields: ['summary'], maxResults: 50 });
  const have = new Set(existing.issues.map((i) => i.fields.summary));
  for (const [summary, desc, comment] of ISSUES) {
    if (have.has(summary)) { console.log('exists:', summary); continue; }
    const issue = await j('POST', '/rest/api/3/issue', {
      fields: { project: { key: KEY }, summary, description: adf(desc), issuetype: { name: 'Task' } },
    });
    console.log('created', issue.key, summary);
    if (comment) {
      await j('POST', `/rest/api/3/issue/${issue.key}/comment`, { body: adf(comment) });
      console.log('  commented decision');
    }
  }
  const all = await j('POST', '/rest/api/3/search/jql', { jql: `project = ${KEY} ORDER BY key ASC`, fields: ['summary'], maxResults: 50 });
  for (const i of all.issues) console.log(i.key, '|', i.fields.summary);
})().catch((e) => { console.error(e.message); process.exit(1); });
