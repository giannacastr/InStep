import React, { useState } from 'react';
import VideoUploadCard from '../components/VideoUploadCard';

export default function UploadScreen({ onAnalyze }) {
  const [refFile, setRefFile] = useState(null);
  const [pracFile, setPracFile] = useState(null);
  const [status, setStatus] = useState("Upload your videos to begin");

  const handleUpload = async () => {
    if (!refFile || !pracFile) {
      setStatus("Please select both videos first!");
      return;
    }

    setStatus("Syncing videos...");
    const formData = new FormData();
    formData.append('ref_file', refFile);
    formData.append('prac_file', pracFile);

    try {
      const response = await fetch('http://127.0.0.1:8000/upload-comparison', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      setStatus(data.message);
      if (data.status === "Success" && onAnalyze) {
        onAnalyze(data);
      }
    } catch (error) {
      setStatus("Error connecting to InStep backend.");
    }
  };

  return (
    <div style={{ textAlign: 'center', marginTop: '40px' }}>
      <h1 style={{ color: 'var(--color-dark)', marginBottom: '8px' }}>InStep</h1>
      <p style={{ color: 'var(--color-dark)', opacity: 0.85 }}>{status}</p>

      <div style={{ display: 'flex', justifyContent: 'center', gap: '24px', padding: '24px', flexWrap: 'wrap' }}>
        <VideoUploadCard
          title="Reference Video"
          file={refFile}
          onFileChange={setRefFile}
        />
        <VideoUploadCard
          title="Your Practice"
          file={pracFile}
          onFileChange={setPracFile}
        />
      </div>

      <button onClick={handleUpload} className="cta-button">
        Analyze Move-by-Move
      </button>
    </div>
  );
}