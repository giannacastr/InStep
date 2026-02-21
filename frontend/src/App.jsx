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

  return (
    <>
      {currentScreen === 'upload' && <UploadScreen onAnalyze={handleAnalyze} />}
      {currentScreen === 'loading' && <LoadingScreen />}
      {currentScreen === 'results' && <ResultsScreen data={uploadResult} />}
    </>
  );
}

export default App;