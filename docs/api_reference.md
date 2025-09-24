# MCP Learning Server API Reference

Complete API reference for the MCP Learning Server, covering Resources, Tools, and Prompts.

## Table of Contents

- [Server Information](#server-information)
- [Resources](#resources)
- [Tools](#tools)
- [Prompts](#prompts)
- [HTTP Endpoints](#http-endpoints)
- [Error Handling](#error-handling)

## Server Information

### Server Capabilities

The MCP Learning Server supports the following capabilities:

- **Protocol Version**: 2025-06-18
- **Transport Modes**: STDIO, HTTP
- **Resources**: File system access, system information
- **Tools**: Calculator, file operations, web scraping
- **Prompts**: Code review, documentation generation, data analysis, etc.

### Initialization

#### MCP Initialize Request

```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {}
  },
  "id": "init-1"
}
```

#### Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "protocolVersion": "2025-06-18",
    "serverInfo": {
      "name": "MCP Learning Server",
      "version": "0.1.0"
    },
    "capabilities": {
      "resources": {"subscribe": true, "listChanged": true},
      "tools": {"listChanged": true},
      "prompts": {"listChanged": true},
      "logging": {}
    }
  },
  "id": "init-1"
}
```

## Resources

Resources provide read-only access to data and information.

### File Manager Resources

#### List Directory Contents

**URI Pattern**: `file://list/{path}`

**Example**: `file://list//home/user/documents`

**Response**:
```json
{
  "path": "/home/user/documents",
  "total_items": 5,
  "parent_directory": "/home/user",
  "files": [
    {
      "name": "document.txt",
      "path": "/home/user/documents/document.txt",
      "size": 1024,
      "is_directory": false,
      "mime_type": "text/plain",
      "last_modified": 1640995200.0,
      "permissions": "644",
      "readable": true,
      "writable": true
    }
  ]
}
```

#### Read File Contents

**URI Pattern**: `file://read/{path}`

**Example**: `file://read//home/user/config.json`

**Response**: File contents as string

#### Get File Information

**URI Pattern**: `file://info/{path}`

**Example**: `file://info//home/user/image.jpg`

**Response**:
```json
{
  "name": "image.jpg",
  "path": "/home/user/image.jpg",
  "size": 2048576,
  "is_directory": false,
  "mime_type": "image/jpeg",
  "last_modified": 1640995200.0,
  "permissions": "644",
  "readable": true,
  "writable": false
}
```

### System Information Resources

#### System Overview

**URI**: `system://info`

**Response**:
```json
{
  "platform": "Linux",
  "platform_version": "5.4.0-91-generic",
  "architecture": "x86_64",
  "hostname": "server01",
  "username": "mcp-user",
  "python_version": "3.9.7",
  "python_executable": "/usr/bin/python3",
  "working_directory": "/app",
  "environment_variables": {
    "PATH": "/usr/bin:/bin",
    "HOME": "/home/mcp-user"
  }
}
```

#### Memory Information

**URI**: `system://memory`

**Response**:
```json
{
  "total": 8589934592,
  "available": 4294967296,
  "used": 4294967296,
  "percentage": 50.0,
  "free": 4294967296,
  "buffers": 268435456,
  "cached": 1073741824
}
```

#### CPU Information

**URI**: `system://cpu`

**Response**:
```json
{
  "physical_cores": 4,
  "logical_cores": 8,
  "current_frequency": 2400.0,
  "min_frequency": 800.0,
  "max_frequency": 3200.0,
  "usage_percentage": 15.5,
  "usage_per_cpu": [12.0, 18.5, 14.2, 17.1, 16.8, 13.5, 15.0, 19.2]
}
```

#### Disk Information

**URI**: `system://disks`

**Response**:
```json
[
  {
    "device": "/dev/sda1",
    "mountpoint": "/",
    "filesystem": "ext4",
    "total": 107374182400,
    "used": 21474836480,
    "free": 85899345920,
    "percentage": 20.0
  }
]
```

#### Network Interfaces

**URI**: `system://network`

**Response**:
```json
[
  {
    "interface": "eth0",
    "addresses": ["192.168.1.100", "fe80::a00:27ff:fe4e:66a1"],
    "is_up": true,
    "speed": 1000,
    "mtu": 1500
  }
]
```

#### Running Processes

**URI**: `system://processes`

**Response**: Returns top 50 processes by CPU usage
```json
[
  {
    "pid": 1234,
    "name": "python3",
    "username": "mcp-user",
    "status": "running",
    "cpu_percent": 15.5,
    "memory_percent": 2.1,
    "memory_info": {"rss": 104857600, "vms": 209715200},
    "create_time": 1640995200.0,
    "cmdline": ["python3", "server.py"]
  }
]
```

#### System Uptime

**URI**: `system://uptime`

**Response**:
```json
{
  "boot_time": "2024-01-01T00:00:00",
  "current_time": "2024-01-01T12:30:00",
  "uptime_seconds": 45000,
  "uptime_days": 0,
  "uptime_hours": 12,
  "uptime_minutes": 30
}
```

## Tools

Tools perform actions and computations.

### Calculator Tool

#### Basic Calculation

**Tool Name**: `calculate`

**Parameters**:
- `expression` (string, required): Mathematical expression to evaluate

**Example Request**:
```json
{
  "name": "calculate",
  "arguments": {
    "expression": "2 + 3 * sqrt(16)"
  }
}
```

**Response**:
```json
{
  "expression": "2 + 3 * sqrt(16)",
  "result": 14.0,
  "result_type": "float",
  "formatted_result": "14"
}
```

**Supported Operations**:
- Basic arithmetic: `+`, `-`, `*`, `/`, `//`, `%`, `**`
- Functions: `abs`, `round`, `min`, `max`, `sum`, `pow`
- Math functions: `sqrt`, `sin`, `cos`, `tan`, `log`, `exp`, `factorial`
- Constants: `pi`, `e`, `tau`, `inf`, `nan`

#### Quadratic Equation Solver

**Tool Name**: `solve_quadratic`

**Parameters**:
- `a` (float, required): Coefficient of x²
- `b` (float, required): Coefficient of x
- `c` (float, required): Constant term

**Example Request**:
```json
{
  "name": "solve_quadratic",
  "arguments": {
    "a": 1,
    "b": -5,
    "c": 6
  }
}
```

**Response**:
```json
{
  "equation": "1x² + -5x + 6 = 0",
  "type": "two_real_solutions",
  "discriminant": 1,
  "solutions": [3.0, 2.0],
  "message": "Two real solutions: x₁ = 3, x₂ = 2"
}
```

#### Unit Converter

**Tool Name**: `unit_converter`

**Parameters**:
- `value` (float, required): Value to convert
- `from_unit` (string, required): Source unit
- `to_unit` (string, required): Target unit
- `unit_type` (string, optional): Unit category (default: "length")

**Supported Unit Types**:
- `length`: mm, cm, m, km, in, ft, yd, mile
- `weight`: g, kg, lb, oz
- `temperature`: celsius, fahrenheit, kelvin
- `area`: m2, cm2, ft2, in2
- `volume`: ml, l, cup, pint, quart, gallon

**Example Request**:
```json
{
  "name": "unit_converter",
  "arguments": {
    "value": 100,
    "from_unit": "cm",
    "to_unit": "m",
    "unit_type": "length"
  }
}
```

**Response**:
```json
{
  "original_value": 100,
  "original_unit": "cm",
  "converted_value": 1.0,
  "converted_unit": "m",
  "unit_type": "length",
  "formatted_result": "100 cm = 1 m"
}
```

#### Statistics Calculator

**Tool Name**: `statistics_calculator`

**Parameters**:
- `numbers` (array of floats, required): List of numbers
- `operation` (string, optional): Statistic to calculate (default: "all")

**Operations**: `all`, `mean`, `median`, `mode`, `std`, `var`, `min`, `max`, `range`

**Example Request**:
```json
{
  "name": "statistics_calculator",
  "arguments": {
    "numbers": [1, 2, 3, 4, 5],
    "operation": "all"
  }
}
```

**Response**:
```json
{
  "numbers": [1, 2, 3, 4, 5],
  "operation": "all",
  "statistics": {
    "mean": 3.0,
    "median": 3.0,
    "mode": [1, 2, 3, 4, 5],
    "min": 1,
    "max": 5,
    "range": 4,
    "variance": 2.0,
    "standard_deviation": 1.4142135623730951,
    "count": 5,
    "sum": 15
  }
}
```

### File Operations Tool

#### Create File

**Tool Name**: `create_file`

**Parameters**:
- `path` (string, required): File path to create
- `content` (string, required): File content
- `overwrite` (boolean, optional): Whether to overwrite existing file (default: false)

**Example Request**:
```json
{
  "name": "create_file",
  "arguments": {
    "path": "/tmp/test.txt",
    "content": "Hello, World!",
    "overwrite": false
  }
}
```

**Response**:
```json
{
  "operation": "create_file",
  "path": "/tmp/test.txt",
  "success": true,
  "message": "File created successfully: /tmp/test.txt",
  "details": {
    "size_bytes": 13,
    "overwritten": false
  }
}
```

#### Append to File

**Tool Name**: `append_to_file`

**Parameters**:
- `path` (string, required): File path
- `content` (string, required): Content to append
- `newline` (boolean, optional): Whether to add newline before content (default: true)

#### Delete File

**Tool Name**: `delete_file`

**Parameters**:
- `path` (string, required): File path to delete
- `confirm` (boolean, required): Confirmation flag for safety

#### Copy File

**Tool Name**: `copy_file`

**Parameters**:
- `source` (string, required): Source file path
- `destination` (string, required): Destination file path
- `overwrite` (boolean, optional): Whether to overwrite existing destination (default: false)

#### Move File

**Tool Name**: `move_file`

**Parameters**:
- `source` (string, required): Source file path
- `destination` (string, required): Destination file path
- `overwrite` (boolean, optional): Whether to overwrite existing destination (default: false)

#### Search in Files

**Tool Name**: `search_in_files`

**Parameters**:
- `directory` (string, required): Directory to search in
- `pattern` (string, required): Text pattern to search for
- `file_pattern` (string, optional): File name pattern (default: "*")
- `case_sensitive` (boolean, optional): Whether search is case sensitive (default: false)

**Response**:
```json
[
  {
    "path": "/path/to/file.txt",
    "line_number": 5,
    "line_content": "This line contains the search pattern",
    "match_text": "search pattern"
  }
]
```

#### Create Directory

**Tool Name**: `create_directory`

**Parameters**:
- `path` (string, required): Directory path to create
- `parents` (boolean, optional): Whether to create parent directories (default: true)

#### Process CSV File

**Tool Name**: `process_csv_file`

**Parameters**:
- `path` (string, required): CSV file path
- `operation` (string, required): Operation type (read, analyze, filter, sort)
- Additional parameters vary by operation

**Operations**:
- `read`: Read CSV contents (supports `limit` parameter)
- `analyze`: Analyze CSV structure and provide summary

#### Process JSON File

**Tool Name**: `process_json_file`

**Parameters**:
- `path` (string, required): JSON file path
- `operation` (string, required): Operation type (read, validate, extract, keys, size)

**Operations**:
- `read`: Read JSON contents
- `validate`: Validate JSON syntax
- `keys`: List top-level keys (for objects) or length (for arrays)
- `size`: Get object/array size information

### Web Scraper Tool

#### Scrape Webpage

**Tool Name**: `scrape_webpage`

**Parameters**:
- `url` (string, required): URL to scrape
- `include_html` (boolean, optional): Whether to include HTML content (default: false)
- `follow_redirects` (boolean, optional): Whether to follow HTTP redirects (default: true)

**Response**:
```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "text_content": "This domain is for use in illustrative examples...",
  "html_content": "<html>...</html>",
  "status_code": 200,
  "headers": {"content-type": "text/html"},
  "links": ["https://example.com/page1"],
  "images": ["https://example.com/image.jpg"],
  "metadata": {
    "content_type": "text/html",
    "content_length": 1024,
    "response_time": 0.5,
    "link_count": 5,
    "image_count": 2
  }
}
```

#### Extract Links

**Tool Name**: `extract_links`

**Parameters**:
- `url` (string, required): URL to extract links from
- `internal_only` (boolean, optional): Only return internal links (default: false)
- `filter_pattern` (string, optional): Regex pattern to filter links

**Response**:
```json
[
  {
    "url": "https://example.com/page1",
    "text": "Page 1",
    "title": "Go to Page 1",
    "is_external": false
  }
]
```

#### Extract Images

**Tool Name**: `extract_images`

**Parameters**:
- `url` (string, required): URL to extract images from
- `internal_only` (boolean, optional): Only return internal images (default: false)

**Response**:
```json
[
  {
    "url": "https://example.com/image.jpg",
    "alt_text": "Example image",
    "title": "Image title",
    "width": "300",
    "height": "200"
  }
]
```

#### Search Text in Page

**Tool Name**: `search_text_in_page`

**Parameters**:
- `url` (string, required): URL to search in
- `pattern` (string, required): Text pattern or regex to search for
- `case_sensitive` (boolean, optional): Whether search is case sensitive (default: false)

**Response**:
```json
{
  "url": "https://example.com",
  "pattern": "search term",
  "case_sensitive": false,
  "total_matches": 3,
  "matches": [
    {
      "match": "search term",
      "position": 150,
      "context": "...text before search term text after..."
    }
  ]
}
```

#### Extract Structured Data

**Tool Name**: `extract_structured_data`

**Parameters**:
- `url` (string, required): URL to extract data from
- `data_type` (string, optional): Type of data to extract (default: "all")

**Data Types**: `all`, `json-ld`, `microdata`, `meta`, `tables`

**Response**:
```json
{
  "url": "https://example.com",
  "data_type": "all",
  "extracted_data": {
    "meta": {
      "description": "Page description",
      "keywords": "keyword1, keyword2"
    },
    "json_ld": [
      {"@context": "https://schema.org", "@type": "WebPage"}
    ],
    "tables": [
      {
        "headers": ["Name", "Value"],
        "rows": [["Item 1", "Value 1"]]
      }
    ]
  }
}
```

#### Check Page Status

**Tool Name**: `check_page_status`

**Parameters**:
- `url` (string, required): URL to check

**Response**:
```json
{
  "url": "https://example.com",
  "final_url": "https://example.com",
  "status_code": 200,
  "status_text": "OK",
  "headers": {"content-type": "text/html"},
  "content_type": "text/html",
  "content_length": "1024",
  "server": "nginx/1.18.0",
  "response_time_ms": 250,
  "is_redirect": false,
  "is_success": true,
  "is_client_error": false,
  "is_server_error": false,
  "title": "Example Domain"
}
```

## Prompts

Prompts provide reusable templates for LLM interactions.

### Code Review

**Prompt Name**: `code_review`

**Parameters**:
- `code` (string, required): Code to review
- `language` (string, optional): Programming language (default: "python")
- `focus_areas` (string, optional): Areas to focus on (default: "all")
- `severity_level` (string, optional): Review severity (default: "standard")

**Focus Areas**: `all`, `security`, `performance`, `style`, `bugs`
**Severity Levels**: `lenient`, `standard`, `strict`

### Generate Documentation

**Prompt Name**: `generate_documentation`

**Parameters**:
- `code` (string, required): Code to document
- `doc_type` (string, optional): Documentation type (default: "api")
- `format_type` (string, optional): Output format (default: "markdown")
- `include_examples` (boolean, optional): Include usage examples (default: true)
- `target_audience` (string, optional): Target audience (default: "developers")

**Doc Types**: `api`, `user_guide`, `technical`, `readme`
**Formats**: `markdown`, `rst`, `html`, `plain`
**Audiences**: `developers`, `users`, `beginners`, `experts`

### Data Analysis

**Prompt Name**: `analyze_data`

**Parameters**:
- `data_description` (string, required): Description of data to analyze
- `analysis_type` (string, optional): Analysis type (default: "exploratory")
- `questions` (string, optional): Specific questions to answer
- `visualization_needed` (boolean, optional): Include visualization requirements (default: true)
- `output_format` (string, optional): Output format (default: "report")

**Analysis Types**: `exploratory`, `statistical`, `predictive`, `comparative`
**Output Formats**: `report`, `summary`, `detailed`, `presentation`

### Problem Solving

**Prompt Name**: `problem_solving`

**Parameters**:
- `problem_statement` (string, required): Description of the problem
- `domain` (string, optional): Problem domain (default: "general")
- `constraints` (string, optional): Constraints or limitations
- `solution_type` (string, optional): Solution approach (default: "step_by_step")
- `creativity_level` (string, optional): Creativity level (default: "balanced")

**Domains**: `general`, `technical`, `business`, `creative`, `academic`
**Solution Types**: `step_by_step`, `creative`, `analytical`, `practical`
**Creativity Levels**: `conservative`, `balanced`, `innovative`

### Learning Plan

**Prompt Name**: `create_learning_plan`

**Parameters**:
- `topic` (string, required): Topic to learn
- `skill_level` (string, optional): Current skill level (default: "beginner")
- `time_frame` (string, optional): Available timeframe (default: "1 month")
- `learning_style` (string, optional): Learning style preference (default: "mixed")
- `goals` (string, optional): Specific learning goals

**Skill Levels**: `beginner`, `intermediate`, `advanced`
**Time Frames**: `1 week`, `1 month`, `3 months`, `6 months`
**Learning Styles**: `visual`, `hands-on`, `reading`, `mixed`

### Content Creation

**Prompt Name**: `create_content`

**Parameters**:
- `content_type` (string, required): Type of content to create
- `topic` (string, required): Content topic
- `audience` (string, optional): Target audience (default: "general")
- `tone` (string, optional): Writing tone (default: "professional")
- `length` (string, optional): Content length (default: "medium")
- `keywords` (string, optional): Keywords to include

**Content Types**: `blog_post`, `article`, `tutorial`, `guide`, `email`, `social_media`
**Audiences**: `general`, `technical`, `business`, `casual`, `academic`
**Tones**: `professional`, `casual`, `friendly`, `formal`, `conversational`
**Lengths**: `short`, `medium`, `long`, `detailed`

### Test Generation

**Prompt Name**: `generate_tests`

**Parameters**:
- `code` (string, required): Code to test
- `test_type` (string, optional): Type of tests (default: "unit")
- `framework` (string, optional): Testing framework (default: "pytest")
- `coverage_level` (string, optional): Test coverage level (default: "comprehensive")
- `include_edge_cases` (boolean, optional): Include edge cases (default: true)

**Test Types**: `unit`, `integration`, `end_to_end`, `performance`
**Frameworks**: `pytest`, `unittest`, `jest`, `mocha`
**Coverage Levels**: `basic`, `comprehensive`, `exhaustive`

## HTTP Endpoints

When using HTTP transport, additional REST-style endpoints are available:

### Server Endpoints

- `GET /` - Server information
- `GET /health` - Health check
- `GET /metrics` - Server metrics (if enabled)

### MCP Endpoints

- `POST /mcp` - Main MCP JSON-RPC endpoint
- `GET /mcp/resources` - List available resources
- `GET /mcp/tools` - List available tools
- `GET /mcp/prompts` - List available prompts

### Example HTTP Usage

```bash
# Health check
curl http://localhost:8000/health

# List tools
curl http://localhost:8000/mcp/tools

# Call MCP method
curl -X POST http://localhost:8000/mcp \\
  -H "Content-Type: application/json" \\
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "calculate",
      "arguments": {"expression": "2 + 2"}
    },
    "id": "calc-1"
  }'
```

## Error Handling

### MCP Errors

Standard JSON-RPC error format:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32601,
    "message": "Method not found",
    "data": "Additional error details"
  },
  "id": "request-id"
}
```

### Common Error Codes

- `-32700`: Parse error
- `-32600`: Invalid request
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error

### HTTP Error Responses

- `400 Bad Request`: Invalid request format
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Server unhealthy

### Tool-Specific Errors

Tools may return error results in their response format:

```json
{
  "content": [
    {
      "type": "text",
      "text": "Error: Division by zero"
    }
  ],
  "isError": true
}
```

For additional information, examples, and troubleshooting, see the main documentation and deployment guide.