import React from 'react';

export default function LoadingScreen() {
  return (
    <div style={{ textAlign: 'center', marginTop: '80px' }}>
      <h1 style={{ color: 'var(--color-dark)' }}>InStep</h1>
      <p style={{ color: 'var(--color-dark)', opacity: 0.8 }}>Analyzing your moves...</p>
    </div>
  );
}