"""Prompt Templates for MCP Learning Server."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from ..utils.config import get_config
from ..utils.logger import get_logger


class PromptArgument(BaseModel):
    """Prompt argument model."""
    name: str
    description: str
    required: bool = True
    type: str = "string"
    default: Optional[Any] = None


class PromptResult(BaseModel):
    """Prompt result model."""
    title: str
    content: str
    metadata: Dict[str, Any]


class PromptTemplates:
    """Prompt Templates implementation."""

    def __init__(self, server):
        """Initialize Prompt Templates.

        Args:
            server: MCP server instance
        """
        self.server = server
        self.config = get_config()
        self.logger = get_logger(__name__)

    async def register(self):
        """Register prompt templates with the server."""

        # Code Review Template
        @self.server.mcp.prompt()
        async def code_review(
            code: str,
            language: str = "python",
            focus_areas: str = "all",
            severity_level: str = "standard"
        ) -> PromptResult:
            """Generate a comprehensive code review prompt.

            Args:
                code: Code to review
                language: Programming language
                focus_areas: Areas to focus on (all, security, performance, style, bugs)
                severity_level: Review severity (lenient, standard, strict)

            Returns:
                PromptResult: Generated code review prompt
            """
            return await self._code_review_template(code, language, focus_areas, severity_level)

        # Documentation Generator Template
        @self.server.mcp.prompt()
        async def generate_documentation(
            code: str,
            doc_type: str = "api",
            format_type: str = "markdown",
            include_examples: bool = True,
            target_audience: str = "developers"
        ) -> PromptResult:
            """Generate documentation for code.

            Args:
                code: Code to document
                doc_type: Type of documentation (api, user_guide, technical, readme)
                format_type: Output format (markdown, rst, html, plain)
                include_examples: Whether to include usage examples
                target_audience: Target audience (developers, users, beginners, experts)

            Returns:
                PromptResult: Generated documentation prompt
            """
            return await self._documentation_template(code, doc_type, format_type, include_examples, target_audience)

        # Data Analysis Template
        @self.server.mcp.prompt()
        async def analyze_data(
            data_description: str,
            analysis_type: str = "exploratory",
            questions: Optional[str] = None,
            visualization_needed: bool = True,
            output_format: str = "report"
        ) -> PromptResult:
            """Generate a data analysis prompt.

            Args:
                data_description: Description of the data to analyze
                analysis_type: Type of analysis (exploratory, statistical, predictive, comparative)
                questions: Specific questions to answer
                visualization_needed: Whether to include visualization requirements
                output_format: Output format (report, summary, detailed, presentation)

            Returns:
                PromptResult: Generated data analysis prompt
            """
            return await self._data_analysis_template(data_description, analysis_type, questions, visualization_needed, output_format)

        # Problem Solving Template
        @self.server.mcp.prompt()
        async def problem_solving(
            problem_statement: str,
            domain: str = "general",
            constraints: Optional[str] = None,
            solution_type: str = "step_by_step",
            creativity_level: str = "balanced"
        ) -> PromptResult:
            """Generate a problem-solving prompt.

            Args:
                problem_statement: Description of the problem
                domain: Problem domain (general, technical, business, creative, academic)
                constraints: Any constraints or limitations
                solution_type: Type of solution approach (step_by_step, creative, analytical, practical)
                creativity_level: Level of creativity needed (conservative, balanced, innovative)

            Returns:
                PromptResult: Generated problem-solving prompt
            """
            return await self._problem_solving_template(problem_statement, domain, constraints, solution_type, creativity_level)

        # Learning Template
        @self.server.mcp.prompt()
        async def create_learning_plan(
            topic: str,
            skill_level: str = "beginner",
            time_frame: str = "1 month",
            learning_style: str = "mixed",
            goals: Optional[str] = None
        ) -> PromptResult:
            """Generate a learning plan prompt.

            Args:
                topic: Topic to learn
                skill_level: Current skill level (beginner, intermediate, advanced)
                time_frame: Available time frame (1 week, 1 month, 3 months, 6 months)
                learning_style: Preferred learning style (visual, hands-on, reading, mixed)
                goals: Specific learning goals

            Returns:
                PromptResult: Generated learning plan prompt
            """
            return await self._learning_plan_template(topic, skill_level, time_frame, learning_style, goals)

        # Content Creation Template
        @self.server.mcp.prompt()
        async def create_content(
            content_type: str,
            topic: str,
            audience: str = "general",
            tone: str = "professional",
            length: str = "medium",
            keywords: Optional[str] = None
        ) -> PromptResult:
            """Generate a content creation prompt.

            Args:
                content_type: Type of content (blog_post, article, tutorial, guide, email, social_media)
                topic: Content topic
                audience: Target audience (general, technical, business, casual, academic)
                tone: Writing tone (professional, casual, friendly, formal, conversational)
                length: Content length (short, medium, long, detailed)
                keywords: Keywords to include

            Returns:
                PromptResult: Generated content creation prompt
            """
            return await self._content_creation_template(content_type, topic, audience, tone, length, keywords)

        # Testing Template
        @self.server.mcp.prompt()
        async def generate_tests(
            code: str,
            test_type: str = "unit",
            framework: str = "pytest",
            coverage_level: str = "comprehensive",
            include_edge_cases: bool = True
        ) -> PromptResult:
            """Generate test cases for code.

            Args:
                code: Code to test
                test_type: Type of tests (unit, integration, end_to_end, performance)
                framework: Testing framework (pytest, unittest, jest, mocha)
                coverage_level: Test coverage level (basic, comprehensive, exhaustive)
                include_edge_cases: Whether to include edge cases

            Returns:
                PromptResult: Generated test prompt
            """
            return await self._testing_template(code, test_type, framework, coverage_level, include_edge_cases)

        self.logger.info("Prompt templates registered")

    async def _code_review_template(self, code: str, language: str, focus_areas: str, severity_level: str) -> PromptResult:
        """Generate code review template."""
        focus_instructions = {
            "all": "all aspects including security, performance, style, maintainability, and potential bugs",
            "security": "security vulnerabilities, input validation, authentication, and authorization issues",
            "performance": "performance bottlenecks, optimization opportunities, and scalability concerns",
            "style": "code style, formatting, naming conventions, and readability",
            "bugs": "potential bugs, error handling, and edge cases"
        }

        severity_instructions = {
            "lenient": "Focus on critical issues only. Be encouraging and highlight good practices.",
            "standard": "Provide balanced feedback covering important issues and improvements.",
            "strict": "Be thorough and meticulous. Flag even minor issues and suggest best practices."
        }

        content = f"""# Code Review Request

