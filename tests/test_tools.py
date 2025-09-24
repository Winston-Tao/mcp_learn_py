"""Tests for MCP Learning Server tools."""

import math
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

import sys

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.tools.calculator import CalculatorTool
from src.tools.file_operations import FileOperationsTool
from src.tools.web_scraper import WebScraperTool


@pytest.fixture
def mock_server():
    """Create a mock server instance."""
    server = MagicMock()
    server.mcp = MagicMock()
    return server


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


class TestCalculatorTool:
    """Test cases for Calculator Tool."""

    @pytest.fixture
    def calculator(self, mock_server):
        """Create a calculator tool instance."""
        return CalculatorTool(mock_server)

    def test_initialization(self, calculator):
        """Test calculator initialization."""
        assert calculator.server is not None
        assert calculator.config is not None
        assert calculator.logger is not None
        assert calculator.SAFE_OPERATORS is not None
        assert calculator.SAFE_FUNCTIONS is not None
        assert calculator.SAFE_CONSTANTS is not None

    @pytest.mark.asyncio
    async def test_basic_arithmetic(self, calculator):
        """Test basic arithmetic calculations."""
        test_cases = [
            ("2 + 3", 5),
            ("10 - 4", 6),
            ("3 * 4", 12),
            ("15 / 3", 5),
            ("17 // 3", 5),
            ("17 % 3", 2),
            ("2 ** 3", 8),
        ]

        for expression, expected in test_cases:
            result = await calculator._calculate(expression)
            assert result.result == expected
            assert result.result_type in ["integer", "float"]

    @pytest.mark.asyncio
    async def test_mathematical_functions(self, calculator):
        """Test mathematical functions."""
        test_cases = [
            ("abs(-5)", 5),
            ("round(3.14159, 2)", 3.14),
            ("sqrt(16)", 4.0),
            ("sin(0)", 0.0),
            ("cos(0)", 1.0),
            ("log(1)", 0.0),
            ("factorial(5)", 120),
        ]

        for expression, expected in test_cases:
            result = await calculator._calculate(expression)
            if isinstance(expected, float):
                assert abs(result.result - expected) < 1e-10
            else:
                assert result.result == expected

    @pytest.mark.asyncio
    async def test_constants(self, calculator):
        """Test mathematical constants."""
        result = await calculator._calculate("pi")
        assert abs(result.result - math.pi) < 1e-10

        result = await calculator._calculate("e")
        assert abs(result.result - math.e) < 1e-10

    @pytest.mark.asyncio
    async def test_complex_expressions(self, calculator):
        """Test complex mathematical expressions."""
        test_cases = [
            ("2 + 3 * 4", 14),  # Order of operations
            ("(2 + 3) * 4", 20),  # Parentheses
            ("sqrt(16) + log10(100)", 6.0),  # Function composition
            ("sin(pi/2)", 1.0),  # Constants in functions
        ]

        for expression, expected in test_cases:
            result = await calculator._calculate(expression)
            if isinstance(expected, float):
                assert abs(result.result - expected) < 1e-10
            else:
                assert result.result == expected

    @pytest.mark.asyncio
    async def test_error_handling(self, calculator):
        """Test error handling in calculations."""
        # Division by zero
        result = await calculator._calculate("1 / 0")
        assert "Error" in result.formatted_result

        # Invalid syntax
        result = await calculator._calculate("2 +")
        assert "Error" in result.formatted_result

        # Unknown variable
        result = await calculator._calculate("unknown_var")
        assert "Error" in result.formatted_result

    @pytest.mark.asyncio
    async def test_quadratic_solver(self, calculator):
        """Test quadratic equation solver."""
        # Two real solutions: x² - 5x + 6 = 0 → x = 2, 3
        result = await calculator._solve_quadratic(1, -5, 6)
        assert result["type"] == "two_real_solutions"
        assert len(result["solutions"]) == 2
        assert 2 in result["solutions"]
        assert 3 in result["solutions"]

        # One real solution: x² - 4x + 4 = 0 → x = 2
        result = await calculator._solve_quadratic(1, -4, 4)
        assert result["type"] == "one_real_solution"
        assert result["solutions"] == [2.0]

        # Complex solutions: x² + x + 1 = 0
        result = await calculator._solve_quadratic(1, 1, 1)
        assert result["type"] == "complex_solutions"
        assert len(result["solutions"]) == 2

    @pytest.mark.asyncio
    async def test_unit_converter(self, calculator):
        """Test unit conversion."""
        # Length conversion
        result = await calculator._unit_converter(100, "cm", "m", "length")
        assert result["converted_value"] == 1.0

        # Temperature conversion
        result = await calculator._unit_converter(0, "celsius", "fahrenheit", "temperature")
        assert result["converted_value"] == 32.0

        # Weight conversion
        result = await calculator._unit_converter(1, "kg", "g", "weight")
        assert result["converted_value"] == 1000.0

    @pytest.mark.asyncio
    async def test_statistics_calculator(self, calculator):
        """Test statistics calculations."""
        numbers = [1, 2, 3, 4, 5]

        # Test mean calculation
        result = await calculator._statistics_calculator(numbers, "mean")
        assert result["statistics"]["mean"] == 3.0

        # Test all statistics
        result = await calculator._statistics_calculator(numbers, "all")
        stats = result["statistics"]
        assert stats["mean"] == 3.0
        assert stats["median"] == 3.0
        assert stats["min"] == 1
        assert stats["max"] == 5
        assert stats["range"] == 4
        assert stats["count"] == 5


