import React, { useRef, useState, useEffect, useMemo } from 'react';
import MoveCard from './MoveCard';

const API_BASE = 'http://127.0.0.1:8000';

function parseTimestampToSeconds(ts) {
  if (typeof ts === 'number') return ts;
  const s = String(ts).trim();
  const parts = s.split(':');
  if (parts.length === 2) {
    return parseInt(parts[0], 10) * 60 + parseFloat(parts[1]);
  }
  return parseFloat(s) || 0;
}

function buildSegments(moves, duration) {
  if (!moves?.length || duration <= 0) return [];
  const sorted = [...moves]
    .map((m) => ({ ...m, startSec: parseTimestampToSeconds(m.timestamp) }))
    .sort((a, b) => a.startSec - b.startSec);

  const segments = [];
  let prevEnd = 0;

  for (let i = 0; i < sorted.length; i++) {
    const move = sorted[i];
    const start = move.startSec;
    const end = i < sorted.length - 1 ? sorted[i + 1].startSec : duration;
    if (start > prevEnd) {
      segments.push({ start: prevEnd, end: start, move: null, color: 'var(--color-light)' });
    }
    segments.push({ start, end, move, color: move.match ? '#22c55e' : '#ef4444' });
    prevEnd = end;
  }
  if (prevEnd < duration) {
    segments.push({ start: prevEnd, end: duration, move: null, color: 'var(--color-light)' });
  }
  return segments;
}

