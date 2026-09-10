(function (root) {
  'use strict';

  function isCitationCount(value) {
    return Number.isInteger(value) && value >= 0;
  }

  function renderGoogleScholarStats(data, documentRef) {
    if (!data || !documentRef) {
      return;
    }

    var totalCitationElement = documentRef.getElementById('total_cit');
    if (totalCitationElement && isCitationCount(data.citedby)) {
      totalCitationElement.textContent = String(data.citedby);
    }

    var publications = data.publications || {};
    var citationElements = documentRef.querySelectorAll('.show_paper_citations');
    Array.prototype.forEach.call(citationElements, function (element) {
      var publication = publications[element.dataset.paperId];
      if (!publication || !isCitationCount(publication.num_citations)) {
        return;
      }

      element.textContent = '| Citations: ' + publication.num_citations;
      element.hidden = false;
    });
  }

  async function loadGoogleScholarStats(dataUrl, documentRef, fetchImpl, logger) {
    documentRef = documentRef || root.document;
    fetchImpl = fetchImpl || root.fetch.bind(root);
    logger = logger || root.console;

    try {
      var response = await fetchImpl(dataUrl, { cache: 'no-store' });
      if (!response.ok) {
        throw new Error('citation data request returned HTTP ' + response.status);
      }
      var data = await response.json();
      renderGoogleScholarStats(data, documentRef);
      return true;
    } catch (error) {
      logger.warn('Could not load Google Scholar citation data.', error);
      return false;
    }
  }

  var api = {
    loadGoogleScholarStats: loadGoogleScholarStats,
    renderGoogleScholarStats: renderGoogleScholarStats,
  };

  root.GoogleScholarStats = api;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
}(typeof window !== 'undefined' ? window : globalThis));
