import React from 'react';
import VideoComparisonView from '../components/VideoComparisonView';
import { mockAnalysis } from '../data/mockAnalysis';

export default function ResultsScreen({ data, onTryAgain }) {
  const analysis = data?.analysis ?? mockAnalysis.analysis;
  const { moves = [], overallScore } = analysis;

  return (
    <div className="results-page">
      <div className="results-page__bg">
        <div className="results-page__blob-gold" />
        <div className="results-page__blob-teal" />
        <div className="results-page__blob-purple" />
      </div>
      <div className="results-page__logo">InStep</div>

      <div className="results-page__inner">
        <p className="results-page__subtitle">Move-by-move analysis</p>

        {data?.ref_path && data?.prac_path && (
          <VideoComparisonView
            refPath={data.ref_path}
            pracPath={data.prac_path}
            sync={data.sync}
            moves={moves}
            overallScore={overallScore}
          />
        )}

        {onTryAgain && (
          <div style={{ textAlign: 'center', marginTop: '32px' }}>
            <button type="button" onClick={onTryAgain} className="results-page__upload-btn">
              Upload New Videos
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
