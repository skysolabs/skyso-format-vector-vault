import React, { useState } from 'react';
import { compressFiles, inspectSky, restoreSky } from './api.js';

const sizeLabel = bytes => {
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB']; let value = bytes / 1024, unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit++; }
  return `${value.toFixed(value >= 100 ? 0 : 1)} ${units[unit]}`;
};
const iconFor = name => {
  const ext = name.split('.').pop().toLowerCase();
  if (['jpg','jpeg','png','webp','gif','svg'].includes(ext)) return '▧';
  if (['mp4','mkv','mov','avi','webm'].includes(ext)) return '▷';
  if (['mp3','wav','flac','m4a'].includes(ext)) return '♫';
  if (['csv','json','xlsx'].includes(ext)) return '▦';
  if (['js','jsx','py','html','css'].includes(ext)) return '</>';
  return '▤';
};

function DropZone({ accept, multiple, onFiles, disabled, title, subtitle }) {
  const [dragging, setDragging] = useState(false);
  const add = list => { if (list?.length) onFiles(Array.from(list)); };
  return <div className={`drop-zone ${dragging ? 'dragging' : ''} ${disabled ? 'disabled' : ''}`} onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); if (!disabled) add(e.dataTransfer.files); }}>
    <div className="upload-icon" aria-hidden="true">↑</div><strong>{title}</strong><span>or</span>
    <label className="button secondary choose-button">Choose {multiple ? 'Files' : '.sky File'}<input type="file" accept={accept} multiple={multiple} disabled={disabled} onChange={e => { add(e.target.files); e.target.value = ''; }} /></label>
    <small>{subtitle}</small>
  </div>;
}

function FileRow({ file, onRemove, selected, onSelect, restoring }) {
  return <div className="file-row">
    {onSelect && <input aria-label={`Select ${file.name}`} type="checkbox" checked={selected} onChange={e => onSelect(e.target.checked)} />}
    <div className="file-icon">{iconFor(file.name)}</div><div className="file-meta"><strong title={file.name}>{file.name}</strong>{restoring && <small>Ready to restore</small>}</div>
    <span className="file-size">{sizeLabel(file.size)}</span>{onRemove && <button className="remove" aria-label={`Remove ${file.name}`} onClick={onRemove}>×</button>}
  </div>;
}