## Code to Review
**Language:** {language}
**Focus Areas:** {focus_instructions.get(focus_areas, focus_areas)}
**Review Level:** {severity_level.title()}

```{language}
{code}
```

## Review Instructions
{severity_instructions.get(severity_level, severity_instructions["standard"])}

Please provide a comprehensive code review covering:

### 1. Overall Assessment
- Code quality and structure
- Adherence to best practices
- Maintainability and readability

### 2. Specific Issues
- Security concerns
- Performance implications
- Potential bugs or edge cases
- Code style and formatting

### 3. Recommendations
- Specific improvements
- Alternative approaches
- Best practices to adopt

### 4. Positive Aspects
- Good practices used
- Well-implemented features
- Strengths in the code

### 5. Priority Levels
Rate each issue as:
- 🔴 Critical (must fix)
- 🟡 Important (should fix)
- 🔵 Minor (nice to fix)

Please be constructive and provide actionable feedback with examples where helpful.
"""

        return PromptResult(
            title=f"Code Review: {language.title()} Code",
            content=content,
            metadata={
                "template": "code_review",
                "language": language,
                "focus_areas": focus_areas,
                "severity_level": severity_level,
                "code_length": len(code),
                "generated_at": datetime.now().isoformat()
            }
        )

    async def _documentation_template(self, code: str, doc_type: str, format_type: str, include_examples: bool, target_audience: str) -> PromptResult:
        """Generate documentation template."""
        doc_instructions = {
            "api": "API reference documentation with endpoints, parameters, responses, and authentication",
            "user_guide": "User-friendly guide with step-by-step instructions and common use cases",
            "technical": "Technical documentation for developers including architecture and implementation details",
            "readme": "README file with project overview, installation, usage, and contribution guidelines"
        }

        audience_instructions = {
            "developers": "Technical audience familiar with programming concepts",
            "users": "End users who will use the software or API",
            "beginners": "People new to the technology or concept",
            "experts": "Advanced users who need detailed technical information"
        }

        examples_section = """