export default function VideoComparisonView({ refPath, pracPath, moves = [], overallScore }) {
  const refVideoRef = useRef(null);
  const pracVideoRef = useRef(null);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isReady, setIsReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const isScrubbingRef = useRef(false);

  const refUrl = refPath ? `${API_BASE}/${refPath}` : null;
  const pracUrl = pracPath ? `${API_BASE}/${pracPath}` : null;

  const segments = useMemo(() => buildSegments(moves, duration), [moves, duration]);

  const currentMove = useMemo(() => {
    for (const seg of segments) {
      if (currentTime >= seg.start && currentTime < seg.end) return seg.move;
    }
    return null;
  }, [segments, currentTime]);

  // Determine duration from both videos (use max for full scrub range)
  useEffect(() => {
    if (!refVideoRef.current || !pracVideoRef.current) return;

    const updateDuration = () => {
      const refD = refVideoRef.current?.duration ?? 0;
      const pracD = pracVideoRef.current?.duration ?? 0;
      if (refD > 0 || pracD > 0) {
        setDuration(Math.max(refD, pracD));
        setIsReady(true);
      }
    };

    const refV = refVideoRef.current;
    const pracV = pracVideoRef.current;
    refV.addEventListener('loadedmetadata', updateDuration);
    pracV.addEventListener('loadedmetadata', updateDuration);
    if (refV.readyState >= 1) updateDuration();
    if (pracV.readyState >= 1) updateDuration();

    return () => {
      refV.removeEventListener('loadedmetadata', updateDuration);
      pracV.removeEventListener('loadedmetadata', updateDuration);
    };
  }, [refUrl, pracUrl]);

  // Sync scrubber when video plays
  useEffect(() => {
    const refV = refVideoRef.current;
    if (!refV) return;

    const onTimeUpdate = () => {
      if (!isScrubbingRef.current) setCurrentTime(refV.currentTime);
    };
    refV.addEventListener('timeupdate', onTimeUpdate);
    return () => refV.removeEventListener('timeupdate', onTimeUpdate);
  }, [refUrl, pracUrl]);

  const handleScrubberChange = (e) => {
    const t = parseFloat(e.target.value);
    isScrubbingRef.current = true;
    setCurrentTime(t);
    if (refVideoRef.current) refVideoRef.current.currentTime = t;
    if (pracVideoRef.current)
      pracVideoRef.current.currentTime = Math.min(t, pracVideoRef.current.duration || t);
    isScrubbingRef.current = false;
  };

  const handlePlayPause = () => {
    const refV = refVideoRef.current;
    const pracV = pracVideoRef.current;
    if (!refV || !pracV) return;

    if (isPlaying) {
      refV.pause();
      pracV.pause();
      setIsPlaying(false);
    } else {
      refV.muted = false;
      pracV.muted = true;
      Promise.all([refV.play(), pracV.play()])
        .then(() => setIsPlaying(true))
        .catch(() => setIsPlaying(false));
    }
  };

  // Sync play state with video events (ended, paused)
  useEffect(() => {
    const refV = refVideoRef.current;
    if (!refV) return;
    const onEnded = () => setIsPlaying(false);
    const onPause = () => setIsPlaying(false);
    refV.addEventListener('ended', onEnded);
    refV.addEventListener('pause', onPause);
    return () => {
      refV.removeEventListener('ended', onEnded);
      refV.removeEventListener('pause', onPause);
    };
  }, [refUrl, pracUrl]);

  const formatTime = (sec) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  if (!refUrl || !pracUrl) return null;

  return (
    <div
      className="video-comparison-layout"
      style={{
        marginBottom: '32px',
        border: '2px solid var(--color-purple)',
        borderRadius: '12px',
        overflow: 'hidden',
        backgroundColor: 'var(--color-light)',
      }}
    >
      {/* Left: videos + scrubber */}
      <div className="video-comparison-main">
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '0',
            backgroundColor: 'var(--color-dark)',
          }}
        >
        <div>
          <div
            style={{
              padding: '8px 12px',
              backgroundColor: 'var(--color-dark)',
              color: 'var(--color-light)',
              fontSize: '14px',
              fontWeight: 600,
            }}
          >
            Reference
          </div>
          <video
            ref={refVideoRef}
            src={refUrl}
            style={{ width: '100%', display: 'block' }}
            muted
            playsInline
            crossOrigin="anonymous"
          />
        </div>
        <div>
          <div
            style={{
              padding: '8px 12px',
              backgroundColor: 'var(--color-dark)',
              color: 'var(--color-light)',
              fontSize: '14px',
              fontWeight: 600,
            }}
          >
            Your Practice
          </div>
          <video
            ref={pracVideoRef}
            src={pracUrl}
            style={{ width: '100%', display: 'block' }}
            muted
            playsInline
            crossOrigin="anonymous"
          />
        </div>
      </div>

      {isReady && (
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: 'var(--color-light)',
          }}
        >
          {/* Play/Pause button */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
            <button
              onClick={handlePlayPause}
              className="play-pause-btn"
              style={{
                padding: '8px 20px',
                borderRadius: '8px',
                border: '2px solid var(--color-dark)',
                backgroundColor: 'var(--color-dark)',
                color: 'var(--color-light)',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              {isPlaying ? 'Pause' : 'Play'}
            </button>
            <span style={{ fontSize: '12px', color: 'var(--color-dark)', opacity: 0.7 }}>
              Reference audio plays when playing
            </span>
          </div>
          {/* Colored segments as scrubber background */}
          <div className="video-scrubber" style={{ marginBottom: '4px' }}>
            <div className="scrubber-track">
              {segments.length > 0 ? (
                segments.map((seg, i) => (
                  <div
                    key={seg.move ? seg.move.id : `gap-${i}`}
                    style={{
                      width: `${((seg.end - seg.start) / duration) * 100}%`,
                      backgroundColor: seg.color,
                      minWidth: 2,
                    }}
                    title={seg.move ? `${seg.move.label} (${seg.move.match ? 'matched' : 'needs work'})` : undefined}
                  />
                ))
              ) : (
                <div style={{ width: '100%', backgroundColor: 'var(--color-light)' }} />
              )}
            </div>
            <input
              type="range"
              min={0}
              max={duration || 0.01}
              step={0.1}
              value={currentTime}
              onChange={handleScrubberChange}
            />
          </div>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginTop: '4px',
              fontSize: '12px',
              color: 'var(--color-dark)',
              opacity: 0.7,
            }}
          >
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>
      )}
      </div>

      {/* Right: score + dynamic feedback (stacks below on small screens) */}
      <div className="video-comparison-feedback">
        {overallScore != null && (
          <div
            style={{
              padding: '16px',
              marginBottom: '16px',
              backgroundColor: 'var(--color-gold)',
              borderRadius: '12px',
              color: 'var(--color-dark)',
            }}
          >
            <strong>Overall score: {overallScore}%</strong>
          </div>
        )}
        {currentMove && (
          <MoveCard move={currentMove} />
        )}
        {!currentMove && (
          <p style={{ color: 'var(--color-dark)', opacity: 0.6, fontSize: '14px', margin: 0 }}>
            Scrub to a colored section to see feedback
          </p>
        )}
      </div>
    </div>
  );
}
