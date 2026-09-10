import json
from datetime import datetime, timezone
import os
from pathlib import Path
from scholarly import scholarly


def fetch_author(scholar_id, scholarly_client=None, updated_at=None):
    updated_at = updated_at or datetime.now(timezone.utc).isoformat()
    scholarly_client = scholarly_client or scholarly
    scholarly_client.set_timeout(10)
    scholarly_client.set_retries(2)
    author = scholarly_client.search_author_id(scholar_id)
    scholarly_client.fill(
        author,
        sections=['basics', 'indices', 'counts', 'publications'],
    )
    author['updated'] = updated_at
    author['publications'] = {
        publication['author_pub_id']: publication
        for publication in author['publications']
    }
    return author


def write_results(author, output_directory, expected_scholar_id=None):
    citedby = author.get('citedby')
    publications = author.get('publications')
    if expected_scholar_id and author.get('scholar_id') != expected_scholar_id:
        raise ValueError('citation data belongs to an unexpected scholar profile')
    if isinstance(citedby, bool) or not isinstance(citedby, int) or citedby < 0:
        raise ValueError('citation data must contain a non-negative integer citedby')
    if not isinstance(publications, dict) or not publications:
        raise ValueError('citation data must contain at least one publication')
    for publication_id, publication in publications.items():
        publication_citations = publication.get('num_citations')
        if publication.get('author_pub_id') != publication_id:
            raise ValueError('publication key does not match author_pub_id')
        if (
            isinstance(publication_citations, bool)
            or not isinstance(publication_citations, int)
            or publication_citations < 0
        ):
            raise ValueError('publication citation counts must be non-negative integers')

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    outputs = {
        'gs_data.json': author,
        'gs_data_shieldsio.json': {
            'schemaVersion': 1,
            'label': 'citations',
            'message': str(citedby),
        },
    }
    serialized_outputs = {
        filename: json.dumps(payload, ensure_ascii=False)
        for filename, payload in outputs.items()
    }
    temporary_paths = []
    try:
        for filename, contents in serialized_outputs.items():
            temporary = output_directory / f'.{filename}.tmp'
            temporary.write_text(contents, encoding='utf-8')
            temporary_paths.append(temporary)
        for filename in serialized_outputs:
            os.replace(
                output_directory / f'.{filename}.tmp',
                output_directory / filename,
            )
    finally:
        for temporary in temporary_paths:
            temporary.unlink(missing_ok=True)


def main():
    scholar_id = os.environ.get('GOOGLE_SCHOLAR_ID')
    if not scholar_id:
        raise RuntimeError('GOOGLE_SCHOLAR_ID is required')
    print('Fetching citation data from Google Scholar...')
    author = fetch_author(scholar_id)
    output_directory = os.environ.get(
        'CITATION_OUTPUT_DIR',
        Path(__file__).resolve().parent / 'results',
    )
    write_results(author, output_directory, expected_scholar_id=scholar_id)
    print(
        f"Wrote {len(author['publications'])} publications and "
        f"{author['citedby']} total citations."
    )


if __name__ == '__main__':
    main()
