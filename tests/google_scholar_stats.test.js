const test = require('node:test');
const assert = require('node:assert/strict');

const {
  loadGoogleScholarStats,
  renderGoogleScholarStats,
} = require('../assets/js/google-scholar-stats.js');


function makeDocument({ includeTotal = true } = {}) {
  const total = includeTotal ? { textContent: '—' } : null;
  const papers = [
    {
      dataset: { paperId: 'author:known-paper' },
      hidden: true,
      textContent: '',
    },
    {
      dataset: { paperId: 'author:missing-paper' },
      hidden: true,
      textContent: '',
    },
  ];

  return {
    total,
    papers,
    getElementById(id) {
      return id === 'total_cit' ? total : null;
    },
    querySelectorAll(selector) {
      assert.equal(selector, '.show_paper_citations');
      return papers;
    },
  };
}


test('renders total citations and only publications present in Scholar data', () => {
  const document = makeDocument();

  renderGoogleScholarStats(
    {
      citedby: 70,
      publications: {
        'author:known-paper': { num_citations: 23 },
      },
    },
    document,
  );

  assert.equal(document.total.textContent, '70');
  assert.equal(document.papers[0].textContent, '| Citations: 23');
  assert.equal(document.papers[0].hidden, false);
  assert.equal(document.papers[1].textContent, '');
  assert.equal(document.papers[1].hidden, true);
});


test('renders publication citations even when a page has no total counter', () => {
  const document = makeDocument({ includeTotal: false });

  assert.doesNotThrow(() => {
    renderGoogleScholarStats(
      {
        citedby: 70,
        publications: {
          'author:known-paper': { num_citations: 0 },
        },
      },
      document,
    );
  });
  assert.equal(document.papers[0].textContent, '| Citations: 0');
  assert.equal(document.papers[0].hidden, false);
});


test('keeps placeholders intact when citation data cannot be loaded', async () => {
  const document = makeDocument();
  const warnings = [];

  const loaded = await loadGoogleScholarStats(
    'https://example.test/gs_data.json',
    document,
    async () => ({ ok: false, status: 503 }),
    { warn: (message) => warnings.push(message) },
  );

  assert.equal(loaded, false);
  assert.equal(document.total.textContent, '—');
  assert.equal(document.papers[0].hidden, true);
  assert.equal(warnings.length, 1);
});
