const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

async function responseError(response) {
  try { const body = await response.json(); return body.detail || 'The request could not be completed.'; }
  catch { return 'The request could not be completed.'; }
}

export async function compressFiles(files) {
  const body = new FormData();
  files.forEach(file => body.append('files[]', file, file.name));
  const response = await fetch(`${API}/compress`, { method: 'POST', body });
  if (!response.ok) throw new Error(await responseError(response));
  return response.blob();
}

export async function inspectSky(file) {
  const body = new FormData(); body.append('sky', file, file.name);
  const response = await fetch(`${API}/inspect`, { method: 'POST', body });
  if (!response.ok) throw new Error(await responseError(response));
  return response.json();
}

export async function restoreSky(file, selected) {
  const body = new FormData(); body.append('sky', file, file.name);
  if (selected) body.append('selected', JSON.stringify(selected));
  const response = await fetch(`${API}/decompress`, { method: 'POST', body });
  if (!response.ok) throw new Error(await responseError(response));
  return { blob: await response.blob(), disposition: response.headers.get('content-disposition') || '' };
}
