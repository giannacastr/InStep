import React, { useState } from 'react';
import VideoUploadCard from '../components/VideoUploadCard';

export default function UploadScreen({ onAnalyze }) {
  const [refFile, setRefFile] = useState(null);
  const [pracFile, setPracFile] = useState(null);
  const [status, setStatus] = useState("Upload your videos to begin");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleUpload = async () => {
    if (!refFile || !pracFile) {
      setStatus("Please select both videos first!");
      return;
    }

    setStatus("Syncing videos...");
    setIsSubmitting(true);
    const formData = new FormData();
    formData.append('ref_file', refFile);
    formData.append('prac_file', pracFile);

    try {
      const response = await fetch('http://127.0.0.1:8000/upload-comparison', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      setStatus(data.message || "Upload complete.");
      if (!data.ref_path || !data.prac_path) {
        if (!response.ok) setStatus("Upload failed. Please try again.");
        return;
      }
      setStatus("Syncing videos by audio...");
      try {
        const syncRes = await fetch('http://127.0.0.1:8000/compute-sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ref_path: data.ref_path, prac_path: data.prac_path }),
        });
        const syncData = await syncRes.json();
        
        setStatus("Analyzing movements...");
        
        let analysisData = null;
        try {
          const analysisRes = await fetch('http://127.0.0.1:8000/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              ref_path: data.ref_path, 
              prac_path: data.prac_path,
              offset: syncData.offset || 0
            }),
          });
          analysisData = await analysisRes.json();
        } catch (err) {
          console.warn('Analysis endpoint not available:', err);
        }
        
        if (onAnalyze) onAnalyze({ ...data, sync: syncData, analysis: analysisData });
      } catch {
        if (onAnalyze) onAnalyze({ ...data, sync: { success: false, offset: 0 }, analysis: null });
      }
    } catch {
      setStatus("Error connecting to InStep backend.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={`upload-page ${isSubmitting ? 'is-analyzing' : ''}`}>
      <div className="upload-page__blur-wrap">
        <div className="upload-page__blur-circle-warm" aria-hidden />
        <div className="upload-page__blur-circle-cool" aria-hidden />
      </div>
      <h1 className="upload-page__title">InStep</h1>
      <p className="upload-page__status">{status}</p>

      <div className="upload-page__cards">
        <VideoUploadCard
          title="Practice Video"
          file={pracFile}
          onFileChange={setPracFile}
        />
        <VideoUploadCard
          title="Reference Video"
          file={refFile}
          onFileChange={setRefFile}
        />
      </div>

      <button
        type="button"
        onClick={handleUpload}
        disabled={!refFile || !pracFile || isSubmitting}
        className="cta-button upload-page__analyze"
      >
        {isSubmitting ? "Analyzing..." : "Analyze"}
      </button>
    </div>
  );
}
