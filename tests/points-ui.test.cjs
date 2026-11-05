const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.join(__dirname, '..');
const pointsSource = fs.readFileSync(path.join(root, 'public/assets/points-preview.js'), 'utf8');
const examsSource = fs.readFileSync(path.join(root, 'public/assets/exams-preview.js'), 'utf8');
const index = JSON.parse(fs.readFileSync(path.join(root, 'public/data/exams-preview.json'), 'utf8'));

function node() {
  return {
    textContent: '', innerHTML: '', value: '', hidden: false, disabled: false,
    style: {}, dataset: {}, children: [], attributes: {},
    setAttribute(key, value) { this.attributes[key] = value; },
    insertAdjacentHTML(_position, html) { this.innerHTML += html; },
    replaceChildren(...items) { this.children = items; this.textContent = ''; },
    append(...items) { this.children.push(...items); },
    addEventListener() {},
    classList: { toggle() {} },
  };
}

function response(body, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}

function pointsHarness(fetchImpl) {
  const elements = new Map();
  const document = {
    listeners: new Map(),
    querySelector(selector) {
      if (!elements.has(selector)) elements.set(selector, node());
      return elements.get(selector);
    },
    querySelectorAll(selector) { return selector === '[data-points-login]' ? [this.querySelector(selector)] : []; },
    addEventListener(name, callback) { this.listeners.set(name, callback); },
  };
  const window = { addEventListener() {}, dispatchEvent() {} };
  vm.runInNewContext(pointsSource, { document, window, fetch: fetchImpl, console, Date, Intl, encodeURIComponent, Event });
  return { document, window, elements };
}

async function main() {
  const availableFiles = index.sets.flatMap((set) => set.files).filter((file) => file.githubUrl);
  const unlockedFile = availableFiles[0];
  const secondFile = availableFiles.find((file) => file.id !== unlockedFile?.id);
  assert.ok(unlockedFile && secondFile, 'test fixture contains at least two matched files');
  assert.doesNotMatch(pointsSource, /localStorage/);
  assert.doesNotMatch(examsSource, /localStorage|window\.open/);
  assert.doesNotMatch(examsSource, /data-exam-url/);

  const calls = [];
  const pointResponses = [response({
    signedIn: true, balance: 5, checkedInToday: false,
    events: [{ id: 'event-1', eventType: 'checkin', referenceId: null, delta: 5, createdAt: '2026-11-03T08:00:00.000Z' }],
  }), response({ awarded: 5, alreadyCheckedIn: false, balance: 10 }), response({
    signedIn: true, balance: 10, checkedInToday: true, events: [],
  })];
  const harness = pointsHarness(async (url, options = {}) => {
    calls.push({ url, options });
    return pointResponses.shift();
  });
  assert.equal(typeof harness.window.FudanPoints?.refresh, 'function', 'points UI exposes API refresh');
  await harness.window.FudanPoints.ready;
  assert.equal(calls[0].url, '/api/points');
  assert.equal(harness.elements.get('#points-balance-value').textContent, '5');
  await harness.window.FudanPoints.checkIn();
  assert.equal(calls[1].url, '/api/points/checkin');
  assert.equal(calls[1].options.method, 'POST');
  assert.equal(calls[1].options.body, '{}');
  assert.equal(harness.elements.get('#points-balance-value').textContent, '10');

  const signedOut = pointsHarness(async () => response({ signedIn: false }));
  await signedOut.window.FudanPoints.ready;
  assert.equal(signedOut.elements.get('[data-points-login]').hidden, false);

  const failedCheckinResponses = [response({ signedIn: true, balance: 0, checkedInToday: false, events: [] }), response({ error: 'points_service_unavailable' }, 503)];
  const errors = pointsHarness(async () => failedCheckinResponses.shift());
  await errors.window.FudanPoints.ready;
  await errors.window.FudanPoints.checkIn();
  assert.equal(errors.elements.get('#points-balance-value').textContent, '0');
  assert.match(errors.elements.get('#points-checkin-status').textContent, /失败|暂不可用/);

  const examCalls = [];
  const unlockResponses = [
    response({ url: unlockedFile.githubUrl, charged: 1, alreadyUnlocked: false, balance: 4 }),
    response({ url: unlockedFile.githubUrl, charged: 0, alreadyUnlocked: true, balance: 4 }),
    response({ error: 'insufficient_points', balance: 0 }, 402),
  ];
  const examElements = new Map();
  const examDocument = {
    querySelector(selector) {
      if (!examElements.has(selector)) examElements.set(selector, node());
      return examElements.get(selector);
    },
    addEventListener() {},
    createElement(tag) { const item = node(); item.tagName = tag.toUpperCase(); return item; },
  };
  const examWindow = { FudanPoints: { refresh: async () => {} } };
  vm.runInNewContext(examsSource, {
    document: examDocument, window: examWindow, console, URL, encodeURIComponent,
    fetch: async (url, options = {}) => {
      examCalls.push({ url, options });
      if (url === 'data/exams-preview.json') return response(index);
      return unlockResponses.shift();
    },
  });
  assert.equal(typeof examWindow.ExamPreview?.unlockFile, 'function', 'exam UI exposes per-file unlock action');
  await examWindow.ExamPreview.ready;
  const button = node();
  button.dataset.examFile = unlockedFile.id;
  const status = node();
  await examWindow.ExamPreview.unlockFile(button, status);
  const unlockCall = examCalls.find((call) => call.url.startsWith('/api/exams/'));
  assert.equal(unlockCall.url, `/api/exams/${encodeURIComponent(unlockedFile.id)}/unlock`);
  assert.equal(unlockCall.options.method, 'POST');
  assert.equal(unlockCall.options.body, '{}');
  assert.equal(status.children.at(-1).href, unlockedFile.githubUrl);
  assert.equal(examCalls.filter((call) => call.url.startsWith('/api/exams/')).length, 1);
  assert.equal(status.children.filter((child) => child.tagName === 'A').length, 1);

  await examWindow.ExamPreview.unlockFile(button, status);
  assert.match(status.textContent, /免费打开/);
  assert.equal(status.children.filter((child) => child.tagName === 'A').length, 1);
  assert.equal(examCalls.filter((call) => call.url === `/api/exams/${encodeURIComponent(unlockedFile.id)}/unlock`).length, 2);

  const insufficientButton = node();
  insufficientButton.dataset.examFile = secondFile.id;
  const insufficientStatus = node();
  await examWindow.ExamPreview.unlockFile(insufficientButton, insufficientStatus);
  assert.match(insufficientStatus.textContent, /积分不足/);
  assert.equal(insufficientStatus.children.filter((child) => child.tagName === 'A').length, 0);

  console.log(JSON.stringify({ checks: 20 }));
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