### Usage Examples
Include practical code examples showing:
- Basic usage scenarios
- Common use cases
- Error handling
- Best practices
""" if include_examples else ""

        content = f"""# Documentation Generation Request

## Code to Document
**Documentation Type:** {doc_type.replace('_', ' ').title()}
**Format:** {format_type.upper()}
**Target Audience:** {target_audience.title()}
**Include Examples:** {"Yes" if include_examples else "No"}

```
{code}
```

## Documentation Requirements
Create {doc_instructions.get(doc_type, doc_type)} suitable for {audience_instructions.get(target_audience, target_audience)}.

### Structure Requirements
1. **Clear Overview**
   - Purpose and functionality
   - Key features and benefits

2. **Installation/Setup**
   - Prerequisites
   - Installation steps
   - Configuration

3. **Usage Instructions**
   - Getting started guide
   - Core functionality
   - Advanced features

{examples_section}

4. **Reference**
   - Parameters and options
   - Return values or outputs
   - Error codes and handling

5. **Additional Information**
   - Troubleshooting
   - FAQ
   - Links to related resources

### Formatting Guidelines
- Use clear, concise language
- Include proper headings and sections
- Add code blocks where appropriate
- Use bullet points and numbered lists for clarity
- Include tables for reference information

Please generate comprehensive, well-organized documentation following these requirements.
"""

        return PromptResult(
            title=f"Documentation: {doc_type.replace('_', ' ').title()}",
            content=content,
            metadata={
                "template": "documentation",
                "doc_type": doc_type,
                "format_type": format_type,
                "target_audience": target_audience,
                "include_examples": include_examples,
                "generated_at": datetime.now().isoformat()
            }
        )

    async def _data_analysis_template(self, data_description: str, analysis_type: str, questions: Optional[str], visualization_needed: bool, output_format: str) -> PromptResult:
        """Generate data analysis template."""
        analysis_instructions = {
            "exploratory": "comprehensive exploration to understand data patterns, distributions, and relationships",
            "statistical": "statistical analysis with hypothesis testing, confidence intervals, and significance tests",
            "predictive": "predictive modeling and forecasting with model evaluation and validation",
            "comparative": "comparative analysis between different groups, time periods, or conditions"
        }

        questions_section = f"""
### Specific Questions to Address
{questions}
""" if questions else """
### Analysis Focus Areas
- Data quality and completeness
- Key patterns and trends
- Outliers and anomalies
- Relationships between variables
- Insights and actionable findings
"""

        viz_section = """
### Visualization Requirements
Please include:
- Appropriate charts and graphs
- Clear labels and legends
- Visual analysis of key findings
- Interactive elements if applicable
""" if visualization_needed else ""

        content = f"""# Data Analysis Request

## Data Overview
{data_description}

## Analysis Requirements
**Type:** {analysis_type.replace('_', ' ').title()} Analysis
**Output Format:** {output_format.title()}
**Visualizations:** {"Required" if visualization_needed else "Not required"}

{questions_section}

## Analysis Structure
Please provide {analysis_instructions.get(analysis_type, analysis_type)} including:

### 1. Data Understanding
- Data structure and variables
- Data quality assessment
- Missing values and outliers
- Sample characteristics

### 2. Data Preparation
- Cleaning and preprocessing steps
- Feature engineering if needed
- Data transformation rationale
- Quality checks performed

### 3. Analysis Method
- Analytical approach and rationale
- Tools and techniques used
- Assumptions and limitations
- Statistical methods applied

