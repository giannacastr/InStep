import React from 'react';

export default function VideoUploadCard({ title, file, onFileChange }) {
  return (
    <div style={{ border: '1px solid #ddd', padding: '20px' }}>
      <h3>{title}</h3>
      <input type="file" accept="video/*" onChange={(e) => onFileChange(e.target.files[0])} />
      {file && <p style={{ marginTop: '8px', fontSize: '14px', color: '#666' }}>{file.name}</p>}
    </div>
  );
}