import React from 'react';

export default function MoveCard({ move }) {
  const { timestamp, label, match, feedback, tips } = move;

  return (
    <div
      style={{
        border: `2px solid ${match ? '#22c55e' : '#ef4444'}`,
        borderRadius: '12px',
        padding: '16px',
        marginBottom: '12px',
        textAlign: 'left',
        backgroundColor: match ? '#e8f5e9' : '#ffebee',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <strong style={{ color: 'var(--color-dark)' }}>{label}</strong>
        <span style={{ fontSize: '14px', color: 'var(--color-dark)', opacity: 0.7 }}>{timestamp}</span>
      </div>
      {!match && feedback && (
        <p style={{ margin: '0 0 8px 0', fontSize: '14px', color: 'var(--color-dark)' }}>{feedback}</p>
      )}
      {!match && tips.length > 0 && (
        <div style={{ marginTop: '8px' }}>
          <strong style={{ fontSize: '13px', color: 'var(--color-dark)' }}>Tips:</strong>
          <ul style={{ margin: '4px 0 0 0', paddingLeft: '20px', fontSize: '13px', color: 'var(--color-dark)' }}>
            {tips.map((tip, i) => (
              <li key={i}>{tip}</li>
            ))}
          </ul>
        </div>
      )}
      {match && <p style={{ margin: 0, fontSize: '14px', color: '#2e7d32', fontWeight: 600 }}>✓ Matched</p>}
    </div>
  );
}
