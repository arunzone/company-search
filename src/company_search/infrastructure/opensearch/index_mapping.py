"""OpenSearch index settings and field mappings.

Design:
  - 3 shards: supports ~7M docs at ~2.3M/shard; sized for 60 RPS
  - industry_synonyms filter: maps plain-English terms → dataset vocabulary at index time,
    enabling semantic matching without runtime vector search or extra infrastructure
  - edge_ngram on name: enables prefix/partial-name search (e.g. "acce" → "accenture")
  - year_founded as integer: supports range queries
  - locality/country as text+keyword: partial match search + exact filter/aggregation
"""

INDEX_MAPPING: dict = {
    "settings": {
        "number_of_shards": 3,
        "number_of_replicas": 1,
        "analysis": {
            "filter": {
                "industry_synonyms": {
                    "type": "synonym",
                    "synonyms": [
                        "tech, technology, it => information technology and services",
                        "software => computer software",
                        "finance, financial => financial services",
                        "healthcare, health care => hospital & health care",
                        "ecommerce, e-commerce, online retail => internet",
                        "consulting, advisory => management consulting",
                        "marketing, advertising => marketing and advertising",
                        "media, film, tv => media production",
                        "education, edtech, learning => e-learning",
                        "real estate, property => real estate",
                        "automotive, auto, car => automotive",
                        "pharma, pharmaceutical, drug => pharmaceuticals",
                        "telecom, telecommunications => telecommunications",
                        "manufacturing, industrial => mechanical or industrial engineering",
                        "logistics, supply chain, shipping => logistics and supply chain",
                        "food, beverage, restaurant => food & beverages",
                        "security, cybersecurity => computer & network security",
                        "insurance => insurance",
                        "construction, building => construction",
                        "energy, oil, gas => oil & energy",
                    ],
                },
                "edge_ngram_filter": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 20,
                },
            },
            "analyzer": {
                # Used at index time — builds edge n-grams for prefix search
                "name_index_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding", "edge_ngram_filter"],
                },
                # Used at search time — no n-grams so score isn't diluted
                "name_search_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"],
                },
                # Applies synonym expansion so "tech" matches "information technology and services"
                "industry_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding", "industry_synonyms"],
                },
            },
        },
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "name": {
                "type": "text",
                "analyzer": "name_index_analyzer",
                "search_analyzer": "name_search_analyzer",
                "fields": {
                    # keyword subfield for exact sort and aggregations
                    "keyword": {"type": "keyword", "ignore_above": 256},
                },
            },
            "domain": {"type": "keyword"},
            "year_founded": {"type": "integer"},
            "industry": {
                "type": "text",
                "analyzer": "industry_analyzer",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 256},
                },
            },
            "size_range": {"type": "keyword"},
            "locality": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 256},
                },
            },
            "country": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 256},
                },
            },
            "linkedin_url": {"type": "keyword"},
            "current_employee_estimate": {"type": "integer"},
            "total_employee_estimate": {"type": "integer"},
        }
    },
}
