from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, TypedDict, cast
from html import unescape
from html.parser import HTMLParser

import httpx
from core.disease_facts import get_disease_facts


NCBI_EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DEFAULT_GENE_SEARCH_LIMIT = 8
DISEASE_CACHE_PATH = Path(__file__).resolve().parent.parent / "database" / "disease_cache.json"
DISEASE_CACHE_TTL_SECONDS = 60 * 60 * 24
DISEASE_CACHE_SCHEMA_VERSION = 2
MEDLINEPLUS_CONNECT_BASE = "https://connect.medlineplus.gov/service"
MEDGEN_BASE = "https://www.ncbi.nlm.nih.gov/medgen/"


class DiseaseGeneRecord(TypedDict):
    disease: str
    description: str
    genes: List[str]


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self) -> str:
        return " ".join(self.parts)


DISEASE_GENE_DB: List[DiseaseGeneRecord] = [
    {
        "disease": "Breast Cancer",
        "description": "A cancer that develops in breast tissue and may be linked to inherited mutations.",
        "genes": ["BRCA1", "BRCA2", "TP53", "PALB2"],
    },
    {
        "disease": "Sickle Cell Anemia",
        "description": "A hereditary blood disorder caused by a mutation affecting hemoglobin structure.",
        "genes": ["HBB"],
    },
    {
        "disease": "Cystic Fibrosis",
        "description": "An inherited disorder that affects mucus-producing glands, especially in lungs and pancreas.",
        "genes": ["CFTR"],
    },
    {
        "disease": "Parkinson Disease",
        "description": "A neurodegenerative disorder associated with both genetic and environmental factors.",
        "genes": ["SNCA", "LRRK2", "PINK1", "PARK7"],
    },
    {
        "disease": "Alzheimer Disease",
        "description": "A progressive neurological disorder that impairs memory and cognition.",
        "genes": ["APOE", "APP", "PSEN1", "PSEN2"],
    },
]