### 4. Key Findings
- Primary insights discovered
- Statistical significance
- Practical implications
- Confidence levels

### 5. Recommendations
- Actionable insights
- Business implications
- Next steps for investigation
- Data collection improvements

{viz_section}

### 6. Conclusion
- Summary of key findings
- Limitations and caveats
- Future analysis opportunities

Please ensure the analysis is thorough, well-documented, and provides actionable insights.
"""

        return PromptResult(
            title=f"Data Analysis: {analysis_type.replace('_', ' ').title()}",
            content=content,
            metadata={
                "template": "data_analysis",
                "analysis_type": analysis_type,
                "output_format": output_format,
                "visualization_needed": visualization_needed,
                "has_specific_questions": questions is not None,
                "generated_at": datetime.now().isoformat()
            }
        )

    async def _problem_solving_template(self, problem_statement: str, domain: str, constraints: Optional[str], solution_type: str, creativity_level: str) -> PromptResult:
        """Generate problem-solving template."""
        approach_instructions = {
            "step_by_step": "systematic, methodical approach with clear steps",
            "creative": "innovative, out-of-the-box thinking with multiple creative solutions",
            "analytical": "data-driven, logical analysis with evidence-based recommendations",
            "practical": "hands-on, implementable solutions focusing on feasibility"
        }

        creativity_instructions = {
            "conservative": "Focus on proven, low-risk solutions with established methods",
            "balanced": "Combine proven methods with some innovative approaches",
            "innovative": "Encourage creative, unconventional solutions and breakthrough thinking"
        }

        constraints_section = f"""
### Constraints and Limitations
{constraints}
""" if constraints else ""

        content = f"""# Problem-Solving Request

## Problem Statement
{problem_statement}

## Solution Requirements
**Domain:** {domain.title()}
**Approach:** {approach_instructions.get(solution_type, solution_type)}
**Creativity Level:** {creativity_instructions.get(creativity_level, creativity_level)}

{constraints_section}

## Solution Framework
Please provide a {solution_type.replace('_', ' ')} solution following this structure:

### 1. Problem Analysis
- Problem definition and scope
- Root cause analysis
- Stakeholders affected
- Success criteria

### 2. Information Gathering
- Key facts and data needed
- Assumptions to validate
- Expert insights required
- Research areas

### 3. Solution Development
- Multiple solution options
- Pros and cons of each approach
- Resource requirements
- Timeline considerations

### 4. Evaluation Criteria
- Feasibility assessment
- Cost-benefit analysis
- Risk evaluation
- Impact measurement

### 5. Recommended Solution
- Primary recommendation with rationale
- Implementation plan
- Success metrics
- Contingency plans

### 6. Next Steps
- Immediate actions required
- Medium-term milestones
- Long-term objectives
- Review and adjustment process

## Additional Considerations
- Think {creativity_level}ly and consider unconventional approaches
- Focus on {domain} domain expertise and best practices
- Ensure solutions are actionable and measurable
- Consider potential unintended consequences

Please provide a comprehensive, well-reasoned solution that addresses all aspects of the problem.
"""

        return PromptResult(
            title=f"Problem Solving: {domain.title()} Domain",
            content=content,
            metadata={
                "template": "problem_solving",
                "domain": domain,
                "solution_type": solution_type,
                "creativity_level": creativity_level,
                "has_constraints": constraints is not None,
                "generated_at": datetime.now().isoformat()
            }
        )

    async def _learning_plan_template(self, topic: str, skill_level: str, time_frame: str, learning_style: str, goals: Optional[str]) -> PromptResult:
        """Generate learning plan template."""
        style_instructions = {
            "visual": "diagrams, videos, infographics, and visual aids",
            "hands_on": "practical exercises, projects, and interactive learning",
            "reading": "books, articles, documentation, and written materials",
            "mixed": "combination of visual, hands-on, and reading materials"
        }

        goals_section = f"""
### Specific Learning Goals
{goals}
""" if goals else """
### General Learning Objectives
- Build solid foundation in the topic
- Develop practical skills
- Gain confidence in application
- Prepare for advanced topics
"""

        content = f"""# Learning Plan Request

