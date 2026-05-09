"""
MultiAgentic-Becas — Web Search Tool
Busca becas usando DuckDuckGo y extrae información estructurada con BeautifulSoup.
"""
import re
from loguru import logger
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup

from models.schemas import Scholarship, FundingType, AcademicLevel


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

TIMEOUT = 8  # segundos por request


def search_scholarships(query: str, max_results: int = 5) -> list[Scholarship]:
    """
    Busca becas en la web usando DuckDuckGo y parsea los resultados.

    Args:
        query: Término de búsqueda
        max_results: Máximo de resultados a procesar

    Returns:
        Lista de Scholarship encontradas y estructuradas
    """
    scholarships: list[Scholarship] = []

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(
                query,
                max_results=max_results * 2,  # Pedimos más, filtramos después
                region="wt-wt",
                safesearch="moderate",
            ))
    except Exception as e:
        logger.warning(f"DuckDuckGo search error: {e}")
        return []

    for result in results[:max_results]:
        url = result.get("href", "")
        title = result.get("title", "Beca sin título")
        body = result.get("body", "")

        if not url or _is_irrelevant_url(url):
            continue

        # Enriquecer con contenido de la página cuando sea posible
        page_content = _fetch_page_content(url)

        scholarship = _build_scholarship(
            name=title,
            url=url,
            description=body,
            page_content=page_content,
        )
        if scholarship:
            scholarships.append(scholarship)

    return scholarships


def _is_irrelevant_url(url: str) -> bool:
    """Filtra URLs que claramente no son de becas."""
    skip_patterns = [
        "youtube.com", "facebook.com", "twitter.com", "instagram.com",
        "reddit.com", "wikipedia.org", "amazon.com",
    ]
    return any(p in url.lower() for p in skip_patterns)


def _fetch_page_content(url: str) -> str:
    """Descarga el contenido de una URL y extrae texto limpio."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        # Eliminar scripts y estilos
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        # Limitar a 3000 caracteres
        return text[:3000]

    except Exception:
        return ""


def _build_scholarship(
    name: str,
    url: str,
    description: str,
    page_content: str,
) -> Scholarship | None:
    """
    Construye un objeto Scholarship a partir del texto disponible.
    Usa heurísticas simples; el EvaluatorAgent hará el análisis profundo.
    """
    combined_text = f"{name} {description} {page_content}".lower()

    # Detectar tipo de financiamiento
    if "fully funded" in combined_text or "full scholarship" in combined_text or "beca completa" in combined_text:
        funding_type = FundingType.FULL
    elif "tuition" in combined_text and "stipend" not in combined_text:
        funding_type = FundingType.TUITION_ONLY
    elif "partial" in combined_text or "parcial" in combined_text:
        funding_type = FundingType.PARTIAL
    else:
        funding_type = FundingType.FULL  # Asumir completa por defecto

    # Detectar niveles académicos mencionados
    eligible_levels = []
    level_map = {
        "undergraduate": AcademicLevel.UNDERGRADUATE,
        "bachelor": AcademicLevel.UNDERGRADUATE,
        "master": AcademicLevel.MASTER,
        "phd": AcademicLevel.PHD,
        "doctoral": AcademicLevel.PHD,
        "postdoc": AcademicLevel.POSTDOC,
    }
    for keyword, level in level_map.items():
        if keyword in combined_text and level not in eligible_levels:
            eligible_levels.append(level)

    # Detectar deadline (patrón básico)
    deadline = None
    deadline_patterns = [
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+20\d{2}\b",
        r"\b\d{1,2}/\d{1,2}/20\d{2}\b",
        r"\b20\d{2}-\d{2}-\d{2}\b",
    ]
    for pattern in deadline_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            deadline = match.group(0)
            break

    # Extraer proveedor del dominio
    domain_match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    provider = domain_match.group(1) if domain_match else "Desconocido"

    # Descripción limpia: preferir body de DuckDuckGo
    clean_desc = description if description else page_content[:300]

    try:
        return Scholarship(
            name=name,
            provider=provider,
            url=url,
            description=clean_desc,
            funding_type=funding_type,
            deadline=deadline,
            eligible_levels=eligible_levels,
        )
    except Exception as e:
        logger.debug(f"Error construyendo Scholarship: {e}")
        return None
