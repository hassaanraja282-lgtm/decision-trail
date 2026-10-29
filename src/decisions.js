// Pure helpers: no Forge imports, so they are unit-testable with node --test.

const STOP = new Set(
  'a an the and or but if then so of to in on at for from by with as is are was were be been being it its this that these those we our us you your they them their i me my will would should could can may might must do does did done not no yes use using used have has had into over under about than also just only very more most less least all any each every some such per via vs'.split(
    ' '
  )
);

const DECISION_RE = /^\s*(?:\*\*)?\s*(decision|decided|we decided|agreed)\s*[:\-–]\s*/i;

/** Flatten Atlassian Document Format (or a plain string) into text. */
function adfToText(node) {
  if (node == null) return '';
  if (typeof node === 'string') return node;
  if (Array.isArray(node)) return node.map(adfToText).join('');
  let out = '';
  if (node.type === 'text' && typeof node.text === 'string') out += node.text;
  if (node.type === 'hardBreak') out += '\n';
  if (Array.isArray(node.content)) {
    out += node.content.map(adfToText).join('');
    if (['paragraph', 'heading', 'listItem', 'blockquote'].includes(node.type)) out += '\n';
  }
  return out;
}

/** Return the decision text if a comment is a decision, else null. Checks every line. */
function parseDecision(text) {
  if (!text) return null;
  for (const line of String(text).split(/\r?\n/)) {
    if (DECISION_RE.test(line)) {
      const body = line.replace(DECISION_RE, '').trim();
      if (body.length >= 3) return body.slice(0, 500);
    }
  }
  return null;
}

function keywords(text) {
  const words = String(text || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s\-_.]/g, ' ')
    .split(/\s+/)
    .map((w) => w.replace(/^[\-_.]+|[\-_.]+$/g, ''))
    .filter((w) => w.length > 2 && !STOP.has(w));
  return [...new Set(words)];
}

/** Score a decision against a query's keywords (0 = unrelated). */
function score(decision, queryWords) {
  if (!queryWords.length) return 0;
  const dw = new Set(decision.keywords || keywords(decision.text));
  let s = 0;
  for (const q of queryWords) {
    if (dw.has(q)) s += 2;
    else if ([...dw].some((w) => w.startsWith(q) || q.startsWith(w))) s += 1;
  }
  return s;
}

function search(decisions, query, { limit = 10, excludeIssue = null, minScore = 2 } = {}) {
  const q = keywords(query);
  return decisions
    .filter((d) => !d.superseded && d.issueKey !== excludeIssue)
    .map((d) => ({ ...d, score: score(d, q) }))
    .filter((d) => d.score >= minScore)
    .sort((a, b) => b.score - a.score || b.createdAt.localeCompare(a.createdAt))
    .slice(0, limit);
}

const NEG = /\b(not|no|never|instead|avoid|drop|stop|deprecate|remove|don't|won't)\b/i;

/** Two decisions on overlapping topics where exactly one is phrased negatively look like a conflict. */
function looksConflicting(a, b) {
  const shared = (a.keywords || keywords(a.text)).filter((w) => (b.keywords || keywords(b.text)).includes(w));
  if (shared.length < 2) return false;
  return NEG.test(a.text) !== NEG.test(b.text);
}

function makeDecision({ issueKey, text, author, authorName, source }) {
  const createdAt = new Date().toISOString();
  const id = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`;
  return {
    id,
    issueKey: String(issueKey || '').toUpperCase(),
    text: String(text).trim().slice(0, 500),
    author: author || null,
    authorName: authorName || null,
    source: source || 'panel',
    createdAt,
    superseded: false,
    keywords: keywords(text),
  };
}

module.exports = { adfToText, parseDecision, keywords, score, search, looksConflicting, makeDecision };
