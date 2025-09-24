"""Calculator Tool for MCP Learning Server."""

import ast
import math
import operator
from typing import Any, Dict, Union

from pydantic import BaseModel

from ..utils.config import get_config
from ..utils.logger import get_logger


class CalculationResult(BaseModel):
    """Calculation result model."""
    expression: str
    result: Union[int, float, str]
    result_type: str
    formatted_result: str


class CalculatorTool:
    """Calculator Tool implementation."""

    # Safe operators for evaluation
    SAFE_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # Safe functions
    SAFE_FUNCTIONS = {
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'sum': sum,
        'pow': pow,
        # Math functions
        'sqrt': math.sqrt,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'asin': math.asin,
        'acos': math.acos,
        'atan': math.atan,
        'atan2': math.atan2,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'ceil': math.ceil,
        'floor': math.floor,
        'factorial': math.factorial,
        'degrees': math.degrees,
        'radians': math.radians,
        'gcd': math.gcd,
    }

    # Safe constants
    SAFE_CONSTANTS = {
        'pi': math.pi,
        'e': math.e,
        'tau': math.tau,
        'inf': math.inf,
        'nan': math.nan,
    }

    def __init__(self, server):
        """Initialize Calculator Tool.

        Args:
            server: MCP server instance
        """
        self.server = server
        self.config = get_config()
        self.logger = get_logger(__name__)

    async def register(self):
        """Register calculator tools with the server."""

        @self.server.mcp.tool()
        async def calculate(expression: str) -> CalculationResult:
            """Perform mathematical calculations.

            Supports basic arithmetic operations (+, -, *, /, //, %, **),
            mathematical functions (sin, cos, sqrt, log, etc.), and constants (pi, e).

            Args:
                expression: Mathematical expression to evaluate

            Returns:
                CalculationResult: Calculation result with formatted output

            Examples:
                - calculate("2 + 3 * 4")
                - calculate("sqrt(16) + log(10)")
                - calculate("sin(pi/2)")
                - calculate("factorial(5)")
            """
            return await self._calculate(expression)

        @self.server.mcp.tool()
        async def solve_quadratic(a: float, b: float, c: float) -> Dict[str, Any]:
            """Solve quadratic equation ax² + bx + c = 0.

            Args:
                a: Coefficient of x²
                b: Coefficient of x
                c: Constant term

            Returns:
                Dict[str, Any]: Solutions and equation information

            Example:
                - solve_quadratic(1, -5, 6)  # x² - 5x + 6 = 0
            """
            return await self._solve_quadratic(a, b, c)

        @self.server.mcp.tool()
        async def unit_converter(value: float, from_unit: str, to_unit: str, unit_type: str = "length") -> Dict[str, Any]:
            """Convert between different units.

            Supported unit types:
            - length: mm, cm, m, km, in, ft, yd, mile
            - weight: g, kg, lb, oz
            - temperature: celsius, fahrenheit, kelvin
            - area: m2, cm2, ft2, in2
            - volume: ml, l, cup, pint, quart, gallon

            Args:
                value: Value to convert
                from_unit: Source unit
                to_unit: Target unit
                unit_type: Type of unit (length, weight, temperature, area, volume)

            Returns:
                Dict[str, Any]: Conversion result

            Examples:
                - unit_converter(100, "cm", "m", "length")
                - unit_converter(32, "fahrenheit", "celsius", "temperature")
                - unit_converter(1, "kg", "lb", "weight")
            """
            return await self._unit_converter(value, from_unit, to_unit, unit_type)

        @self.server.mcp.tool()
        async def statistics_calculator(numbers: list[float], operation: str = "all") -> Dict[str, Any]:
            """Calculate statistical measures for a list of numbers.

            Args:
                numbers: List of numbers
                operation: Statistic to calculate (all, mean, median, mode, std, var, min, max, range)

            Returns:
                Dict[str, Any]: Statistical results

            Example:
                - statistics_calculator([1, 2, 3, 4, 5], "all")
                - statistics_calculator([1, 1, 2, 3, 3, 3], "mode")
            """
            return await self._statistics_calculator(numbers, operation)

        self.logger.info("Calculator tools registered")

    async def _calculate(self, expression: str) -> CalculationResult:
        """Perform safe mathematical calculation.

        Args:
            expression: Mathematical expression

        Returns:
            CalculationResult: Calculation result
        """
        try:
            # Clean the expression
            expression = expression.strip()
            if not expression:
                raise ValueError("Empty expression")

            # Parse the expression into AST
            try:
                node = ast.parse(expression, mode='eval')
            except SyntaxError as e:
                raise ValueError(f"Invalid syntax: {e}")

            # Evaluate the AST safely
            result = self._eval_ast(node.body)

            # Format the result
            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)
                    result_type = "integer"
                    formatted_result = str(result)
                else:
                    result_type = "float"
                    formatted_result = f"{result:.10g}"  # Remove trailing zeros
            elif isinstance(result, int):
                result_type = "integer"
                formatted_result = str(result)
            elif isinstance(result, complex):
                result_type = "complex"
                formatted_result = str(result)
            else:
                result_type = "unknown"
                formatted_result = str(result)

            self.logger.info(f"Calculated: {expression} = {formatted_result}")

            return CalculationResult(
                expression=expression,
                result=result,
                result_type=result_type,
                formatted_result=formatted_result
            )

        except Exception as e:
            self.logger.error(f"Calculation error for '{expression}': {e}")
            return CalculationResult(
                expression=expression,
                result=f"Error: {e}",
                result_type="error",
                formatted_result=f"Error: {e}"
            )

    def _eval_ast(self, node):
        """Safely evaluate AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Num):  # Python < 3.8 compatibility
            return node.n
        elif isinstance(node, ast.Name):
            if node.id in self.SAFE_CONSTANTS:
                return self.SAFE_CONSTANTS[node.id]
            else:
                raise ValueError(f"Unknown variable: {node.id}")
        elif isinstance(node, ast.BinOp):
            left = self._eval_ast(node.left)
            right = self._eval_ast(node.right)
            if type(node.op) in self.SAFE_OPERATORS:
                try:
                    return self.SAFE_OPERATORS[type(node.op)](left, right)
                except ZeroDivisionError:
                    raise ValueError("Division by zero")
                except Exception as e:
                    raise ValueError(f"Operation error: {e}")
            else:
                raise ValueError(f"Unsafe operator: {type(node.op).__name__}")
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_ast(node.operand)
            if type(node.op) in self.SAFE_OPERATORS:
                return self.SAFE_OPERATORS[type(node.op)](operand)
            else:
                raise ValueError(f"Unsafe unary operator: {type(node.op).__name__}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in self.SAFE_FUNCTIONS:
                args = [self._eval_ast(arg) for arg in node.args]
                try:
                    return self.SAFE_FUNCTIONS[node.func.id](*args)
                except Exception as e:
                    raise ValueError(f"Function error: {e}")
            else:
                func_name = getattr(node.func, 'id', 'unknown')
                raise ValueError(f"Unknown or unsafe function: {func_name}")
        elif isinstance(node, ast.List):
            return [self._eval_ast(elem) for elem in node.elts]
        elif isinstance(node, ast.Tuple):
            return tuple(self._eval_ast(elem) for elem in node.elts)
        else:
            raise ValueError(f"Unsafe node type: {type(node).__name__}")

    async def _solve_quadratic(self, a: float, b: float, c: float) -> Dict[str, Any]:
        """Solve quadratic equation.

        Args:
            a: Coefficient of x²
            b: Coefficient of x
            c: Constant term

        Returns:
            Dict[str, Any]: Solution information
        """
        try:
            if a == 0:
                if b == 0:
                    if c == 0:
                        return {
                            "equation": f"{a}x² + {b}x + {c} = 0",
                            "type": "identity",
                            "solutions": "All real numbers",
                            "message": "Every number is a solution"
                        }
                    else:
                        return {
                            "equation": f"{a}x² + {b}x + {c} = 0",
                            "type": "contradiction",
                            "solutions": "No solution",
                            "message": "No real solutions exist"
                        }
                else:
                    # Linear equation
                    solution = -c / b
                    return {
                        "equation": f"{a}x² + {b}x + {c} = 0",
                        "type": "linear",
                        "solutions": [solution],
                        "message": f"Linear equation with solution x = {solution}"
                    }

            # Calculate discriminant
            discriminant = b**2 - 4*a*c

            equation_str = f"{a}x² + {b}x + {c} = 0"

            if discriminant > 0:
                # Two real solutions
                x1 = (-b + math.sqrt(discriminant)) / (2*a)
                x2 = (-b - math.sqrt(discriminant)) / (2*a)
                return {
                    "equation": equation_str,
                    "type": "two_real_solutions",
                    "discriminant": discriminant,
                    "solutions": [x1, x2],
                    "message": f"Two real solutions: x₁ = {x1:.6g}, x₂ = {x2:.6g}"
                }
            elif discriminant == 0:
                # One real solution (repeated root)
                x = -b / (2*a)
                return {
                    "equation": equation_str,
                    "type": "one_real_solution",
                    "discriminant": discriminant,
                    "solutions": [x],
                    "message": f"One real solution (repeated root): x = {x:.6g}"
                }
            else:
                # Complex solutions
                real_part = -b / (2*a)
                imaginary_part = math.sqrt(abs(discriminant)) / (2*a)
                x1 = complex(real_part, imaginary_part)
                x2 = complex(real_part, -imaginary_part)
                return {
                    "equation": equation_str,
                    "type": "complex_solutions",
                    "discriminant": discriminant,
                    "solutions": [str(x1), str(x2)],
                    "message": f"Complex solutions: x₁ = {x1}, x₂ = {x2}"
                }

        except Exception as e:
            self.logger.error(f"Quadratic solver error: {e}")
            raise ValueError(f"Error solving quadratic equation: {e}")

    async def _unit_converter(self, value: float, from_unit: str, to_unit: str, unit_type: str) -> Dict[str, Any]:
        """Convert between units.

        Args:
            value: Value to convert
            from_unit: Source unit
            to_unit: Target unit
            unit_type: Type of unit

        Returns:
            Dict[str, Any]: Conversion result
        """
        try:
            # Unit conversion factors to base units
            conversions = {
                "length": {  # Base unit: meter
                    "mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0,
                    "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mile": 1609.344
                },
                "weight": {  # Base unit: kilogram
                    "g": 0.001, "kg": 1.0, "lb": 0.453592, "oz": 0.0283495
                },
                "temperature": {  # Special handling needed
                    "celsius": "C", "fahrenheit": "F", "kelvin": "K"
                },
                "area": {  # Base unit: square meter
                    "m2": 1.0, "cm2": 0.0001, "ft2": 0.092903, "in2": 0.00064516
                },
                "volume": {  # Base unit: liter
                    "ml": 0.001, "l": 1.0, "cup": 0.236588,
                    "pint": 0.473176, "quart": 0.946353, "gallon": 3.78541
                }
            }

            if unit_type not in conversions:
                raise ValueError(f"Unknown unit type: {unit_type}")

            if unit_type == "temperature":
                result = self._convert_temperature(value, from_unit, to_unit)
            else:
                conversion_factors = conversions[unit_type]
                if from_unit not in conversion_factors:
                    raise ValueError(f"Unknown {unit_type} unit: {from_unit}")
                if to_unit not in conversion_factors:
                    raise ValueError(f"Unknown {unit_type} unit: {to_unit}")

                # Convert to base unit, then to target unit
                base_value = value * conversion_factors[from_unit]
                result = base_value / conversion_factors[to_unit]

            return {
                "original_value": value,
                "original_unit": from_unit,
                "converted_value": result,
                "converted_unit": to_unit,
                "unit_type": unit_type,
                "formatted_result": f"{value} {from_unit} = {result:.6g} {to_unit}"
            }

        except Exception as e:
            self.logger.error(f"Unit conversion error: {e}")
            raise ValueError(f"Error converting units: {e}")

    def _convert_temperature(self, value: float, from_unit: str, to_unit: str) -> float:
        """Convert temperature between different scales."""
        # Normalize unit names
        from_unit = from_unit.lower()
        to_unit = to_unit.lower()

        # Convert to Celsius first
        if from_unit in ["celsius", "c"]:
            celsius = value
        elif from_unit in ["fahrenheit", "f"]:
            celsius = (value - 32) * 5/9
        elif from_unit in ["kelvin", "k"]:
            celsius = value - 273.15
        else:
            raise ValueError(f"Unknown temperature unit: {from_unit}")

        # Convert from Celsius to target unit
        if to_unit in ["celsius", "c"]:
            return celsius
        elif to_unit in ["fahrenheit", "f"]:
            return celsius * 9/5 + 32
        elif to_unit in ["kelvin", "k"]:
            return celsius + 273.15
        else:
            raise ValueError(f"Unknown temperature unit: {to_unit}")

    async def _statistics_calculator(self, numbers: list[float], operation: str) -> Dict[str, Any]:
        """Calculate statistical measures.

        Args:
            numbers: List of numbers
            operation: Statistical operation

        Returns:
            Dict[str, Any]: Statistical results
        """
        try:
            if not numbers:
                raise ValueError("Empty list of numbers")

            # Remove any None values and convert to float
            clean_numbers = []
            for num in numbers:
                if num is not None:
                    clean_numbers.append(float(num))

            if not clean_numbers:
                raise ValueError("No valid numbers in the list")

            n = len(clean_numbers)
            sorted_numbers = sorted(clean_numbers)

            # Calculate various statistics
            stats = {}

            if operation in ["all", "mean"]:
                stats["mean"] = sum(clean_numbers) / n

            if operation in ["all", "median"]:
                if n % 2 == 0:
                    stats["median"] = (sorted_numbers[n//2-1] + sorted_numbers[n//2]) / 2
                else:
                    stats["median"] = sorted_numbers[n//2]

            if operation in ["all", "mode"]:
                from collections import Counter
                counts = Counter(clean_numbers)
                max_count = max(counts.values())
                modes = [num for num, count in counts.items() if count == max_count]
                stats["mode"] = modes if len(modes) > 1 else modes[0]
                stats["mode_frequency"] = max_count

            if operation in ["all", "min"]:
                stats["min"] = min(clean_numbers)

            if operation in ["all", "max"]:
                stats["max"] = max(clean_numbers)

            if operation in ["all", "range"]:
                stats["range"] = max(clean_numbers) - min(clean_numbers)

            if operation in ["all", "std", "var"]:
                mean = sum(clean_numbers) / n
                variance = sum((x - mean) ** 2 for x in clean_numbers) / n
                stats["variance"] = variance
                stats["standard_deviation"] = math.sqrt(variance)

                # Sample standard deviation (n-1)
                if n > 1:
                    sample_variance = sum((x - mean) ** 2 for x in clean_numbers) / (n - 1)
                    stats["sample_variance"] = sample_variance
                    stats["sample_standard_deviation"] = math.sqrt(sample_variance)

            # Add summary info
            stats["count"] = n
            stats["sum"] = sum(clean_numbers)

            return {
                "numbers": clean_numbers,
                "operation": operation,
                "statistics": stats,
                "sorted_numbers": sorted_numbers
            }

        except Exception as e:
            self.logger.error(f"Statistics calculation error: {e}")
            raise ValueError(f"Error calculating statistics: {e}")