function App() {
  const [tab, setTab] = useState('compress');
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [sky, setSky] = useState(null);
  const [inspection, setInspection] = useState(null);
  const [selected, setSelected] = useState([]);
  const [download, setDownload] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const reset = next => { setTab(next); setFiles([]); setSky(null); setInspection(null); setSelected([]); setDownload(null); setError(''); setSuccess(''); };
  const addFiles = list => {
    setError(''); setSuccess('');
    const names = new Set(files.map(f => f.name.toLocaleLowerCase()));
    const accepted = list.filter(f => { if (names.has(f.name.toLocaleLowerCase())) return false; names.add(f.name.toLocaleLowerCase()); return true; });
    if (accepted.length < list.length) setError('Files must have unique filenames. Duplicate selections were skipped.');
    setFiles(current => [...current, ...accepted]);
  };
  const doCompress = async () => {
    if (!files.length) return;
    setBusy(true); setError(''); setSuccess('');
    try {
      const blob = await compressFiles(files); const url = URL.createObjectURL(blob);
      setDownload({ url, name: 'skyso_files.sky', label: 'Download your .sky file' }); setSuccess('Your Skyso file is ready.');
    } catch (e) { setError(e.message || 'Compression failed. Please try again.'); }
    finally { setBusy(false); }
  };
  const inspect = async list => {
    const file = list.find(f => f.name.toLowerCase().endsWith('.sky'));
    if (!file) { setError('Choose a file with the .sky extension.'); return; }
    setBusy(true); setError(''); setSuccess(''); setSky(file); setInspection(null);
    try { const info = await inspectSky(file); setInspection(info); setSelected(info.files.map(f => f.name)); }
    catch (e) { setSky(null); setError(e.message || 'This .sky file could not be read.'); }
    finally { setBusy(false); }
  };
  const doRestore = async all => {
    if (!sky || !inspection) return;
    const chosen = all ? inspection.files.map(f => f.name) : selected;
    if (!chosen.length) { setError('Select at least one file to restore.'); return; }
    setBusy(true); setError(''); setSuccess('');
    try {
      const result = await restoreSky(sky, all ? null : chosen); const url = URL.createObjectURL(result.blob);
      const encodedName = result.disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
      const dispositionName = encodedName ? decodeURIComponent(encodedName) : result.disposition.match(/filename="?([^";]+)"?/i)?.[1];
      setDownload({ url, name: dispositionName || (chosen.length === 1 ? chosen[0] : 'restored_files.zip'), label: 'Download restored files' });
      setSuccess(`${chosen.length} ${chosen.length === 1 ? 'file' : 'files'} restored and verified.`);
    } catch (e) { setError(e.message || 'Restoration failed. No files were downloaded.'); }
    finally { setBusy(false); }
  };
  const total = files.reduce((sum, file) => sum + file.size, 0);

  return <main className="app-shell">
    <header className="site-header"><a className="brand" href="#top" onClick={e => { e.preventDefault(); reset('compress'); }}><span className="brand-mark">S</span><span><b>SKYso</b><small>Portable data. One container.</small></span></a><nav aria-label="Main navigation"><button className={tab === 'compress' ? 'active' : ''} onClick={() => reset('compress')}>Compress</button><button className={tab === 'decompress' ? 'active' : ''} onClick={() => reset('decompress')}>Decompress</button></nav></header>
    <section className="workspace">
      <div className="eyebrow"><span className="status-dot" /> PRIVATE, PORTABLE, PRECISE</div>
      {tab === 'compress' ? <>
        <h1>Compress files</h1><p className="intro">Combine and compress your files into a portable <code>.sky</code> container.</p>
        {!files.length && <DropZone accept="*/*" multiple onFiles={addFiles} disabled={busy} title="Drop files here" subtitle="Images · Videos · Documents · Data · And more" />}
        {!!files.length && <><section className="file-card"><div className="card-heading"><div><h2>Selected files</h2><p>{files.length} {files.length === 1 ? 'file' : 'files'} <span className="bullet">·</span> {sizeLabel(total)}</p></div><button className="text-button" onClick={() => setFiles([])} disabled={busy}>Clear all</button></div>{files.map((file, index) => <FileRow key={`${file.name}-${index}`} file={file} onRemove={() => setFiles(current => current.filter((_, i) => i !== index))} />)}<label className="add-more">+ Add more files<input type="file" multiple onChange={e => { addFiles(Array.from(e.target.files || [])); e.target.value = ''; }} /></label></section>
          <button className="button primary full" onClick={doCompress} disabled={busy}>{busy ? <><span className="spinner" /> Creating your Skyso file…</> : 'Create .sky'}</button>
        </>}
      </> : <>
        <h1>Restore a Skyso file</h1><p className="intro">Upload a <code>.sky</code> container to inspect and recover your original files.</p>
        {!inspection && <DropZone accept=".sky,application/octet-stream" multiple={false} onFiles={inspect} disabled={busy} title="Drop .sky file here" subtitle="Your container is checked before anything is restored" />}
        {inspection && <section className="file-card"><div className="card-heading"><div><h2>Skyso container</h2><p>{inspection.file_count} {inspection.file_count === 1 ? 'file' : 'files'} <span className="bullet">·</span> {sizeLabel(inspection.container_size)}</p></div><button className="text-button" onClick={() => { setInspection(null); setSky(null); setDownload(null); setError(''); setSuccess(''); }}>Choose another</button></div><div className="integrity"><span className="check">✓</span><span><strong>Container valid</strong><small>Manifest and container integrity verified</small></span></div><div className="contents-label">CONTENTS <span>{inspection.file_count}</span></div>{inspection.files.map((file, index) => <FileRow key={`${file.name}-${index}`} file={file} selected={selected.includes(file.name)} onSelect={checked => setSelected(current => checked ? [...current, file.name] : current.filter(name => name !== file.name))} />)}<div className="restore-actions"><button className="button primary" onClick={() => doRestore(false)} disabled={busy || !selected.length}>{busy ? <><span className="spinner" /> Restoring…</> : 'Restore selected'}</button><button className="button secondary" onClick={() => doRestore(true)} disabled={busy}>Restore all</button></div></section>}
      </>}
      {busy && <div className="live-status" role="status"><span className="spinner" />{tab === 'compress' ? `Processing ${files.length} ${files.length === 1 ? 'file' : 'files'} and building your container…` : 'Checking container and verifying file contents…'}</div>}
      {error && <div className="notice error" role="alert"><span>!</span>{error}</div>}
      {success && <div className="notice success" role="status"><span>✓</span><div>{success}{download && <a className="download-link" href={download.url} download={download.name}>{download.label}<span>↓</span></a>}</div></div>}
      <footer><span><i className="lock">⌑</i> Files are processed in memory and aren’t stored.</span><span>Lossless by design <b>·</b> SHA-256 verified</span></footer>
    </section>
  </main>;
}

export default App;
