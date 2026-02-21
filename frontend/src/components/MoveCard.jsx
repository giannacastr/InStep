import React, { useState } from 'react';

export default function MoveCard({ move, onIgnore }) {
  const { timestamp, label, match, feedback, tips } = move;
  const [showTooltip, setShowTooltip] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  const handleIgnoreClick = () => setShowConfirmModal(true);
  const handleConfirmNo = () => setShowConfirmModal(false);
  const handleConfirmYes = () => {
    onIgnore?.(move);
    setShowConfirmModal(false);
  };

  return (
    <>
    <div
      style={{
        border: `2px solid ${match ? '#22c55e' : '#ef4444'}`,
        borderRadius: '12px',
        padding: '16px',
        marginBottom: '12px',
        textAlign: 'left',
        backgroundColor: match ? '#e8f5e9' : '#ffebee',
        position: 'relative',
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

      {!match && (
        <div
          style={{
            marginTop: '12px',
            position: 'relative',
          }}
        >
          <button
            type="button"
            onClick={handleIgnoreClick}
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
            title="You like how you did this move better."
            style={{
              padding: 0,
              border: 'none',
              background: 'none',
              cursor: 'pointer',
              fontSize: '11px',
              color: 'var(--color-dark)',
              opacity: 0.6,
              textDecoration: 'underline',
            }}
          >
            Ignore suggestion
          </button>
          {showTooltip && (
            <div
              style={{
                position: 'absolute',
                bottom: '100%',
                left: 0,
                marginBottom: '4px',
                padding: '6px 10px',
                fontSize: '11px',
                color: 'var(--color-light)',
                backgroundColor: 'var(--color-dark)',
                borderRadius: '6px',
                whiteSpace: 'nowrap',
                boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                zIndex: 10,
              }}
            >
              You like how you did this move better.
            </div>
          )}
        </div>
      )}
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
