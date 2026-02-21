import React from 'react';

export default function MoveCard({ move }) {
  const { timestamp, label, match, feedback, tips } = move;

  return (
    <div
      style={{
        border: `1px solid ${match ? '#c8e6c9' : '#ffcdd2'}`,
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '12px',
        textAlign: 'left',
        backgroundColor: match ? '#e8f5e9' : '#ffebee',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <strong>{label}</strong>
        <span style={{ fontSize: '14px', color: '#666' }}>{timestamp}</span>
      </div>
      {!match && feedback && (
        <p style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#333' }}>{feedback}</p>
      )}
      {!match && tips.length > 0 && (
        <div style={{ marginTop: '8px' }}>
          <strong style={{ fontSize: '13px' }}>Tips:</strong>
          <ul style={{ margin: '4px 0 0 0', paddingLeft: '20px', fontSize: '13px' }}>
            {tips.map((tip, i) => (
              <li key={i}>{tip}</li>
            ))}
          </ul>
        </div>
      )}
      {match && <p style={{ margin: 0, fontSize: '14px', color: '#2e7d32' }}>✓ Matched</p>}
    </div>
  );
}