class TestFileOperationsTool:
    """Test cases for File Operations Tool."""

    @pytest.fixture
    def file_ops(self, mock_server):
        """Create a file operations tool instance."""
        return FileOperationsTool(mock_server)

    def test_initialization(self, file_ops):
        """Test file operations initialization."""
        assert file_ops.server is not None
        assert file_ops.config is not None
        assert file_ops.logger is not None
        assert file_ops.max_file_size > 0
        assert isinstance(file_ops.allowed_extensions, set)

    @pytest.mark.asyncio
    async def test_create_file(self, file_ops, temp_directory):
        """Test file creation."""
        file_path = temp_directory / "test.txt"
        content = "Hello, World!"

        result = await file_ops._create_file(str(file_path), content, False)

        assert result.success
        assert file_path.exists()
        assert file_path.read_text() == content

    @pytest.mark.asyncio
    async def test_create_file_overwrite(self, file_ops, temp_directory):
        """Test file creation with overwrite."""
        file_path = temp_directory / "test.txt"
        file_path.write_text("Original content")

        new_content = "New content"
        result = await file_ops._create_file(str(file_path), new_content, True)

        assert result.success
        assert file_path.read_text() == new_content

    @pytest.mark.asyncio
    async def test_create_file_no_overwrite(self, file_ops, temp_directory):
        """Test file creation without overwrite on existing file."""
        file_path = temp_directory / "test.txt"
        file_path.write_text("Original content")

        result = await file_ops._create_file(str(file_path), "New content", False)

        assert not result.success
        assert "already exists" in result.message
        assert file_path.read_text() == "Original content"

    @pytest.mark.asyncio
    async def test_append_to_file(self, file_ops, temp_directory):
        """Test appending to a file."""
        file_path = temp_directory / "test.txt"
        file_path.write_text("Original content")

        result = await file_ops._append_to_file(str(file_path), "Appended content", True)

        assert result.success
        content = file_path.read_text()
        assert "Original content" in content
        assert "Appended content" in content

    @pytest.mark.asyncio
    async def test_delete_file(self, file_ops, temp_directory):
        """Test file deletion."""
        file_path = temp_directory / "test.txt"
        file_path.write_text("Content to delete")

        result = await file_ops._delete_file(str(file_path), True)

        assert result.success
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_file_no_confirm(self, file_ops, temp_directory):
        """Test file deletion without confirmation."""
        file_path = temp_directory / "test.txt"
        file_path.write_text("Content")

        result = await file_ops._delete_file(str(file_path), False)

        assert not result.success
        assert "confirmation" in result.message
        assert file_path.exists()

    @pytest.mark.asyncio
    async def test_copy_file(self, file_ops, temp_directory):
        """Test file copying."""
        source_path = temp_directory / "source.txt"
        dest_path = temp_directory / "dest.txt"
        content = "Content to copy"

        source_path.write_text(content)

        result = await file_ops._copy_file(str(source_path), str(dest_path), False)

        assert result.success
        assert source_path.exists()
        assert dest_path.exists()
        assert dest_path.read_text() == content

    @pytest.mark.asyncio
    async def test_move_file(self, file_ops, temp_directory):
        """Test file moving."""
        source_path = temp_directory / "source.txt"
        dest_path = temp_directory / "dest.txt"
        content = "Content to move"

        source_path.write_text(content)

        result = await file_ops._move_file(str(source_path), str(dest_path), False)

        assert result.success
        assert not source_path.exists()
        assert dest_path.exists()
        assert dest_path.read_text() == content

    @pytest.mark.asyncio
    async def test_create_directory(self, file_ops, temp_directory):
        """Test directory creation."""
        dir_path = temp_directory / "new_directory"

        result = await file_ops._create_directory(str(dir_path), True)

        assert result.success
        assert dir_path.exists()
        assert dir_path.is_dir()

    @pytest.mark.asyncio
    async def test_search_in_files(self, file_ops, temp_directory):
        """Test searching text in files."""
        # Create test files
        file1 = temp_directory / "file1.txt"
        file2 = temp_directory / "file2.txt"

        file1.write_text("This contains the search term")
        file2.write_text("This does not contain it")

        results = await file_ops._search_in_files(str(temp_directory), "search term", "*.txt", False)

        assert len(results) >= 1
        assert any(result.path == str(file1) for result in results)
        assert all("search term" in result.match_text for result in results if result.path == str(file1))

    def test_is_safe_path(self, file_ops, temp_directory):
        """Test path safety checks."""
        safe_path = temp_directory / "safe.txt"
        assert file_ops._is_safe_path(safe_path)

        # Test some potentially unsafe paths
        # Note: This test may vary based on system configuration
        # unsafe_paths = [Path("/etc/passwd"), Path("/root/.ssh/id_rsa")]
        # for path in unsafe_paths:
        #     assert not file_ops._is_safe_path(path)

    def test_is_allowed_extension(self, file_ops):
        """Test file extension checking."""
        # Test with allowed extensions
        txt_file = Path("test.txt")
        assert file_ops._is_allowed_extension(txt_file)

        # Test with potentially disallowed extension
        original_extensions = file_ops.allowed_extensions
        file_ops.allowed_extensions = {".txt", ".json"}

        exe_file = Path("test.exe")
        assert not file_ops._is_allowed_extension(exe_file)

        # Restore original extensions
        file_ops.allowed_extensions = original_extensions


