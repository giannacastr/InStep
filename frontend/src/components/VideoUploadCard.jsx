import React, { useRef } from 'react';

export default function VideoUploadCard({ title, file, onFileChange }) {
  const inputRef = useRef(null);

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleChange = (e) => {
    const chosen = e.target.files?.[0];
    onFileChange(chosen ?? null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div className="upload-card">
      <label className="upload-card__label">{title}</label>
      <div className="upload-card__hint" aria-hidden>
        {title && title.toLowerCase().includes('practice') ? (
          <>
            Your practice clip — the recording you want to improve. Use this
            upload for the performance you'd like feedback on.
          </>
        ) : (
          <>
            The example you're modeling or drawing inspiration from. Upload
            the video you'd like to match or learn from.
          </>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        onChange={handleChange}
        className="upload-card__input"
        aria-label={`Choose ${title}`}
      />
      <div className="upload-card__choose-wrap">
        <button type="button" onClick={handleClick} className="upload-card__choose-btn">
          Choose file
        </button>
      </div>
      {file && (
        <p className="upload-card__filename" title={file.name}>
          {file.name}
        </p>
      )}
    </div>
  );
}
