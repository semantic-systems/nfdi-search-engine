"""Template tests for publication details provenance modal."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.modules.setdefault("opentelemetry", MagicMock())
sys.modules.setdefault("opentelemetry.trace", MagicMock())

from flask import Flask

from nfdi_search_engine.common.models.search_result import ProvenanceDisplayRow
from nfdi_search_engine.web.filters import register_filters

TEMPLATES = str(Path(__file__).resolve().parents[1] / "templates")


class TestPublicationDetailsProvenanceTemplate:
    def test_provenance_modal_renders_table_rows(self):
        app = Flask(__name__, template_folder=TEMPLATES)
        register_filters(app)

        template = app.jinja_env.from_string(
            "{% from 'partials/publication-details/provenance-modal.html' import provenanceModal %}"
            "{% if provenance_rows %}"
            "<div id='provenance_block'>"
            "<button id='btn-view-provenance' data-bs-toggle='modal' "
            "data-bs-target='#publication-provenance-modal'>View</button>"
            "</div>"
            "{{ provenanceModal('publication-provenance-modal', provenance_rows) }}"
            "{% endif %}"
        )
        rows = [
            ProvenanceDisplayRow(
                field="Title",
                value="Machine Learning Approaches",
                sources="OPENALEX - Publications, CROSSREF - Publications",
            ),
            ProvenanceDisplayRow(
                field="Keywords",
                value="AI, NLP",
                sources="OPENALEX - Publications",
            ),
        ]

        with app.app_context():
            html = template.render(provenance_rows=rows)

        assert "provenance_block" in html
        assert "btn-view-provenance" in html
        assert "publication-provenance-modal" in html
        assert "Machine Learning Approaches" in html
        assert "OPENALEX - Publications, CROSSREF - Publications" in html
        assert "AI, NLP" in html

    def test_provenance_section_hidden_when_rows_missing(self):
        app = Flask(__name__, template_folder=TEMPLATES)
        template = app.jinja_env.from_string(
            "{% from 'partials/publication-details/provenance-modal.html' import provenanceModal %}"
            "{% if provenance_rows %}"
            "<div id='provenance_block'></div>"
            "{{ provenanceModal('publication-provenance-modal', provenance_rows) }}"
            "{% endif %}"
        )

        with app.app_context():
            html = template.render(provenance_rows=[])

        assert 'id="provenance_block"' not in html
        assert 'id="publication-provenance-modal"' not in html
