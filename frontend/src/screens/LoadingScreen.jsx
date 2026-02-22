import React from 'react';

export default function LoadingScreen() {
  return (
    <div className="loading-page">
      <div className="loading-page__blur-wrap" aria-hidden>
        <div className="loading-page__blob loading-page__blob-gold" />
        <div className="loading-page__blob loading-page__blob-teal" />
        <div className="loading-page__blob loading-page__blob-purple" />
      </div>
      <h1 className="loading-page__title">InStep</h1>
      <p className="loading-page__text">Analyzing your moves...</p>
    </div>
  );
}