## Learning Overview
**Topic:** {topic}
**Current Level:** {skill_level.title()}
**Time Frame:** {time_frame}
**Learning Style:** {learning_style.replace('_', ' ').title()}

{goals_section}

## Learning Plan Structure
Please create a comprehensive learning plan optimized for {style_instructions.get(learning_style, learning_style)} that includes:

### 1. Learning Path Overview
- Major milestones and phases
- Skill progression roadmap
- Time allocation per topic
- Prerequisites and dependencies

### 2. Weekly/Module Breakdown
- Week-by-week or module-by-module plan
- Learning objectives for each period
- Key concepts to master
- Practical activities and exercises

### 3. Learning Resources
- Primary learning materials
- Supplementary resources
- Online courses and tutorials
- Books and documentation
- Practice platforms and tools

### 4. Practical Application
- Hands-on projects and exercises
- Real-world application scenarios
- Portfolio-building activities
- Skill demonstration opportunities

### 5. Assessment and Progress Tracking
- Self-assessment checkpoints
- Knowledge validation methods
- Progress measurement criteria
- Milestone achievement indicators

### 6. Support and Community
- Learning communities to join
- Mentorship opportunities
- Peer learning groups
- Expert resources for questions

### 7. Advanced Path
- Next-level topics to explore
- Specialization opportunities
- Career development connections
- Continuous learning recommendations

## Customization Notes
- Adapt pace based on {skill_level} level understanding
- Emphasize {learning_style.replace('_', ' ')} learning approaches
- Ensure realistic expectations for {time_frame} timeframe
- Include regular review and reinforcement

Please provide a detailed, actionable learning plan that maximizes learning efficiency and retention.
"""

        return PromptResult(
            title=f"Learning Plan: {topic}",
            content=content,
            metadata={
                "template": "learning_plan",
                "topic": topic,
                "skill_level": skill_level,
                "time_frame": time_frame,
                "learning_style": learning_style,
                "has_specific_goals": goals is not None,
                "generated_at": datetime.now().isoformat()
            }
        )

    async def _content_creation_template(self, content_type: str, topic: str, audience: str, tone: str, length: str, keywords: Optional[str]) -> PromptResult:
        """Generate content creation template."""
        content_specifications = {
            "blog_post": "engaging blog post with compelling headlines and reader engagement",
            "article": "informative article with research-backed content and expert insights",
            "tutorial": "step-by-step tutorial with clear instructions and examples",
            "guide": "comprehensive guide covering all aspects of the topic",
            "email": "effective email with clear subject line and call-to-action",
            "social_media": "social media content optimized for engagement and sharing"
        }

        length_specifications = {
            "short": "concise and to-the-point (300-500 words)",
            "medium": "balanced depth and readability (800-1200 words)",
            "long": "comprehensive and detailed (1500-2500 words)",
            "detailed": "extensive coverage with examples (2500+ words)"
        }

        keywords_section = f"""
### SEO Keywords to Include
{keywords}
""" if keywords else ""

        content = f"""# Content Creation Request

## Content Overview
**Type:** {content_type.replace('_', ' ').title()}
**Topic:** {topic}
**Target Audience:** {audience.title()}
**Tone:** {tone.title()}
**Length:** {length_specifications.get(length, length)}

{keywords_section}

## Content Requirements
Create a {content_specifications.get(content_type, content_type)} that is {tone} in tone and suitable for a {audience} audience.

### 1. Content Structure
- Compelling headline/title
- Engaging introduction
- Well-organized main content
- Strong conclusion with takeaways
- Clear call-to-action (if applicable)

### 2. Writing Guidelines
- Use {tone} tone throughout
- Write for {audience} audience level
- Maintain {length_specifications.get(length, length)}
- Include relevant examples and analogies
- Ensure clear, scannable formatting

### 3. Content Elements
- Key points and takeaways
- Supporting evidence or data
- Practical tips and actionable advice
- Relevant examples or case studies
- Visual content suggestions (if applicable)

