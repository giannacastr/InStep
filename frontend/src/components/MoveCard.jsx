import React, { useState } from 'react';

export default function MoveCard({ move, darkBackground }) {
  const { timestamp, label, match, feedback, tips } = move;
  const textColor = darkBackground ? 'rgba(237,242,253,0.85)' : 'var(--color-dark)';
  const muteColor = darkBackground ? 'rgba(237,242,253,0.5)' : 'var(--color-dark)';

  return (
    <>
    <div
      style={{
        border: `2px solid ${match ? 'var(--color-teal)' : 'var(--color-purple)'}`,
        borderRadius: '10px',
        padding: '11px 12px',
        marginBottom: '6px',
        textAlign: 'left',
        backgroundColor: match ? 'rgba(68, 187, 164, 0.1)' : 'rgba(180, 126, 179, 0.1)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
        <strong style={{ color: match ? 'var(--color-teal)' : 'var(--color-purple)', fontSize: '13px' }}>{label}</strong>
        <span style={{ fontSize: '10px', color: muteColor }}>{timestamp}</span>
      </div>
      {!match && feedback && (
        <p style={{ margin: '0 0 6px 0', fontSize: '12px', color: textColor, lineHeight: 1.5 }}>{feedback}</p>
      )}
      {!match && tips?.length > 0 && (
        <div style={{ marginTop: '6px' }}>
          <strong style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px', color: muteColor }}>Tips</strong>
          <ul style={{ margin: '2px 0 0 0', paddingLeft: '14px', fontSize: '11px', color: muteColor, lineHeight: 1.7 }}>
            {tips.map((tip, i) => (
              <li key={i}>{tip}</li>
            ))}
          </ul>
        </div>
      )}
      {match && <p style={{ margin: 0, fontSize: '12px', color: 'var(--color-teal)', fontWeight: 600 }}>✓ Matched</p>}
    </div>

      {/* Ignore confirmation modal */}
      {showConfirmModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(0,0,0,0.4)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={handleConfirmNo}
        >
          <div
            style={{
              backgroundColor: 'var(--color-light)',
              padding: '28px 32px',
              borderRadius: '12px',
              maxWidth: '360px',
              boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
              border: '2px solid var(--color-dark)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: '0 0 12px 0', fontSize: '22px', color: 'var(--color-dark)' }}>
              Ignore suggestion?
            </h3>
            <p style={{ margin: '0 0 24px 0', fontSize: '14px', color: 'var(--color-dark)', opacity: 0.85 }}>
              If you say yes, we won't suggest this change anymore.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={handleConfirmNo}
                style={{
                  padding: '10px 20px',
                  borderRadius: '8px',
                  border: '2px solid var(--color-dark)',
                  backgroundColor: 'transparent',
                  color: 'var(--color-dark)',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                No
              </button>
              <button
                type="button"
                onClick={handleConfirmYes}
                style={{
                  padding: '10px 20px',
                  borderRadius: '8px',
                  border: '2px solid var(--color-dark)',
                  backgroundColor: 'var(--color-dark)',
                  color: 'var(--color-light)',
                  cursor: 'pointer',
                  fontWeight: 600,
                }}
              >
                Yes
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