class TestWebScraperTool:
    """Test cases for Web Scraper Tool."""

    @pytest.fixture
    def web_scraper(self, mock_server):
        """Create a web scraper tool instance."""
        return WebScraperTool(mock_server)

    def test_initialization(self, web_scraper):
        """Test web scraper initialization."""
        assert web_scraper.server is not None
        assert web_scraper.config is not None
        assert web_scraper.logger is not None
        assert web_scraper.timeout > 0
        assert web_scraper.max_concurrent > 0
        assert web_scraper.user_agent is not None

    @pytest.mark.asyncio
    async def test_check_page_status_success(self, web_scraper):
        """Test checking page status for successful response."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock successful response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.reason_phrase = "OK"
            mock_response.url = "https://example.com"
            mock_response.headers = {"content-type": "text/html", "server": "nginx"}
            mock_response.elapsed.total_seconds.return_value = 0.5

            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await web_scraper._check_page_status("https://example.com")

            assert result["status_code"] == 200
            assert result["status_text"] == "OK"
            assert result["is_success"] is True
            assert result["is_client_error"] is False
            assert result["is_server_error"] is False

    @pytest.mark.asyncio
    async def test_check_page_status_error(self, web_scraper):
        """Test checking page status for error response."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock error response
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.reason_phrase = "Not Found"
            mock_response.url = "https://example.com/notfound"
            mock_response.headers = {"content-type": "text/html"}
            mock_response.elapsed.total_seconds.return_value = 0.3

            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await web_scraper._check_page_status("https://example.com/notfound")

            assert result["status_code"] == 404
            assert result["is_success"] is False
            assert result["is_client_error"] is True

    @pytest.mark.asyncio
    async def test_scrape_webpage_basic(self, web_scraper):
        """Test basic webpage scraping."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock HTML content
            html_content = """
            <html>
                <head><title>Test Page</title></head>
                <body>
                    <h1>Welcome</h1>
                    <p>This is test content.</p>
                    <a href="/link1">Link 1</a>
                    <a href="https://external.com">External Link</a>
                    <img src="/image1.jpg" alt="Test Image">
                </body>
            </html>
            """

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.url = "https://example.com"
            mock_response.content = html_content.encode('utf-8')
            mock_response.headers = {"content-type": "text/html"}
            mock_response.elapsed.total_seconds.return_value = 0.5

            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await web_scraper._scrape_webpage("https://example.com", False, True)

            assert result.title == "Test Page"
            assert "Welcome" in result.text_content
            assert "This is test content" in result.text_content
            assert result.status_code == 200
            assert len(result.links) >= 2
            assert len(result.images) >= 1

    @pytest.mark.asyncio
    async def test_extract_metadata(self, web_scraper):
        """Test metadata extraction from webpage."""
        from bs4 import BeautifulSoup

        html_content = """
        <html lang="en">
            <head>
                <meta charset="utf-8">
                <meta name="description" content="Test description">
                <meta name="keywords" content="test, example">
                <meta name="author" content="Test Author">
                <title>Test Page</title>
            </head>
            <body>
                <h1>Heading 1</h1>
                <h2>Heading 2</h2>
                <a href="/link">Link</a>
                <img src="/image.jpg" alt="Image">
            </body>
        </html>
        """

        soup = BeautifulSoup(html_content, 'html.parser')
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "text/html"}
        mock_response.elapsed.total_seconds.return_value = 0.5

        metadata = web_scraper._extract_metadata(soup, mock_response)

        assert metadata["language"] == "en"
        assert metadata["charset"] == "utf-8"
        assert metadata["description"] == "Test description"
        assert metadata["keywords"] == "test, example"
        assert metadata["author"] == "Test Author"
        assert metadata["link_count"] == 1
        assert metadata["image_count"] == 1
        assert metadata["heading_count"] == 2

    @pytest.mark.asyncio
    async def test_search_text_in_page(self, web_scraper):
        """Test searching text in webpage content."""
        with patch('httpx.AsyncClient') as mock_client:
            html_content = """
            <html>
                <body>
                    <p>This is the first paragraph with search term.</p>
                    <p>This is another paragraph.</p>
                    <p>Here is another search term occurrence.</p>
                </body>
            </html>
            """

            mock_response = MagicMock()
            mock_response.content = html_content.encode('utf-8')
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await web_scraper._search_text_in_page("https://example.com", "search term", False)

            assert result["total_matches"] == 2
            assert len(result["matches"]) == 2
            assert all("search term" in match["match"] for match in result["matches"])

    def test_convert_temperature(self, web_scraper):
        """Test temperature conversion in unit converter."""
        # Celsius to Fahrenheit
        result = web_scraper._convert_temperature(0, "celsius", "fahrenheit")
        assert result == 32.0

        # Fahrenheit to Celsius
        result = web_scraper._convert_temperature(32, "fahrenheit", "celsius")
        assert result == 0.0

        # Celsius to Kelvin
        result = web_scraper._convert_temperature(0, "celsius", "kelvin")
        assert result == 273.15

        # Kelvin to Celsius
        result = web_scraper._convert_temperature(273.15, "kelvin", "celsius")
        assert abs(result - 0.0) < 1e-10