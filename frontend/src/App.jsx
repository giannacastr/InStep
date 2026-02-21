import React, { useState } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import UploadScreen from './screens/UploadScreen';
import LoadingScreen from './screens/LoadingScreen';
import ResultsScreen from './screens/ResultsScreen';

function App() {
  const [currentScreen, setCurrentScreen] = useState('upload');
  const [uploadResult, setUploadResult] = useState(null);
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
    <>
      {currentScreen === 'upload' && <UploadScreen onAnalyze={handleAnalyze} />}
      {currentScreen === 'loading' && <LoadingScreen />}
      {currentScreen === 'results' && (
        <ResultsScreen data={uploadResult} onTryAgain={handleTryAgain} />
      )}
    </>
  );
}

export default App;