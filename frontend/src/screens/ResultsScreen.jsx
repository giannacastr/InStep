import React from 'react';
import VideoComparisonView from '../components/VideoComparisonView';
import { mockAnalysis } from '../data/mockAnalysis';

export default function ResultsScreen({ data, onTryAgain }) {
  // Use real analysis from backend when available, otherwise mock data
  const analysis = data?.analysis ?? mockAnalysis.analysis;
  const { moves = [], overallScore } = analysis;

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '0 24px' }}>
      <h1 style={{ textAlign: 'center', marginBottom: '8px', color: 'var(--color-dark)' }}>InStep</h1>
      <p style={{ textAlign: 'center', color: 'var(--color-dark)', opacity: 0.8, marginBottom: '24px' }}>
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
          <button onClick={onTryAgain} className="cta-button">
            Upload New Videos
          </button>
        </div>
      )}
    </div>
  );
}
