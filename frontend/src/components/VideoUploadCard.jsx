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
