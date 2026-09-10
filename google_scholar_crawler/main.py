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


def write_results(author, output_directory):
    citedby = author.get('citedby')
    publications = author.get('publications')
    if isinstance(citedby, bool) or not isinstance(citedby, int) or citedby < 0:
        raise ValueError('citation data must contain a non-negative integer citedby')
    if not isinstance(publications, dict):
        raise ValueError('citation data must contain a publications mapping')

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
    for filename, payload in outputs.items():
        destination = output_directory / filename
        temporary = output_directory / f'.{filename}.tmp'
        with temporary.open('w', encoding='utf-8') as output_file:
            json.dump(payload, output_file, ensure_ascii=False)
        os.replace(temporary, destination)


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
    write_results(author, output_directory)
    print(
        f"Wrote {len(author['publications'])} publications and "
        f"{author['citedby']} total citations."
    )


if __name__ == '__main__':
    main()