### 4. Engagement Factors
- Hook readers from the beginning
- Use storytelling elements where appropriate
- Include questions or interactive elements
- Provide clear value proposition
- End with memorable conclusion

### 5. SEO and Discoverability
- Include relevant keywords naturally
- Use appropriate headings and subheadings
- Optimize for search intent
- Include meta description suggestion
- Add internal/external link opportunities

### 6. Quality Assurance
- Fact-check all claims and statistics
- Ensure logical flow and coherence
- Maintain consistent voice and style
- Proofread for grammar and clarity
- Verify all links and references

## Additional Instructions
- Make content valuable and actionable
- Ensure authenticity and credibility
- Consider current trends and relevance
- Include original insights where possible
- Make it shareable and memorable

Please create high-quality, engaging content that serves the target audience effectively.
"""

        return PromptResult(
            title=f"{content_type.replace('_', ' ').title()}: {topic}",
            content=content,
            metadata={
                "template": "content_creation",
                "content_type": content_type,
                "audience": audience,
                "tone": tone,
                "length": length,
                "has_keywords": keywords is not None,
                "generated_at": datetime.now().isoformat()
            }
        )

    async def _testing_template(self, code: str, test_type: str, framework: str, coverage_level: str, include_edge_cases: bool) -> PromptResult:
        """Generate testing template."""
        coverage_instructions = {
            "basic": "essential functionality and common use cases",
            "comprehensive": "all major functions, error conditions, and user scenarios",
            "exhaustive": "complete code coverage including all edge cases and error conditions"
        }

        edge_cases_section = """
### Edge Cases to Test
- Boundary conditions
- Invalid inputs
- Error conditions
- Performance limits
- Concurrent access
- Resource constraints
""" if include_edge_cases else ""

        content = f"""# Test Generation Request

## Code to Test
**Testing Framework:** {framework}
**Test Type:** {test_type.replace('_', ' ').title()}
**Coverage Level:** {coverage_level.title()}
**Include Edge Cases:** {"Yes" if include_edge_cases else "No"}

```
{code}
```

## Testing Requirements
Generate {coverage_instructions.get(coverage_level, coverage_level)} test cases using {framework}.

### 1. Test Structure
- Clear test organization and naming
- Setup and teardown methods
- Test data management
- Mock and fixture usage

### 2. Test Coverage Areas
- Happy path scenarios
- Error handling and exceptions
- Input validation
- Business logic verification
- Integration points

{edge_cases_section}

### 3. Test Types to Include
- **Unit Tests:** Individual function/method testing
- **Integration Tests:** Component interaction testing
- **Functional Tests:** End-to-end workflow testing
- **Performance Tests:** Speed and efficiency testing (if applicable)

### 4. Test Quality Standards
- Independent and isolated tests
- Deterministic and repeatable results
- Clear assertions and expectations
- Descriptive test names and documentation
- Proper error message validation

### 5. Test Implementation
- Use {framework} best practices
- Include proper assertions
- Handle async operations (if applicable)
- Implement data-driven tests where appropriate
- Add parameterized tests for multiple scenarios

### 6. Test Data and Mocking
- Create realistic test data
- Mock external dependencies
- Use fixtures for common setups
- Implement test database/state management
- Handle test isolation requirements

### 7. Documentation
- Comment complex test logic
- Explain test scenarios and expectations
- Document test data requirements
- Include run instructions
- Add troubleshooting notes

## Additional Requirements
- Ensure tests are maintainable and readable
- Follow testing pyramid principles
- Include both positive and negative test cases
- Verify error messages and status codes
- Test configuration and environment variations

Please generate comprehensive, well-structured tests that ensure code reliability and maintainability.
"""

        return PromptResult(
            title=f"Test Suite: {test_type.replace('_', ' ').title()} Tests",
            content=content,
            metadata={
                "template": "testing",
                "test_type": test_type,
                "framework": framework,
                "coverage_level": coverage_level,
                "include_edge_cases": include_edge_cases,
                "code_length": len(code),
                "generated_at": datetime.now().isoformat()
            }
        )