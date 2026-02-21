import React, { useState, useEffect } from 'react';
import './App.css';
import { Routes, Route, useNavigate } from 'react-router-dom';
import UploadScreen from './screens/UploadScreen';
import LoadingScreen from './screens/LoadingScreen';
import ResultsScreen from './screens/ResultsScreen';
import { mockAnalysis } from './data/mockAnalysis';

function App() {
  const [currentScreen, setCurrentScreen] = useState('upload');
  const [uploadResult, setUploadResult] = useState(null);

  // Preview results screen: open http://localhost:5176/#results
  useEffect(() => {
    if (window.location.hash === '#results') {
      setUploadResult({
        ref_path: mockAnalysis.ref_path,
        prac_path: mockAnalysis.prac_path,
        analysis: mockAnalysis.analysis,
      });
      setCurrentScreen('results');
    }
  }, []);

  const navigate = useNavigate();

  const handleAnalyze = (data) => {
    setUploadResult(data);
    setCurrentScreen('loading');
    setTimeout(() => setCurrentScreen('results'), 2000);
  };

  const handleTryAgain = async () => {
    if (uploadResult?.ref_path || uploadResult?.prac_path) {
      try {
        await fetch('http://127.0.0.1:8000/clear-uploads', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ref_path: uploadResult.ref_path,
            prac_path: uploadResult.prac_path,
          }),
        });
      } catch (_) {
        // Backend may be offline; still go back to upload screen
      }
    }
    setCurrentScreen('upload');
    setUploadResult(null);
  };

  return (
    <div className="app-container">
      {currentScreen === 'upload' && <UploadScreen onAnalyze={handleAnalyze} />}
      {currentScreen === 'loading' && <LoadingScreen />}
      {currentScreen === 'results' && (
        <ResultsScreen data={uploadResult} onTryAgain={handleTryAgain} />
      )}
    </div>
  );
}

export default App;