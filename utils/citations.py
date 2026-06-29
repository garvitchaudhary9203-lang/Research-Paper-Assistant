import re
from typing import Dict, Any

class CitationsGenerator:
    @staticmethod
    def _clean_authors_list(authors_str: str) -> list:
        if not authors_str:
            return ["Unknown Author"]
        # Split authors by comma, semicolon, or "and"
        authors = re.split(r',\s*|;\s*|\s+and\s+', authors_str)
        return [a.strip() for a in authors if a.strip()]

    @classmethod
    def to_apa(cls, metadata: Dict[str, Any]) -> str:
        """Format metadata to APA style: Authors. (Year). Title. DOI"""
        title = metadata.get("title", "Untitled Paper").strip()
        year = metadata.get("pub_year")
        year_str = f"({year})" if year else "(n.d.)"
        doi = metadata.get("doi", "").strip()
        
        authors = cls._clean_authors_list(metadata.get("authors", ""))
        formatted_authors = ""
        
        if len(authors) == 1:
            formatted_authors = authors[0]
        elif len(authors) == 2:
            formatted_authors = f"{authors[0]} & {authors[1]}"
        elif len(authors) > 2:
            formatted_authors = f"{authors[0]}, et al."
        else:
            formatted_authors = "Unknown Author"

        citation = f"{formatted_authors} {year_str}. *{title}*."
        if doi:
            citation += f" https://doi.org/{doi}"
        return citation

    @classmethod
    def to_mla(cls, metadata: Dict[str, Any]) -> str:
        """Format metadata to MLA style: Authors. "Title." Year. DOI"""
        title = metadata.get("title", "Untitled Paper").strip()
        year = metadata.get("pub_year")
        year_str = str(year) if year else "n.d."
        doi = metadata.get("doi", "").strip()
        
        authors = cls._clean_authors_list(metadata.get("authors", ""))
        formatted_authors = ""
        
        if len(authors) == 1:
            formatted_authors = authors[0]
        elif len(authors) == 2:
            formatted_authors = f"{authors[0]} and {authors[1]}"
        elif len(authors) > 2:
            formatted_authors = f"{authors[0]}, et al."
        else:
            formatted_authors = "Unknown Author"

        citation = f"{formatted_authors}. \"{title}.\" {year_str}."
        if doi:
            citation += f" doi:{doi}."
        return citation

    @classmethod
    def to_ieee(cls, metadata: Dict[str, Any]) -> str:
        """Format metadata to IEEE style: Authors, "Title," Year. doi: DOI."""
        title = metadata.get("title", "Untitled Paper").strip()
        year = metadata.get("pub_year")
        year_str = str(year) if year else "n.d."
        doi = metadata.get("doi", "").strip()
        
        authors = cls._clean_authors_list(metadata.get("authors", ""))
        formatted_authors = ""
        
        if len(authors) == 1:
            formatted_authors = authors[0]
        elif len(authors) == 2:
            formatted_authors = f"{authors[0]} and {authors[1]}"
        elif len(authors) > 2:
            formatted_authors = f"{authors[0]} *et al.*"
        else:
            formatted_authors = "Unknown Author"

        citation = f"{formatted_authors}, \"{title},\" {year_str}."
        if doi:
            citation += f" doi: {doi}."
        return citation

    @classmethod
    def to_bibtex(cls, metadata: Dict[str, Any]) -> str:
        """Format metadata to BibTeX string."""
        title = metadata.get("title", "Untitled Paper").strip()
        year = metadata.get("pub_year")
        year_str = str(year) if year else "n.d."
        doi = metadata.get("doi", "").strip()
        authors = metadata.get("authors", "Unknown Author").strip()
        
        # Create citation key: first_author_lastname + year
        author_list = cls._clean_authors_list(authors)
        first_author = author_list[0] if author_list else "unknown"
        lastname = first_author.split()[-1].lower() if " " in first_author else first_author.lower()
        # strip non-alphanumeric
        lastname = re.sub(r'[^a-z0-9]', '', lastname)
        citation_key = f"{lastname}{year_str}" if year_str.isdigit() else f"{lastname}_paper"

        bibtex = f"@article{{{citation_key},\n"
        bibtex += f"  author = {{{' and '.join(author_list)}}},\n"
        bibtex += f"  title = {{{title}}},\n"
        bibtex += f"  year = {{{year_str}}}"
        if doi:
            bibtex += f",\n  doi = {{{doi}}}"
        bibtex += "\n}"
        return bibtex
