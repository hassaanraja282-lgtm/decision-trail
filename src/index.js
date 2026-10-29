const Resolver = require('@forge/resolver').default;
const api = require('@forge/api');
const { route } = api;
const { kvs, WhereConditions } = require('@forge/kvs');
const D = require('./decisions');

const PREFIX = 'd:';

async function allDecisions() {
  const out = [];
  let cursor;
  do {
    let q = kvs.query().where('key', WhereConditions.beginsWith(PREFIX)).limit(100);
    if (cursor) q = q.cursor(cursor);
    const page = await q.getMany();
    for (const r of page.results) out.push(r.value);
    cursor = page.nextCursor;
  } while (cursor && out.length < 2000);
  return out;
}

async function saveDecision(d) {
  await kvs.set(PREFIX + d.id, d);
  return d;
}

async function issueSummary(issueKey) {
  try {
    const res = await api.asApp().requestJira(route`/rest/api/3/issue/${issueKey}?fields=summary,description`);
    if (!res.ok) return '';
    const j = await res.json();
    return `${j.fields.summary || ''} ${D.adfToText(j.fields.description).slice(0, 1000)}`;
  } catch (e) {
    return '';
  }
}

async function userName(accountId) {
  if (!accountId) return null;
  try {
    const res = await api.asApp().requestJira(route`/rest/api/3/user?accountId=${accountId}`);
    if (!res.ok) return null;
    return (await res.json()).displayName || null;
  } catch (e) {
    return null;
  }
}

async function panelData(issueKey) {
  const all = await allDecisions();
  const mine = all
    .filter((d) => d.issueKey === issueKey)
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const context = (await issueSummary(issueKey)) + ' ' + mine.map((d) => d.text).join(' ');
  const related = D.search(all, context, { excludeIssue: issueKey, limit: 5 });
  const conflicts = [];
  for (const m of mine.filter((d) => !d.superseded)) {
    for (const r of related) if (D.looksConflicting(m, r)) conflicts.push({ mine: m.id, other: r.id, otherIssue: r.issueKey });
  }
  return { issueKey, mine, related, conflicts, total: all.length };
}

const resolver = new Resolver();

resolver.define('getPanel', async ({ context }) => {
  const issueKey = context.extension.issue.key;
  return panelData(issueKey);
});

resolver.define('logDecision', async ({ payload, context }) => {
  const issueKey = context.extension.issue.key;
  const text = String(payload.text || '').trim();
  if (text.length < 3) return { error: 'Write the decision in a few words.' };
  const accountId = context.accountId;
  await saveDecision(
    D.makeDecision({ issueKey, text, author: accountId, authorName: await userName(accountId), source: 'panel' })
  );
  return panelData(issueKey);
});

resolver.define('supersede', async ({ payload, context }) => {
  const issueKey = context.extension.issue.key;
  const d = await kvs.get(PREFIX + payload.id);
  if (d && d.issueKey === issueKey) {
    d.superseded = !d.superseded;
    d.supersededAt = d.superseded ? new Date().toISOString() : null;
    await kvs.set(PREFIX + d.id, d);
  }
  return panelData(issueKey);
});

exports.handler = resolver.getDefinitions();

// Trigger: a Jira comment that starts with "DECISION:" is captured automatically.
exports.onComment = async (event) => {
  try {
    const issueKey = event.issue && (event.issue.key || event.issue.id);
    const commentId = event.comment && event.comment.id;
    let body = event.comment && event.comment.body;
    if (!body && issueKey && commentId) {
      const res = await api.asApp().requestJira(route`/rest/api/3/issue/${issueKey}/comment/${commentId}`);
      if (res.ok) body = (await res.json()).body;
    }
    const text = D.parseDecision(D.adfToText(body));
    if (!text) return;
    let key = event.issue.key;
    if (!key) {
      const r = await api.asApp().requestJira(route`/rest/api/3/issue/${issueKey}?fields=summary`);
      key = (await r.json()).key;
    }
    const accountId = (event.comment.author && event.comment.author.accountId) || event.atlassianId;
    await saveDecision(
      D.makeDecision({ issueKey: key, text, author: accountId, authorName: await userName(accountId), source: 'comment' })
    );
  } catch (e) {
    console.error('decision capture failed', e);
  }
};

// Trigger: when an issue is deleted, its decisions go with it.
exports.onIssueDeleted = async (event) => {
  try {
    const key = event.issue && event.issue.key;
    if (!key) return;
    for (const d of await allDecisions()) if (d.issueKey === key) await kvs.delete(PREFIX + d.id);
  } catch (e) {
    console.error('cleanup failed', e);
  }
};

// Rovo actions
exports.findDecisionsAction = async (payload) => {
  const all = await allDecisions();
  const hits = D.search(all, payload.query || '', { limit: 8, minScore: 1 });
  if (!hits.length) return { found: 0, message: `No logged decisions match "${payload.query}".` };
  return {
    found: hits.length,
    decisions: hits.map((d) => ({
      issueKey: d.issueKey,
      decision: d.text,
      by: d.authorName || 'unknown',
      date: d.createdAt.slice(0, 10),
    })),
  };
};

exports.logDecisionAction = async (payload, context) => {
  const issueKey = String(payload.issueKey || '').toUpperCase();
  const text = String(payload.text || '').trim();
  if (!/^[A-Z][A-Z0-9_]+-\d+$/.test(issueKey) || text.length < 3) {
    return { stored: false, message: 'Need a valid issue key like KAN-12 and the decision text.' };
  }
  const accountId = context && context.principal && context.principal.accountId;
  const d = await saveDecision(
    D.makeDecision({ issueKey, text, author: accountId, authorName: await userName(accountId), source: 'rovo' })
  );
  return { stored: true, issueKey: d.issueKey, decision: d.text, date: d.createdAt.slice(0, 10) };
};
