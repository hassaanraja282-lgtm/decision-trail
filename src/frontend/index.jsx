import React, { useEffect, useState } from 'react';
import ForgeReconciler, {
  Box,
  Button,
  Heading,
  Inline,
  Lozenge,
  SectionMessage,
  Spinner,
  Stack,
  Text,
  TextArea,
} from '@forge/react';
import { invoke } from '@forge/bridge';

const day = (iso) => (iso ? iso.slice(0, 10) : '');

const DecisionRow = ({ d, onToggle, conflictWith }) => (
  <Box padding="space.100">
    <Stack space="space.050">
      <Inline space="space.100" alignBlock="center">
        {d.superseded ? <Lozenge appearance="removed">Superseded</Lozenge> : <Lozenge appearance="success">Active</Lozenge>}
        {d.source === 'comment' && <Lozenge>from comment</Lozenge>}
        {d.source === 'rovo' && <Lozenge appearance="new">via Rovo</Lozenge>}
        {conflictWith && <Lozenge appearance="moved">Possible conflict with {conflictWith}</Lozenge>}
      </Inline>
      <Text>{d.text}</Text>
      <Inline space="space.100" alignBlock="center">
        <Text size="small">
          {d.authorName || 'Someone'} · {day(d.createdAt)}
        </Text>
        {onToggle && (
          <Button appearance="subtle" spacing="compact" onClick={() => onToggle(d.id)}>
            {d.superseded ? 'Restore' : 'Mark superseded'}
          </Button>
        )}
      </Inline>
    </Stack>
  </Box>
);

const App = () => {
  const [data, setData] = useState(null);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const load = async (fn, payload) => {
    setBusy(true);
    setError(null);
    try {
      const res = await invoke(fn, payload);
      if (res && res.error) setError(res.error);
      else setData(res);
    } catch (e) {
      setError('Something went wrong. Try again.');
    }
    setBusy(false);
  };

  useEffect(() => {
    load('getPanel');
  }, []);

  if (!data) return <Spinner label="Loading decisions" />;

  const conflictFor = (id) => {
    const c = data.conflicts.find((x) => x.mine === id);
    return c ? c.otherIssue : null;
  };

  return (
    <Stack space="space.200">
      {data.conflicts.length > 0 && (
        <SectionMessage appearance="warning" title="This may contradict an earlier decision">
          <Text>
            A decision here looks opposite to one already made on {[...new Set(data.conflicts.map((c) => c.otherIssue))].join(', ')}. Check before
            you build.
          </Text>
        </SectionMessage>
      )}

      <Heading size="small">Decisions on {data.issueKey}</Heading>
      {data.mine.length === 0 ? (
        <Text>No decisions yet. Log one below, or start any comment with "DECISION:".</Text>
      ) : (
        data.mine.map((d) => (
          <DecisionRow key={d.id} d={d} conflictWith={conflictFor(d.id)} onToggle={(id) => load('supersede', { id })} />
        ))
      )}

      <Stack space="space.100">
        <TextArea
          placeholder="e.g. Use Postgres for billing, not Mongo"
          value={text}
          onChange={(e) => setText(e.target.value)}
          isDisabled={busy}
        />
        <Inline space="space.100">
          <Button
            appearance="primary"
            isDisabled={busy || text.trim().length < 3}
            onClick={async () => {
              await load('logDecision', { text });
              setText('');
            }}
          >
            Log decision
          </Button>
        </Inline>
        {error && <Text>{error}</Text>}
      </Stack>

      <Heading size="small">Already decided elsewhere</Heading>
      {data.related.length === 0 ? (
        <Text>No related decisions found in {data.total} logged across your projects.</Text>
      ) : (
        data.related.map((d) => (
          <Stack key={d.id} space="space.0">
            <Text size="small">{d.issueKey}</Text>
            <DecisionRow d={d} />
          </Stack>
        ))
      )}
    </Stack>
  );
};

ForgeReconciler.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
