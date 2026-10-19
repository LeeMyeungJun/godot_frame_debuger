// Exercise the standalone viewer without browser permissions or a live GPU.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const path = require('path');
const root = path.resolve(__dirname, '..');
if (!process.argv[2]) {
  console.error('Usage: node tests/viewer_smoke.cjs <exported-frame.html>');
  process.exit(1);
}
const captureHtml = fs.readFileSync(path.resolve(root, process.argv[2]), 'utf8');
const capture = JSON.parse(captureHtml.match(/<script id="frame-data" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const html = fs.readFileSync(path.join(root, 'frame_viewer_template.html'), 'utf8');
const source = html.match(/<script>\s*([\s\S]*?)<\/script>/)[1].replace('__ASSET_PREFIX__', JSON.stringify('assets/'));
function run(data) {
  class Element {
    constructor() {
      this.children = []; this.listeners = {}; this.className = ''; this.value = '';
      this.classList = { toggle: (name, active) => {
        const classes = new Set(this.className.split(' ').filter(Boolean));
        if (active) classes.add(name); else classes.delete(name);
        this.className = [...classes].join(' ');
      }};
    }
    replaceChildren() { this.children = []; }
    appendChild(child) { this.children.push(child); return child; }
    setAttribute(name, value) { this[name] = value; }
    addEventListener(name, callback) { this.listeners[name] = callback; }
    querySelector() { return this.children.find(c => c.className.split(' ').includes('active')); }
    scrollIntoView() {}
  }
  const elements = new Map();
  const get = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  get('frame-data').textContent = JSON.stringify(data);
  const handlers = {};
  const document = { getElementById: get, createElement: () => new Element(), addEventListener: (name, fn) => handlers[name] = fn };
  class Image { set src(url) { this.url = url; if (this.onload) this.onload(); } }
  vm.runInNewContext(source, { document, Image, console });
  const key = (name, editing = false) => {
    let prevented = false;
    handlers.keydown({ key: name, target: { closest: () => editing }, preventDefault: () => prevented = true });
    return prevented;
  };
  return { get, key };
}
const { get, key } = run(capture);
assert.match(get('progress').textContent, /^Draw 1 \/ /);
assert.equal(key('ArrowRight'), true);
assert.match(get('progress').textContent, /^Draw 2 \/ /);
assert.equal(key('ArrowLeft'), true);
assert.equal(get('prev').disabled, true);
key('ArrowLeft'); assert.equal(get('draw-number').value, 1);
key('End'); assert.equal(get('next').disabled, true);
assert.equal(get('draw-number').value, capture.draws.length);
key('ArrowDown'); assert.equal(get('draw-number').value, capture.draws.length);
key('Home'); assert.equal(get('draw-number').value, 1);
key('ArrowRight', true); assert.equal(get('draw-number').value, 1);
get('draw-number').listeners.change({ target: { value: '50' } });
assert.equal(get('draw-number').value, Math.min(50, capture.draws.length));
get('timeline').listeners.input({ target: { value: '3' } });
assert.equal(get('draw-number').value, 3);
get('before').onclick(); assert.equal(get('before')['aria-pressed'], 'true');
if (capture.draws[2].targets?.length) assert.match(get('screen-image').src, /_before\.png$/);
get('after').onclick(); assert.equal(get('after')['aria-pressed'], 'true');
if (capture.draws[2].targets?.length) assert.match(get('screen-image').src, /_after\.png$/);
run({ ...capture, draw_count: 0, draws: [] });
run({ ...capture, draw_count: 1, draws: [{ ...capture.draws[0], targets: [], textures: [] }] });
const multi = run({ ...capture, draw_count: 1, draws: [{ ...capture.draws[0], targets: [
  { slot: 0, id: '10', width: 16, height: 16, image: 'a.png', before: 'b.png' },
  { slot: 1, id: '20', width: 16, height: 16, image: 'c.png', before: 'd.png' }
] }] });
multi.get('target-select').onchange({ target: { value: '1' } });
assert.equal(multi.get('screen-image').src, 'assets/c.png');
console.log('PASS: keyboard navigation, bounds, input focus, jump, slider, before/after, empty captures, missing targets, multiple outputs');
