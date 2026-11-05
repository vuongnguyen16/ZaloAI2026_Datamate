import assert from 'node:assert/strict';
import test from 'node:test';
import { parseExplainer } from '../explainer/parse.mjs';
import { renderExplainer } from '../explainer/render.mjs';
import { scanHtml } from '../explainer/check.mjs';

for (const [language, title, summary, panel, body] of [
  ['English', 'Start here', 'The data loader is ready.', 'Next step', 'Read the source before editing.'],
  ['Vietnamese', 'Bắt đầu tại đây', 'Bộ nạp dữ liệu đã sẵn sàng.', 'Bước tiếp theo', 'Đọc source trước khi sửa.'],
]) {
  test(`${language} explainer without locale keeps its copy and uses English controls`, () => {
    const draft = `# ${title}\n\n${summary}\n\n## ${panel}\n\n${body}\n`;
    const parsed = parseExplainer(draft, { inputPath: 'synthetic.archify.md', output: 'synthetic.html' });
    assert.ok(parsed.document, 'Synthetic draft must parse');
    const html = renderExplainer(parsed.document);
    const scanned = scanHtml(html);
    assert.equal(scanned.elements.find(element => element.tag === 'html').attrs.lang, 'en');
    const words = JSON.parse(scanned.scripts.find(script => script.attrs.id === 'explainer-reader-words').text);
    assert.equal(words.export, 'Export');
    assert.equal(words.sources, 'Sources');
    assert.equal(words.askCopy, 'Copy question');
    assert.ok(html.includes(title) && html.includes(body), 'Authored copy must survive rendering');
    const markup = html.replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1>/gi, '');
    assert.equal(/\p{Script=Han}/u.test(markup), false, 'Rendered markup must contain no Chinese text');
  });
}
