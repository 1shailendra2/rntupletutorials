/* ─────────────────────────────────────────────────────
   app.js  –  Voice Inventory Demo
   ───────────────────────────────────────────────────── */

const API = 'http://localhost:8000';

// ── State ─────────────────────────────────────────────
let accessToken   = '';
let mediaRecorder = null;
let recordChunks  = [];
let recordedBlob  = null;
let uploadedFile  = null;
let timerInterval = null;
let seconds       = 0;
let currentTab    = 'rec';

// ── Login ─────────────────────────────────────────────
async function doLogin() {
  const email    = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;
  const msgEl    = document.getElementById('loginMsg');

  if (!email || !password) { showMsg(msgEl, 'err', 'Please fill in both fields.'); return; }

  try {
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();

    if (!res.ok) {
      showMsg(msgEl, 'err', `Login failed: ${data.detail || res.statusText}`);
      return;
    }

    accessToken = data.access_token;
    showMsg(msgEl, 'ok', `✅ Logged in as ${email}`);
  } catch (e) {
    showMsg(msgEl, 'err', `Network error: ${e.message}`);
  }
}

// ── Tab switch ────────────────────────────────────────
function switchTab(tab) {
  currentTab = tab;
  document.getElementById('pRec').classList.toggle('hidden',    tab !== 'rec');
  document.getElementById('pUpload').classList.toggle('hidden', tab !== 'upload');
  document.getElementById('tRec').classList.toggle('active',    tab === 'rec');
  document.getElementById('tUpload').classList.toggle('active', tab === 'upload');
}

// ── File Upload ───────────────────────────────────────
function onFile(input) {
  if (!input.files.length) return;
  uploadedFile = input.files[0];
  document.getElementById('dropText').textContent = `✅ ${uploadedFile.name}`;
}

// ── Recording ─────────────────────────────────────────
async function toggleRecord() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    stopRecording();
  } else {
    startRecording();
  }
}

async function startRecording() {
  if (!navigator.mediaDevices) {
    alert('Your browser does not support audio recording. Try Chrome or Firefox.');
    return;
  }

  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (e) {
    alert('Microphone access denied – please allow it and try again.');
    return;
  }

  recordChunks  = [];
  recordedBlob  = null;
  mediaRecorder = new MediaRecorder(stream);

  mediaRecorder.ondataavailable = e => { if (e.data && e.data.size > 0) recordChunks.push(e.data); };
  mediaRecorder.onstop = () => {
    const mimeType = mediaRecorder.mimeType || 'audio/webm';
    recordedBlob = new Blob(recordChunks, { type: mimeType });
    console.log("Recorded blob size:", recordedBlob.size, "bytes, type:", mimeType);
    
    if (recordedBlob.size === 0) {
        alert("Recording failed (0 bytes). Check your microphone.");
    }
    
    const url = URL.createObjectURL(recordedBlob);
    const audio = document.getElementById('recAudio');
    audio.src = url;
    audio.classList.remove('hidden');
    stream.getTracks().forEach(t => t.stop());
  };

  mediaRecorder.start();

  // UI
  const btn = document.getElementById('recBtn');
  btn.textContent = '⏹ Stop Recording';
  btn.classList.add('recording');
  document.getElementById('recTimer').classList.remove('hidden');
  seconds = 0;
  document.getElementById('timerVal').textContent = 0;
  timerInterval = setInterval(() => {
    seconds++;
    document.getElementById('timerVal').textContent = seconds;
  }, 1000);
}

function stopRecording() {
  if (mediaRecorder) mediaRecorder.stop();
  clearInterval(timerInterval);
  const btn = document.getElementById('recBtn');
  btn.textContent = '⏺ Start Recording';
  btn.classList.remove('recording');
  document.getElementById('recTimer').classList.add('hidden');
}

// ── Send to API ───────────────────────────────────────
async function sendAudio() {
  if (!accessToken) { alert('Please login first (Step 1).'); return; }

  // pick audio source
  let audioFile = null;
  if (currentTab === 'rec') {
    if (!recordedBlob) { alert('Please record something first.'); return; }
    const ext = recordedBlob.type.includes('mp4') ? 'mp4' : (recordedBlob.type.includes('ogg') ? 'ogg' : 'webm');
    audioFile = new File([recordedBlob], `recording.${ext}`, { type: recordedBlob.type });
  } else {
    if (!uploadedFile) { alert('Please choose an audio file first.'); return; }
    audioFile = uploadedFile;
  }

  const lang = document.getElementById('lang').value;
  const url  = new URL(`${API}/transactions/voice`);
  if (lang) url.searchParams.set('language', lang);

  const form = new FormData();
  form.append('file', audioFile, audioFile.name);

  // loading state
  document.getElementById('spinner').classList.remove('hidden');
  document.getElementById('results').classList.add('hidden');
  document.getElementById('errBox').classList.add('hidden');

  try {
    const res  = await fetch(url.toString(), {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${accessToken}` },
      body: form,
    });
    const data = await res.json();

    document.getElementById('spinner').classList.add('hidden');

    if (!res.ok) {
      showError(data.detail || JSON.stringify(data));
      return;
    }

    // populate result cards
    document.getElementById('rTranscript').textContent =
      data.transcript || '–';
    document.getElementById('rExtracted').textContent =
      JSON.stringify(data.extracted, null, 2);
    document.getElementById('rProduct').textContent =
      data.product ? formatProduct(data.product) : '–';
    document.getElementById('rTx').textContent =
      data.transaction ? formatTx(data.transaction) : '–';

    // alert badge
    document.getElementById('alertBadge').classList.toggle('hidden', !data.alert_sent);

    document.getElementById('results').classList.remove('hidden');

  } catch (e) {
    document.getElementById('spinner').classList.add('hidden');
    showError(`Network error: ${e.message}`);
  }
}

// ── Helpers ───────────────────────────────────────────
function formatProduct(p) {
  return [
    `Name:      ${p.name}`,
    `Quantity:  ${p.quantity}`,
    `Price:     $${p.price}`,
    `Threshold: ${p.threshold}`,
    `Status:    ${p.status}`,
  ].join('\n');
}

function formatTx(t) {
  return [
    `Action:   ${t.action}`,
    `Quantity: ${t.quantity}`,
    `Price:    $${t.price}`,
    `Created:  ${new Date(t.created_at).toLocaleString()}`,
  ].join('\n');
}

function showMsg(el, type, text) {
  el.textContent = text;
  el.className   = `msg ${type}`;
  el.classList.remove('hidden');
}

function showError(msg) {
  const box = document.getElementById('errBox');
  box.textContent = msg;
  box.classList.remove('hidden');
  document.getElementById('results').classList.remove('hidden');
}
