"""
custom_processor.py - Metadata processor para documentos do Red Hat Connectivity Link
Usado pelo rag-content tool para adicionar metadados aos chunks indexados.

Uso no index-content.sh:
  --custom-processor scripts/custom_processor.py
"""

import os


class CustomMetadataProcessor:
    """Metadata processor for Red Hat Connectivity Link documentation."""

    def __init__(self, url: str = "https://docs.redhat.com/en/documentation/red_hat_connectivity_link/1.0/"):
        self.base_url = url.rstrip("/")

    def url_function(self, file_path: str) -> str:
        """
        Retorna URL de referencia para o documento.

        Mapeia nomes de arquivo para URLs da documentacao oficial.
        """
        filename = os.path.basename(file_path)
        url_map = {
            "01-overview.md": "/html/introduction_to_connectivity_link/about-connectivity-link_rhcl",
            "02-architecture.md": "/html/introduction_to_connectivity_link/about-connectivity-link_rhcl",
            "03-installation.md": "/html/install/index",
            "04-gateway-api.md": "/html/configure/index",
            "05-tls-policies.md": "/html/configure/index",
            "06-auth-policies.md": "/html/configure/index",
            "07-rate-limiting.md": "/html/configure/index",
            "08-dns-multicluster.md": "/html/configure/index",
            "09-observability.md": "/html/operate/index",
        }
        suffix = url_map.get(filename, "")
        return f"{self.base_url}{suffix}" if suffix else self.base_url

    def title_function(self, file_path: str) -> str:
        """Retorna titulo do documento baseado no nome do arquivo."""
        filename = os.path.basename(file_path)
        title_map = {
            "01-overview.md": "Red Hat Connectivity Link - Overview",
            "02-architecture.md": "Red Hat Connectivity Link - Architecture",
            "03-installation.md": "Red Hat Connectivity Link - Installation",
            "04-gateway-api.md": "Red Hat Connectivity Link - Gateway API",
            "05-tls-policies.md": "Red Hat Connectivity Link - TLS Policies",
            "06-auth-policies.md": "Red Hat Connectivity Link - Auth Policies",
            "07-rate-limiting.md": "Red Hat Connectivity Link - Rate Limiting",
            "08-dns-multicluster.md": "Red Hat Connectivity Link - DNS and Multicluster",
            "09-observability.md": "Red Hat Connectivity Link - Observability",
        }
        return title_map.get(filename, "Red Hat Connectivity Link Documentation")