def get_ncbi_common_params() -> Dict[str, str]:
    params = {
        "retmode": "json",
        "tool": "bioinformatics_explorer",
        "email": os.getenv("NCBI_EMAIL", "student@example.com"),
    }
    api_key = os.getenv("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    return params


def looks_like_gene_symbol(query: str) -> bool:
    stripped = query.strip()
    return bool(stripped) and " " not in stripped and len(stripped) <= 15


def ncbi_esearch(term: str, limit: int, database: str = "gene") -> List[str]:
    params = {
        **get_ncbi_common_params(),
        "db": database,
        "term": term,
        "retmax": str(limit),
    }
    response = httpx.get(f"{NCBI_EUTILS_BASE}/esearch.fcgi", params=params, timeout=25.0)
    response.raise_for_status()
    data = cast(Dict[str, Any], response.json())
    return cast(List[str], data.get("esearchresult", {}).get("idlist", []))


def search_local_disease_gene(query: str) -> List[Dict[str, Any]]:
    normalized = query.strip().lower()
    if not normalized:
        raise ValueError("Search query cannot be empty.")

    results: List[Dict[str, Any]] = []
    for item in DISEASE_GENE_DB:
        matched_by: List[str] = []
        if normalized in item["disease"].lower():
            matched_by.append("disease")
        if normalized in item["description"].lower():
            matched_by.append("description")
        if any(normalized in gene.lower() for gene in item["genes"]):
            matched_by.append("gene")
        if matched_by:
            results.append(
                {
                    "disease": item["disease"],
                    "description": item["description"],
                    "genes": item["genes"],
                    "matched_by": matched_by,
                }
            )
    return results


def load_disease_cache() -> Dict[str, Any]:
    if not DISEASE_CACHE_PATH.exists():
        return {}
    try:
        return cast(Dict[str, Any], json.loads(DISEASE_CACHE_PATH.read_text(encoding="utf-8")))
    except Exception:
        return {}


def save_disease_cache(cache: Dict[str, Any]) -> None:
    DISEASE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DISEASE_CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def strip_html_text(value: str) -> str:
    if not value:
        return ""
    stripper = _HTMLStripper()
    stripper.feed(value)
    clean_text = unescape(stripper.get_text())
    return re.sub(r"\s+", " ", clean_text).strip()


def split_summary_sentences(text: str) -> List[str]:
    if not text:
        return []
    chunks = re.split(r"(?<=[.!?])\s+", text.strip())
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def extract_clinical_sections(summary_text: str, fallback: Dict[str, Any]) -> Dict[str, List[str]]:
    fallback_symptoms = cast(List[str], fallback.get("symptoms", []))
    fallback_precautions = cast(List[str], fallback.get("precautions", []))
    fallback_treatment = cast(List[str], fallback.get("treatment", []))

    symptom_terms = ("symptom", "sign", "pain", "fever", "cough", "fatigue", "swelling", "weakness", "memory")
    precaution_terms = ("prevent", "avoid", "monitor", "screen", "vaccin", "follow", "hygiene", "exercise", "diet")
    treatment_terms = ("treat", "therapy", "medicine", "drug", "surgery", "transplant", "management", "care")

    symptoms: List[str] = []
    precautions: List[str] = []
    treatment: List[str] = []

    for sentence in split_summary_sentences(summary_text):
        lowered = sentence.lower()
        if any(term in lowered for term in symptom_terms):
            symptoms.append(sentence)
        if any(term in lowered for term in precaution_terms):
            precautions.append(sentence)
        if any(term in lowered for term in treatment_terms):
            treatment.append(sentence)

    return {
        "symptoms": symptoms or fallback_symptoms,
        "precautions": precautions or fallback_precautions,
        "treatment": treatment or fallback_treatment,
    }


def is_cache_entry_fresh(entry: Dict[str, Any]) -> bool:
    if entry.get("schema_version") != DISEASE_CACHE_SCHEMA_VERSION:
        return False
    cached_at = entry.get("cached_at")
    if not isinstance(cached_at, (int, float)):
        return False
    return (time.time() - float(cached_at)) < DISEASE_CACHE_TTL_SECONDS


def fetch_medgen_ids(query: str, limit: int = 5) -> List[str]:
    return ncbi_esearch(f"{query}[title]", limit, "medgen")


def build_medgen_links(medgen_ids: List[str]) -> List[str]:
    return [f"{MEDGEN_BASE}{medgen_id}" for medgen_id in medgen_ids]


def fetch_medlineplus_connect(query: str, disease_facts: Dict[str, Any]) -> Dict[str, Any]:
    code = disease_facts.get("code")
    code_system_oid = disease_facts.get("code_system_oid")
    if not code or not code_system_oid:
        return {}

    params = {
        "mainSearchCriteria.v.cs": str(code_system_oid),
        "mainSearchCriteria.v.c": str(code),
        "mainSearchCriteria.v.dn": query,
        "knowledgeResponseType": "application/json",
        "informationRecipient.languageCode.c": "en",
    }
    response = httpx.get(MEDLINEPLUS_CONNECT_BASE, params=params, timeout=25.0)
    response.raise_for_status()
    payload = cast(Dict[str, Any], response.json())

    feed = cast(Dict[str, Any], payload.get("feed", payload))
    entry_data = feed.get("entry", [])
    entries = entry_data if isinstance(entry_data, list) else ([entry_data] if entry_data else [])
    if not entries:
        return {}

    first = cast(Dict[str, Any], entries[0])
    link_obj = first.get("link", {})
    if isinstance(link_obj, list) and link_obj:
        link_obj = link_obj[0]
    summary_value = first.get("summary", "")
    if isinstance(summary_value, dict):
        summary_value = summary_value.get("_value") or summary_value.get("#text") or ""
    clean_summary = strip_html_text(str(summary_value))

    related_links: List[Dict[str, str]] = []
    for entry in entries[1:4]:
        if not isinstance(entry, dict):
            continue
        extra_link = entry.get("link", {})
        if isinstance(extra_link, list) and extra_link:
            extra_link = extra_link[0]
        if isinstance(extra_link, dict):
            related_links.append(
                {
                    "title": str(entry.get("title", "")),
                    "url": str(extra_link.get("href", "")),
                }
            )

    title_value = first.get("title", "")
    if isinstance(title_value, dict):
        title_value = title_value.get("_value") or title_value.get("#text") or ""

    return {
        "title": str(title_value),
        "url": str(cast(Dict[str, Any], link_obj).get("href", "")) if isinstance(link_obj, dict) else "",
        "summary_html": str(summary_value),
        "summary": clean_summary,
        "source": "MedlinePlus Connect",
        "code": str(code),
        "code_system": str(disease_facts.get("code_system", "")),
        "related_links": related_links,
    }


def get_cached_disease_profile(query: str) -> Dict[str, Any]:
    normalized = query.strip().lower()
    cache = load_disease_cache()
    cached_profile = cast(Dict[str, Any], cache.get(normalized, {}))
    if cached_profile and is_cache_entry_fresh(cached_profile):
        return cached_profile

    disease_facts = get_disease_facts(query)
    local_results = search_local_disease_gene(query)
    try:
        gene_ids = fetch_ncbi_gene_ids(query)
        genes = fetch_ncbi_gene_summaries(gene_ids)
        proteins = fetch_ncbi_protein_summaries(query)
        medgen_ids = fetch_medgen_ids(query)
    except Exception:
        gene_ids = []
        genes = []
        proteins = []
        medgen_ids = []
    medlineplus = {}
    try:
        medlineplus = fetch_medlineplus_connect(query, disease_facts)
    except Exception:
        medlineplus = {}

    medlineplus_summary = str(medlineplus.get("summary", "")).strip()
    clinical_sections = extract_clinical_sections(medlineplus_summary, disease_facts)
    disease_type = disease_facts.get("is_genetic")

    profile = {
        "query": query,
        "schema_version": DISEASE_CACHE_SCHEMA_VERSION,
        "cached_at": int(time.time()),
        "medgen_ids": medgen_ids,
        "medgen_links": build_medgen_links(medgen_ids),
        "local_results": local_results,
        "genes": genes,
        "proteins": proteins,
        "medlineplus": medlineplus,
        "disease_facts": disease_facts,
        "clinical_sections": clinical_sections,
        "disease_type": disease_type,
        "related_diseases": sorted({item["disease"] for item in local_results}),
        "summary": (
            medlineplus.get("summary")
            if medlineplus.get("summary")
            else local_results[0]["description"]
            if local_results
            else (genes[0]["summary"] if genes else f"No cached disease summary yet for {query}.")
        ),
        "sources": {
            "medgen_overview": "https://www.ncbi.nlm.nih.gov/medgen/docs/overview/",
            "medlineplus_connect": "https://medlineplus.gov/medlineplus-connect/",
            "medlineplus_connect_technical": "https://medlineplus.gov/medlineplus-connect/technical-information/",
        },
    }
    cache[normalized] = profile
    save_disease_cache(cache)
    return profile


def fetch_ncbi_gene_ids(query: str, limit: int = DEFAULT_GENE_SEARCH_LIMIT) -> List[str]:
    base_term = f"{query} AND human[Organism]"
    if looks_like_gene_symbol(query):
        exact_ids = ncbi_esearch(f"{query}[sym] AND human[Organism]", limit, "gene")
        broad_ids = ncbi_esearch(base_term, limit, "gene")
        merged_ids: List[str] = []
        for gene_id in exact_ids + broad_ids:
            if gene_id not in merged_ids:
                merged_ids.append(gene_id)
        return merged_ids[:limit]
    return ncbi_esearch(base_term, limit, "gene")


def fetch_ncbi_gene_summaries(gene_ids: List[str]) -> List[Dict[str, Any]]:
    if not gene_ids:
        return []

    params = {
        **get_ncbi_common_params(),
        "db": "gene",
        "id": ",".join(gene_ids),
    }
    response = httpx.get(f"{NCBI_EUTILS_BASE}/esummary.fcgi", params=params, timeout=25.0)
    response.raise_for_status()
    payload = cast(Dict[str, Any], response.json())
    data = cast(Dict[str, Any], payload.get("result", {}))

    summaries: List[Dict[str, Any]] = []
    for gene_id in gene_ids:
        raw_item = data.get(gene_id)
        if not isinstance(raw_item, dict):
            continue
        organism = cast(Dict[str, Any], raw_item.get("organism", {}))
        summaries.append(
            {
                "gene_id": gene_id,
                "symbol": str(raw_item.get("name", "") or raw_item.get("nomenclaturesymbol", "")),
                "official_name": str(raw_item.get("description", "")),
                "summary": str(raw_item.get("summary", "")),
                "chromosome": str(raw_item.get("chromosome", "")),
                "map_location": str(raw_item.get("maplocation", "")),
                "organism": str(organism.get("scientificname", "")),
                "source": "NCBI Gene",
                "ncbi_url": f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}",
            }
        )
    return summaries


