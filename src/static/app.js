// Data Insights frontend — vanilla JS, fetch + manual SSE parsing.
const $ = (s) => document.querySelector(s);
const thread = $('#thread');
const form = $('#composer');
const fileInput = $('#file');
const fileChip = $('#filechip');
const fileChipName = $('#filechip-name');
const fileChipX = $('#filechip-x');
const q = $('#q');
const send = $('#send');

let attachedFile = null;
let busy = false;

function updateSendState() {
  send.disabled = busy || !q.value.trim() || !attachedFile;
}

q.addEventListener('input', () => {
  q.style.height = 'auto';
  q.style.height = Math.min(q.scrollHeight, 220) + 'px';
  updateSendState();
});

q.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!send.disabled) form.requestSubmit();
  }
});

fileInput.addEventListener('change', () => {
  if (fileInput.files && fileInput.files[0]) {
    attachedFile = fileInput.files[0];
    fileChipName.textContent = attachedFile.name;
    fileChip.classList.remove('hidden');
  }
  updateSendState();
});

fileChipX.addEventListener('click', () => {
  attachedFile = null;
  fileInput.value = '';
  fileChip.classList.add('hidden');
  updateSendState();
});

function clearWelcome() {
  const w = $('.welcome');
  if (w) w.remove();
}

function addUserMessage(text, fileName) {
  clearWelcome();
  const msg = document.createElement('div');
  msg.className = 'msg user';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  if (fileName) {
    const tag = document.createElement('div');
    tag.className = 'filetag';
    tag.textContent = '📎 ' + fileName;
    bubble.appendChild(tag);
  }
  const tx = document.createElement('div');
  tx.textContent = text;
  bubble.appendChild(tx);
  msg.appendChild(bubble);
  thread.appendChild(msg);
  scrollBottom();
}

function addAssistantMessage() {
  const msg = document.createElement('div');
  msg.className = 'msg assistant';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';

  const subtitle = document.createElement('p');
  subtitle.className = 'subtitle';
  subtitle.textContent = 'Loading data…';
  bubble.appendChild(subtitle);

  const reasoning = document.createElement('details');
  reasoning.className = 'reasoning';
  const summary = document.createElement('summary');
  summary.textContent = 'Show reasoning';
  const rbody = document.createElement('div');
  rbody.className = 'reasoning-body';
  reasoning.appendChild(summary);
  reasoning.appendChild(rbody);
  bubble.appendChild(reasoning);

  const charts = document.createElement('div');
  charts.className = 'charts';
  bubble.appendChild(charts);

  const narration = document.createElement('div');
  narration.className = 'narration';
  bubble.appendChild(narration);

  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  narration.appendChild(cursor);

  msg.appendChild(bubble);
  thread.appendChild(msg);
  scrollBottom();
  return { msg, subtitle, reasoning, rbody, charts, narration, cursor, raw: '' };
}

function reasoningBlock(title, content) {
  const block = document.createElement('div');
  block.className = 'block';
  const h = document.createElement('h4');
  h.textContent = title;
  block.appendChild(h);
  const pre = document.createElement('pre');
  pre.textContent = typeof content === 'string' ? content : JSON.stringify(content, null, 2);
  block.appendChild(pre);
  return block;
}

function renderChart(charts, payload) {
  const wrap = document.createElement('div');
  wrap.className = 'chart';
  wrap.dataset.chartId = payload.chart_id;
  const img = document.createElement('img');
  img.src = `data:${payload.mime || 'image/png'};base64,${payload.base64}`;
  img.alt = payload.caption || '';
  const cap = document.createElement('div');
  cap.className = 'cap';
  cap.textContent = payload.caption || '';
  wrap.appendChild(img);
  wrap.appendChild(cap);
  charts.appendChild(wrap);
  scrollBottom();
}

function scrollBottom() {
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}

async function streamRun(file, question, ctx) {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('question', question);
  const resp = await fetch('/analyze', { method: 'POST', body: fd });
  if (!resp.ok || !resp.body) {
    ctx.subtitle.textContent = 'Error: ' + resp.status;
    ctx.cursor.remove();
    return;
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf('\n\n')) !== -1) {
      const block = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      handleSSE(block, ctx);
    }
  }
  ctx.cursor.remove();
}

function handleSSE(block, ctx) {
  let event = 'message';
  const dataLines = [];
  for (const line of block.split('\n')) {
    if (line.startsWith('event: ')) event = line.slice(7).trim();
    else if (line.startsWith('data: ')) dataLines.push(line.slice(6));
  }
  const data = dataLines.join('\n');
  if (event === 'token') {
    ctx.raw += data;
    ctx.narration.innerHTML = marked.parse(ctx.raw) + '<span class="cursor"></span>';
    ctx.cursor = ctx.narration.querySelector('.cursor');
    scrollBottom();
    return;
  }
  let payload;
  try { payload = JSON.parse(data); } catch { payload = data; }

  switch (event) {
    case 'profile':
      ctx.subtitle.textContent = `Loaded ${payload.rows.toLocaleString()} rows × ${payload.cols} columns from ${payload.file_name}`;
      ctx.rbody.appendChild(reasoningBlock('Dataset profile', payload));
      break;
    case 'plan_draft':
      ctx.rbody.appendChild(reasoningBlock('Plan — draft (Claude)', payload));
      ctx.subtitle.textContent = 'Reviewing plan…';
      break;
    case 'plan_critique':
      ctx.rbody.appendChild(reasoningBlock(`Plan critique r${payload.round} (GPT)`, payload));
      ctx.subtitle.textContent = payload.approve_as_is ? 'Plan approved. Executing…' : 'Refining plan…';
      break;
    case 'plan_final':
      ctx.rbody.appendChild(reasoningBlock('Plan — final', payload));
      ctx.subtitle.textContent = 'Executing analysis…';
      break;
    case 'chart_draft':
    case 'chart':
      // De-dupe: if a chart with this id already exists, skip
      if (!ctx.charts.querySelector(`[data-chart-id="${payload.chart_id}"]`)) {
        renderChart(ctx.charts, payload);
      }
      break;
    case 'finding_draft':
    case 'finding':
      ctx.rbody.appendChild(reasoningBlock(`Finding ${payload.id || ''} (${event})`, payload));
      break;
    case 'output_critique':
      ctx.rbody.appendChild(reasoningBlock(`Output critique r${payload.round} (GPT)`, payload));
      ctx.subtitle.textContent = payload.approve_as_is ? 'Output approved. Writing…' : 'Refining output…';
      break;
    case 'done':
      if (payload.error) {
        ctx.subtitle.textContent = 'Error: ' + payload.error;
      } else {
        ctx.subtitle.textContent = `Done · ${payload.n_findings} findings · ${payload.n_charts} charts`;
      }
      break;
  }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (busy || !attachedFile || !q.value.trim()) return;
  busy = true;
  send.disabled = true;
  const file = attachedFile;
  const question = q.value.trim();
  addUserMessage(question, file.name);
  q.value = '';
  q.style.height = 'auto';
  // Keep file attached so user can ask follow-ups about same data without re-attaching.
  const ctx = addAssistantMessage();
  try {
    await streamRun(file, question, ctx);
  } catch (err) {
    ctx.subtitle.textContent = 'Error: ' + err.message;
  } finally {
    busy = false;
    updateSendState();
  }
});
