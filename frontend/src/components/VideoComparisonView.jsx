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

function buildSegments(moves, duration, ignoredMoveIds = new Set()) {
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
      segments.push({ start: prevEnd, end: start, move: null, color: 'rgba(237, 242, 253, 0.2)' });
    }
    const isIgnored = ignoredMoveIds.has(move.id);
    if (isIgnored) {
      segments.push({ start, end, move: null, color: 'rgba(237, 242, 253, 0.2)' });
    } else {
      segments.push({ start, end, move, color: move.match ? '#0B7A25' : '#960319' });
    }
    prevEnd = end;
  }
  if (prevEnd < duration) {
    segments.push({ start: prevEnd, end: duration, move: null, color: 'rgba(237, 242, 253, 0.2)' });
  }
  return segments;
}

export default function VideoComparisonView({ refPath, pracPath, sync, moves = [], overallScore }) {
  const refVideoRef = useRef(null);
  const pracVideoRef = useRef(null);
  const [duration, setDuration] = useState(0);
  const [refDuration, setRefDuration] = useState(0);
  const [pracDuration, setPracDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isReady, setIsReady] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [ignoredMoveIds, setIgnoredMoveIds] = useState(() => new Set());
  const isScrubbingRef = useRef(false);
  const scrubTimeoutRef = useRef(null);

  const syncOffset = sync?.success ? (sync.offset ?? 0) : 0;
  const useSync = sync?.success && syncOffset !== undefined;

  const SPEED_OPTIONS = [0.25, 0.5, 0.75, 1];

  const handleIgnoreMove = (move) => {
    setIgnoredMoveIds((prev) => new Set(prev).add(move.id));
  };

  const refUrl = refPath ? `${API_BASE}/${refPath}` : null;
  const pracUrl = pracPath ? `${API_BASE}/${pracPath}` : null;

  const segments = useMemo(
    () => buildSegments(moves, duration, ignoredMoveIds),
    [moves, duration, ignoredMoveIds]
  );

  const displayScore = useMemo(() => {
    if (overallScore == null) return null;
    if (!moves?.length) return overallScore;
    const activeMoves = moves.filter((m) => !ignoredMoveIds.has(m.id));
    if (!activeMoves.length) return 0;
    const matched = activeMoves.filter((m) => m.match).length;
    return Math.round((matched / activeMoves.length) * 100);
  }, [moves, ignoredMoveIds, overallScore]);

  const currentMove = useMemo(() => {
    for (const seg of segments) {
      if (currentTime >= seg.start && currentTime < seg.end) return seg.move;
    }
    return null;
  }, [segments, currentTime]);

  const pracDisplayTime = currentTime - syncOffset;
  const refInRange = refDuration <= 0 || (currentTime >= 0 && currentTime < refDuration);
  const pracInRange = pracDuration <= 0 || (pracDisplayTime >= 0 && pracDisplayTime < pracDuration);

  // Determine duration from both videos; with sync use full timeline span
  useEffect(() => {
    if (!refVideoRef.current || !pracVideoRef.current) return;

    const updateDuration = () => {
      const refD = refVideoRef.current?.duration ?? sync?.ref_duration ?? 0;
      const pracD = pracVideoRef.current?.duration ?? sync?.prac_duration ?? 0;
      if (refD > 0 || pracD > 0) {
        setRefDuration(refD);
        setPracDuration(pracD);
        const displayDuration = useSync
          ? Math.max(refD, syncOffset + pracD)
          : Math.max(refD, pracD);
        setDuration(displayDuration);
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
  }, [refUrl, pracUrl, useSync, syncOffset, sync?.ref_duration, sync?.prac_duration]);

  // Sync scrubber and practice video when ref plays
  useEffect(() => {
    const refV = refVideoRef.current;
    const pracV = pracVideoRef.current;
    if (!refV) return;

    const onTimeUpdate = () => {
      if (!isScrubbingRef.current) {
        const t = refV.currentTime;
        setCurrentTime(t);
        if (pracV) {
          const pracT = t - syncOffset;
          if (pracT >= 0 && pracT < (pracV.duration || Infinity)) pracV.currentTime = pracT;
        }
      }
    };
    refV.addEventListener('timeupdate', onTimeUpdate);
    return () => refV.removeEventListener('timeupdate', onTimeUpdate);
  }, [refUrl, pracUrl, syncOffset]);

  const handleScrubberChange = (e) => {
    const t = parseFloat(e.target.value);
    if (scrubTimeoutRef.current) clearTimeout(scrubTimeoutRef.current);
    isScrubbingRef.current = true;
    setCurrentTime(t);
    if (refVideoRef.current && t < (refVideoRef.current.duration || Infinity))
      refVideoRef.current.currentTime = t;
    if (pracVideoRef.current) {
      const pracT = t - syncOffset;
      if (pracT >= 0 && pracT < (pracVideoRef.current.duration || Infinity))
        pracVideoRef.current.currentTime = pracT;
    }
    scrubTimeoutRef.current = setTimeout(() => {
      isScrubbingRef.current = false;
      scrubTimeoutRef.current = null;
    }, 100);
  };

  // Apply playback speed to both videos
  useEffect(() => {
    if (refVideoRef.current) refVideoRef.current.playbackRate = playbackRate;
    if (pracVideoRef.current) pracVideoRef.current.playbackRate = playbackRate;
  }, [playbackRate, refUrl, pracUrl]);

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
      const pracT = refV.currentTime - syncOffset;
      if (pracT >= 0 && pracT < (pracV.duration || Infinity)) pracV.currentTime = pracT;
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
        display: 'flex',
        flex: 1,
        gap: '18px',
        minHeight: 0,
        height: 'fit-content',
      }}
    >
      {/* Left: videos + scrubber - fixed height based on aspect ratio */}
      <div className="video-comparison-main" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', borderRadius: '14px', overflow: 'hidden', border: '1px solid rgba(237,242,253,0.07)' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            background: '#050d12',
            aspectRatio: '1',
            minHeight: 180,
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', borderRight: '1px solid rgba(237,242,253,0.05)', background: '#050d12', minHeight: 0 }}>
            <div style={{ padding: '7px 14px', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1.5px', color: 'rgba(237,242,253,0.38)', borderBottom: '1px solid rgba(237,242,253,0.04)' }}>
              Reference
            </div>
            <div style={{ flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', background: '#000' }}>
              <video
                ref={refVideoRef}
                src={refUrl}
                style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', opacity: refInRange ? 1 : 0 }}
                muted
                playsInline
                crossOrigin="anonymous"
              />
              {!refInRange && <div style={{ position: 'absolute', inset: 0, background: '#000', zIndex: 1 }} aria-hidden />}
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', background: '#050d12', minHeight: 0 }}>
            <div style={{ padding: '7px 14px', fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '1.5px', color: 'rgba(237,242,253,0.38)', borderBottom: '1px solid rgba(237,242,253,0.04)' }}>
              Your Practice
            </div>
            <div style={{ flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', background: '#000' }}>
              <video
                ref={pracVideoRef}
                src={pracUrl}
                style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', opacity: pracInRange ? 1 : 0 }}
                muted
                playsInline
                crossOrigin="anonymous"
              />
              {!pracInRange && <div style={{ position: 'absolute', inset: 0, background: '#000', zIndex: 1 }} aria-hidden />}
            </div>
          </div>
        </div>

        <div className="video-comparison-controls" style={{ padding: '10px 12px 12px', background: 'rgba(7,16,22,0.97)', borderTop: '1px solid rgba(237,242,253,0.05)', flexShrink: 0 }}>
          <div className="video-scrubber" style={{ marginBottom: '4px' }}>
            <div className="scrubber-track">
              {isReady && segments.length > 0 ? (
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
                <div style={{ width: '100%', backgroundColor: 'rgba(237,242,253,0.12)' }} />
              )}
            </div>
            <input
              type="range"
              min={0}
              max={duration || 0.01}
              step={0.1}
              value={currentTime}
              onChange={handleScrubberChange}
              disabled={!isReady}
              style={{ opacity: isReady ? 1 : 0.5 }}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: 'rgba(237,242,253,0.28)', marginBottom: '8px' }}>
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={handlePlayPause}
              disabled={!isReady}
              className="play-pause-btn video-comparison-play-btn"
              style={{
                width: 30,
                height: 30,
                minWidth: 30,
                minHeight: 30,
                aspectRatio: '1',
                borderRadius: '50%',
                border: 'none',
                cursor: isReady ? 'pointer' : 'not-allowed',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                flex: '0 0 30px',
                padding: 0,
                background: 'linear-gradient(135deg, var(--color-purple), var(--color-teal))',
                boxShadow: '0 0 14px rgba(68,187,164,0.3)',
                opacity: isReady ? 1 : 0.5,
              }}
            >
              {isPlaying ? (
                <svg width="11" height="11" viewBox="0 0 24 24" fill="white"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
              ) : (
                <svg width="11" height="11" viewBox="0 0 24 24" fill="white"><polygon points="5,3 19,12 5,21"/></svg>
              )}
            </button>
            <div style={{ display: 'flex', gap: 3 }}>
              {SPEED_OPTIONS.map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setPlaybackRate(r)}
                  disabled={!isReady}
                  style={{
                    padding: '3px 8px',
                    fontSize: '10px',
                    borderRadius: 4,
                    border: `1px solid ${playbackRate === r ? 'var(--color-purple)' : 'rgba(237,242,253,0.15)'}`,
                    background: playbackRate === r ? 'rgba(180,126,179,0.2)' : 'transparent',
                    color: playbackRate === r ? 'var(--color-purple)' : 'rgba(237,242,253,0.4)',
                    cursor: isReady ? 'pointer' : 'default',
                    fontFamily: 'inherit',
                  }}
                >
                  {r}
                </button>
              ))}
            </div>
            <span style={{ fontSize: '10px', color: 'rgba(237,242,253,0.45)' }}>Ref audio when playing</span>
          </div>
        </div>
      </div>

      {/* Right: accuracy + feedback - fixed height to match video column */}
      <div className="video-comparison-feedback" style={{ width: '220px', minWidth: '200px', maxWidth: '100%', flexShrink: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', alignSelf: 'stretch' }}>
        {displayScore != null && (
          <div
            className="video-comparison-score-block"
            style={{
              padding: '16px 14px 12px',
              background: 'linear-gradient(150deg, rgba(231,187,65,0.18) 0%, rgba(231,187,65,0.06) 40%, transparent 100%)',
              flexShrink: 0,
            }}
          >
            <div style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '1.5px', color: 'rgba(237,242,253,0.38)', marginBottom: '1px' }}>Accuracy</div>
            <div
              style={{
                fontFamily: "'Barlow Condensed', sans-serif",
                fontWeight: 900,
                fontSize: '48px',
                lineHeight: 1,
                background: 'linear-gradient(120deg, var(--color-gold) 0%, #f5d06a 50%, var(--color-teal) 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                filter: 'drop-shadow(0 0 16px rgba(231,187,65,0.5))',
              }}
            >
              {displayScore}%
            </div>
            <div style={{ marginTop: '10px', height: 4, borderRadius: 2, background: 'rgba(237,242,253,0.08)', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${displayScore}%`, borderRadius: 2, background: 'linear-gradient(90deg, var(--color-gold), var(--color-teal))', transition: 'width 1s cubic-bezier(0.4,0,0.2,1)' }} />
            </div>
          </div>
        )}
        <div style={{ flex: 1, minHeight: 140, overflowY: 'auto', padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {currentMove && (
            <MoveCard move={currentMove} darkBackground onIgnore={handleIgnoreMove} />
          )}
          {!currentMove && (
            <p style={{ color: 'rgba(237,242,253,0.5)', fontSize: '13px', margin: 0 }}>
              Scrub to a colored section to see feedback
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