def fetch_ncbi_protein_summaries(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    protein_ids = ncbi_esearch(f"{query} AND human[Organism]", limit, "protein")
    if not protein_ids:
        return []

    params = {
        **get_ncbi_common_params(),
        "db": "protein",
        "id": ",".join(protein_ids),
    }
    response = httpx.get(f"{NCBI_EUTILS_BASE}/esummary.fcgi", params=params, timeout=25.0)
    response.raise_for_status()
    payload = cast(Dict[str, Any], response.json())
    result_block = cast(Dict[str, Any], payload.get("result", {}))

    proteins: List[Dict[str, Any]] = []
    for protein_id in protein_ids:
        raw_item = result_block.get(protein_id)
        if not isinstance(raw_item, dict):
            continue
        proteins.append(
            {
                "protein_id": protein_id,
                "title": str(raw_item.get("title", "")),
                "caption": str(raw_item.get("caption", "")),
                "accession_version": str(raw_item.get("accessionversion", "")),
            }
        )
    return proteins


def search_ncbi_gene_bundle(query: str) -> Dict[str, Any]:
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("Search query cannot be empty.")

    gene_ids = fetch_ncbi_gene_ids(cleaned_query)
    genes = fetch_ncbi_gene_summaries(gene_ids)
    proteins = fetch_ncbi_protein_summaries(cleaned_query)
    related_diseases = sorted(
        {
            item["disease"]
            for item in DISEASE_GENE_DB
            if any(cleaned_query.lower() in gene.lower() for gene in item["genes"])
        }
    )
    return {
        "genes": genes,
        "proteins": proteins,
        "related_diseases": related_diseases,
    }
