import React, { useState } from 'react';

function App() {
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
    } catch (error) {
      setStatus("Error connecting to InStep backend.");
    }
  };

  return (
    <div style={{ textAlign: 'center', marginTop: '40px', fontFamily: 'sans-serif' }}>
      <h1>InStep</h1>
      <p>{status}</p>

      <div style={{ display: 'flex', justifyContent: 'center', gap: '20px', padding: '20px' }}>
        <div style={{ border: '1px solid #ddd', padding: '20px' }}>
          <h3>Reference Video</h3>
          <input type="file" onChange={(e) => setRefFile(e.target.files[0])} />
        </div>

        <div style={{ border: '1px solid #ddd', padding: '20px' }}>
          <h3>Your Practice</h3>
          <input type="file" onChange={(e) => setPracFile(e.target.files[0])} />
        </div>
      </div>

      <button onClick={handleUpload} style={{ padding: '10px 30px', cursor: 'pointer', backgroundColor: '#000', color: '#fff', border: 'none' }}>
        Analyze Move-by-Move
      </button>
    </div>
  );
}

export default App;