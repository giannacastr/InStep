import React from 'react';

export default function VideoUploadCard({ title, file, onFileChange }) {
  return (
    <div
      style={{
        border: `2px solid var(--color-purple)`,
        borderRadius: '12px',
        padding: '24px',
        backgroundColor: 'var(--color-light)',
        minWidth: 260,
      }}
    >
      <h3 style={{ margin: '0 0 12px 0', color: 'var(--color-dark)' }}>{title}</h3>
      <input
        type="file"
        accept="video/*"
        onChange={(e) => onFileChange(e.target.files[0])}
        style={{ fontSize: '14px' }}
      />
      {file && (
        <p style={{ marginTop: '12px', fontSize: '14px', color: 'var(--color-dark)', opacity: 0.8 }}>
          {file.name}
        </p>
      )}
    </div>
  );
}