import React from 'react';
import VideoComparisonView from '../components/VideoComparisonView';
import { mockAnalysis } from '../data/mockAnalysis';

export default function ResultsScreen({ data, onTryAgain }) {
  // Use real analysis from backend when available, otherwise mock data
  const analysis = data?.analysis ?? mockAnalysis.analysis;
  const { moves = [], overallScore } = analysis;

  return (
    <div style={{ maxWidth: '900px', margin: '40px auto', padding: '0 20px', fontFamily: 'sans-serif' }}>
      <h1 style={{ textAlign: 'center', marginBottom: '8px' }}>InStep</h1>
      <p style={{ textAlign: 'center', color: '#666', marginBottom: '24px' }}>
        Move-by-move analysis
      </p>

      {data?.ref_path && data?.prac_path && (
        <VideoComparisonView
          refPath={data.ref_path}
          pracPath={data.prac_path}
          moves={moves}
          overallScore={overallScore}
        />
      )}

      {onTryAgain && (
        <div style={{ textAlign: 'center', marginTop: '32px' }}>
          <button
            onClick={onTryAgain}
            style={{
              padding: '10px 24px',
              cursor: 'pointer',
              backgroundColor: '#000',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              fontSize: '14px',
            }}
          >
            Upload New Videos
          </button>
        </div>
      )}
    </div>
  );
}
