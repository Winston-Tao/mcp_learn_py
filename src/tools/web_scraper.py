"""Web Scraper Tool for MCP Learning Server."""

import asyncio
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl

from ..utils.config import get_config
from ..utils.logger import get_logger


class ScrapedContent(BaseModel):
    """Scraped content model."""
    url: str
    title: Optional[str] = None
    text_content: str
    html_content: str
    status_code: int
    headers: Dict[str, str]
    links: List[str]
    images: List[str]
    metadata: Dict[str, Any]


class LinkInfo(BaseModel):
    """Link information model."""
    url: str
    text: str
    title: Optional[str] = None
    is_external: bool


class ImageInfo(BaseModel):
    """Image information model."""
    url: str
    alt_text: Optional[str] = None
    title: Optional[str] = None
    width: Optional[str] = None
    height: Optional[str] = None


class WebScraperTool:
    """Web Scraper Tool implementation."""

    def __init__(self, server):
        """Initialize Web Scraper Tool.

        Args:
            server: MCP server instance
        """
        self.server = server
        self.config = get_config()
        self.logger = get_logger(__name__)

        # Configure HTTP client
        self.timeout = self.config.request_timeout
        self.max_concurrent = self.config.max_concurrent_requests
        self.user_agent = self.config.user_agent

        # Session limits to prevent abuse
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

    async def register(self):
        """Register web scraper tools with the server."""

        @self.server.mcp.tool()
        async def scrape_webpage(url: str, include_html: bool = False, follow_redirects: bool = True) -> ScrapedContent:
            """Scrape content from a webpage.

            Args:
                url: URL to scrape
                include_html: Whether to include HTML content in response
                follow_redirects: Whether to follow HTTP redirects

            Returns:
                ScrapedContent: Scraped content and metadata

            Example:
                - scrape_webpage("https://example.com")
                - scrape_webpage("https://news.site.com/article", include_html=True)
            """
            return await self._scrape_webpage(url, include_html, follow_redirects)

        @self.server.mcp.tool()
        async def extract_links(url: str, internal_only: bool = False, filter_pattern: Optional[str] = None) -> List[LinkInfo]:
            """Extract all links from a webpage.

            Args:
                url: URL to extract links from
                internal_only: Only return links from the same domain
                filter_pattern: Regex pattern to filter links

            Returns:
                List[LinkInfo]: List of extracted links

            Example:
                - extract_links("https://example.com")
                - extract_links("https://blog.com", internal_only=True)
                - extract_links("https://site.com", filter_pattern=r".*\\.pdf$")
            """
            return await self._extract_links(url, internal_only, filter_pattern)

        @self.server.mcp.tool()
        async def extract_images(url: str, internal_only: bool = False) -> List[ImageInfo]:
            """Extract all images from a webpage.

            Args:
                url: URL to extract images from
                internal_only: Only return images from the same domain

            Returns:
                List[ImageInfo]: List of extracted images

            Example:
                - extract_images("https://gallery.com")
                - extract_images("https://blog.com", internal_only=True)
            """
            return await self._extract_images(url, internal_only)

        @self.server.mcp.tool()
        async def search_text_in_page(url: str, pattern: str, case_sensitive: bool = False) -> Dict[str, Any]:
            """Search for text patterns in a webpage.

            Args:
                url: URL to search in
                pattern: Text pattern or regex to search for
                case_sensitive: Whether search is case sensitive

            Returns:
                Dict[str, Any]: Search results with matches and context

            Example:
                - search_text_in_page("https://docs.com", "API key")
                - search_text_in_page("https://site.com", r"\\d{4}-\\d{2}-\\d{2}", case_sensitive=True)
            """
            return await self._search_text_in_page(url, pattern, case_sensitive)

        @self.server.mcp.tool()
        async def extract_structured_data(url: str, data_type: str = "all") -> Dict[str, Any]:
            """Extract structured data from a webpage.

            Args:
                url: URL to extract data from
                data_type: Type of data to extract (all, json-ld, microdata, meta, tables)

            Returns:
                Dict[str, Any]: Extracted structured data

            Example:
                - extract_structured_data("https://product.com")
                - extract_structured_data("https://article.com", data_type="json-ld")
                - extract_structured_data("https://data.com", data_type="tables")
            """
            return await self._extract_structured_data(url, data_type)

        @self.server.mcp.tool()
        async def check_page_status(url: str) -> Dict[str, Any]:
            """Check the status and basic information of a webpage.

            Args:
                url: URL to check

            Returns:
                Dict[str, Any]: Page status and information

            Example:
                - check_page_status("https://example.com")
                - check_page_status("https://api.service.com/health")
            """
            return await self._check_page_status(url)

        self.logger.info("Web Scraper tools registered")

    async def _scrape_webpage(self, url: str, include_html: bool, follow_redirects: bool) -> ScrapedContent:
        """Scrape content from a webpage."""
        async with self.semaphore:
            try:
                # Validate URL
                parsed_url = urlparse(url)
                if not parsed_url.scheme or not parsed_url.netloc:
                    raise ValueError(f"Invalid URL: {url}")

                # Make HTTP request
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=follow_redirects,
                    headers={"User-Agent": self.user_agent}
                ) as client:
                    response = await client.get(url)

                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract title
                title = None
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text().strip()

                # Extract text content
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                text_content = soup.get_text()
                # Clean up whitespace
                text_content = re.sub(r'\\s+', ' ', text_content).strip()

                # Extract links
                links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(url, href)
                    links.append(absolute_url)

                # Extract images
                images = []
                for img in soup.find_all('img', src=True):
                    src = img['src']
                    absolute_url = urljoin(url, src)
                    images.append(absolute_url)

                # Extract metadata
                metadata = self._extract_metadata(soup, response)

                self.logger.info(f"Scraped webpage: {url}")

                return ScrapedContent(
                    url=str(response.url),  # Final URL after redirects
                    title=title,
                    text_content=text_content[:10000],  # Limit text length
                    html_content=str(soup)[:20000] if include_html else "",
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    links=links[:50],  # Limit number of links
                    images=images[:30],  # Limit number of images
                    metadata=metadata
                )

            except httpx.TimeoutException:
                raise ValueError(f"Request timeout for URL: {url}")
            except httpx.RequestError as e:
                raise ValueError(f"Request error for URL {url}: {e}")
            except Exception as e:
                self.logger.error(f"Error scraping webpage {url}: {e}")
                raise ValueError(f"Scraping failed: {e}")

    async def _extract_links(self, url: str, internal_only: bool, filter_pattern: Optional[str]) -> List[LinkInfo]:
        """Extract links from a webpage."""
        async with self.semaphore:
            try:
                # Get webpage content
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    headers={"User-Agent": self.user_agent}
                ) as client:
                    response = await client.get(url)

                soup = BeautifulSoup(response.content, 'html.parser')
                parsed_url = urlparse(url)
                base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"

                links = []
                pattern = re.compile(filter_pattern) if filter_pattern else None

                for link in soup.find_all('a', href=True):
                    href = link['href']
                    absolute_url = urljoin(url, href)
                    link_parsed = urlparse(absolute_url)

                    # Check if internal only
                    is_external = link_parsed.netloc != parsed_url.netloc
                    if internal_only and is_external:
                        continue

                    # Apply filter pattern
                    if pattern and not pattern.search(absolute_url):
                        continue

                    link_text = link.get_text().strip()
                    link_title = link.get('title')

                    links.append(LinkInfo(
                        url=absolute_url,
                        text=link_text,
                        title=link_title,
                        is_external=is_external
                    ))

                self.logger.info(f"Extracted {len(links)} links from: {url}")
                return links[:100]  # Limit results

            except Exception as e:
                self.logger.error(f"Error extracting links from {url}: {e}")
                raise ValueError(f"Link extraction failed: {e}")

    async def _extract_images(self, url: str, internal_only: bool) -> List[ImageInfo]:
        """Extract images from a webpage."""
        async with self.semaphore:
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    headers={"User-Agent": self.user_agent}
                ) as client:
                    response = await client.get(url)

                soup = BeautifulSoup(response.content, 'html.parser')
                parsed_url = urlparse(url)

                images = []

                for img in soup.find_all('img'):
                    src = img.get('src')
                    if not src:
                        continue

                    absolute_url = urljoin(url, src)
                    img_parsed = urlparse(absolute_url)

                    # Check if internal only
                    if internal_only and img_parsed.netloc != parsed_url.netloc:
                        continue

                    images.append(ImageInfo(
                        url=absolute_url,
                        alt_text=img.get('alt'),
                        title=img.get('title'),
                        width=img.get('width'),
                        height=img.get('height')
                    ))

                self.logger.info(f"Extracted {len(images)} images from: {url}")
                return images[:50]  # Limit results

            except Exception as e:
                self.logger.error(f"Error extracting images from {url}: {e}")
                raise ValueError(f"Image extraction failed: {e}")

    async def _search_text_in_page(self, url: str, pattern: str, case_sensitive: bool) -> Dict[str, Any]:
        """Search for text patterns in a webpage."""
        async with self.semaphore:
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    headers={"User-Agent": self.user_agent}
                ) as client:
                    response = await client.get(url)

                soup = BeautifulSoup(response.content, 'html.parser')

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                text_content = soup.get_text()

                # Compile regex pattern
                flags = 0 if case_sensitive else re.IGNORECASE
                try:
                    regex_pattern = re.compile(pattern, flags)
                except re.error:
                    # If pattern is not valid regex, treat as literal string
                    escaped_pattern = re.escape(pattern)
                    regex_pattern = re.compile(escaped_pattern, flags)

                # Find matches
                matches = []
                for match in regex_pattern.finditer(text_content):
                    start = max(0, match.start() - 50)
                    end = min(len(text_content), match.end() + 50)
                    context = text_content[start:end].strip()

                    matches.append({
                        "match": match.group(),
                        "position": match.start(),
                        "context": context
                    })

                self.logger.info(f"Found {len(matches)} matches for '{pattern}' in: {url}")

                return {
                    "url": url,
                    "pattern": pattern,
                    "case_sensitive": case_sensitive,
                    "total_matches": len(matches),
                    "matches": matches[:20]  # Limit results
                }

            except Exception as e:
                self.logger.error(f"Error searching text in {url}: {e}")
                raise ValueError(f"Text search failed: {e}")

    async def _extract_structured_data(self, url: str, data_type: str) -> Dict[str, Any]:
        """Extract structured data from a webpage."""
        async with self.semaphore:
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    headers={"User-Agent": self.user_agent}
                ) as client:
                    response = await client.get(url)

                soup = BeautifulSoup(response.content, 'html.parser')
                extracted_data = {}

                if data_type in ["all", "meta"]:
                    # Extract meta tags
                    meta_data = {}
                    for meta in soup.find_all('meta'):
                        name = meta.get('name') or meta.get('property') or meta.get('http-equiv')
                        content = meta.get('content')
                        if name and content:
                            meta_data[name] = content
                    extracted_data["meta"] = meta_data

                if data_type in ["all", "json-ld"]:
                    # Extract JSON-LD structured data
                    json_ld_data = []
                    for script in soup.find_all('script', type='application/ld+json'):
                        try:
                            import json
                            data = json.loads(script.string)
                            json_ld_data.append(data)
                        except (json.JSONDecodeError, TypeError):
                            continue
                    extracted_data["json_ld"] = json_ld_data

                if data_type in ["all", "tables"]:
                    # Extract tables
                    tables_data = []
                    for table in soup.find_all('table'):
                        table_data = {"headers": [], "rows": []}

                        # Extract headers
                        header_row = table.find('tr')
                        if header_row:
                            headers = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]
                            table_data["headers"] = headers

                        # Extract rows
                        for row in table.find_all('tr')[1:]:  # Skip header row
                            row_data = [td.get_text().strip() for td in row.find_all(['td', 'th'])]
                            if row_data:
                                table_data["rows"].append(row_data)

                        if table_data["rows"]:  # Only add non-empty tables
                            tables_data.append(table_data)

                    extracted_data["tables"] = tables_data[:5]  # Limit number of tables

                self.logger.info(f"Extracted structured data from: {url}")

                return {
                    "url": url,
                    "data_type": data_type,
                    "extracted_data": extracted_data
                }

            except Exception as e:
                self.logger.error(f"Error extracting structured data from {url}: {e}")
                raise ValueError(f"Structured data extraction failed: {e}")

    async def _check_page_status(self, url: str) -> Dict[str, Any]:
        """Check page status and basic information."""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent}
            ) as client:
                response = await client.get(url)

            # Basic response info
            status_info = {
                "url": url,
                "final_url": str(response.url),
                "status_code": response.status_code,
                "status_text": response.reason_phrase,
                "headers": dict(response.headers),
                "content_type": response.headers.get('content-type', ''),
                "content_length": response.headers.get('content-length'),
                "server": response.headers.get('server', ''),
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "is_redirect": response.status_code in [301, 302, 303, 307, 308],
                "is_success": 200 <= response.status_code < 300,
                "is_client_error": 400 <= response.status_code < 500,
                "is_server_error": 500 <= response.status_code < 600
            }

            # If HTML content, extract title
            if 'text/html' in status_info["content_type"]:
                try:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    title_tag = soup.find('title')
                    if title_tag:
                        status_info["title"] = title_tag.get_text().strip()
                except Exception:
                    pass

            self.logger.info(f"Checked page status for: {url} ({response.status_code})")
            return status_info

        except httpx.TimeoutException:
            return {
                "url": url,
                "error": "timeout",
                "message": f"Request timeout ({self.timeout}s)"
            }
        except httpx.RequestError as e:
            return {
                "url": url,
                "error": "request_error",
                "message": str(e)
            }
        except Exception as e:
            self.logger.error(f"Error checking page status for {url}: {e}")
            return {
                "url": url,
                "error": "unknown_error",
                "message": str(e)
            }

    def _extract_metadata(self, soup: BeautifulSoup, response) -> Dict[str, Any]:
        """Extract metadata from webpage."""
        metadata = {}

        # Basic info
        metadata["content_type"] = response.headers.get('content-type', '')
        metadata["content_length"] = len(response.content)
        metadata["response_time"] = response.elapsed.total_seconds()

        # Language
        html_tag = soup.find('html')
        if html_tag:
            metadata["language"] = html_tag.get('lang')

        # Character encoding
        charset_meta = soup.find('meta', charset=True)
        if charset_meta:
            metadata["charset"] = charset_meta['charset']

        # Description
        desc_meta = soup.find('meta', attrs={'name': 'description'})
        if desc_meta:
            metadata["description"] = desc_meta.get('content', '')

        # Keywords
        keywords_meta = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_meta:
            metadata["keywords"] = keywords_meta.get('content', '')

        # Author
        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta:
            metadata["author"] = author_meta.get('content', '')

        # Counts
        metadata["link_count"] = len(soup.find_all('a'))
        metadata["image_count"] = len(soup.find_all('img'))
        metadata["heading_count"] = len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']))

        return metadata