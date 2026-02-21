"""算术表达式计算工具。"""

import ast
import logging
import operator
from server.tools.tool_register import register_tool

logger = logging.getLogger(__name__)

# 仅允许安全的数学运算符
_SAFE_OPERATORS = {
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


def _safe_eval(node: ast.AST) -> float:
    """递归求值 AST 节点，仅支持数字和基本运算符。"""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            msg = f"不支持的运算符: {op_type.__name__}"
            raise ValueError(msg)
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _SAFE_OPERATORS[op_type](left, right)
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            msg = f"不支持的运算符: {op_type.__name__}"
            raise ValueError(msg)
        return _SAFE_OPERATORS[op_type](_safe_eval(node.operand))
    msg = f"不支持的表达式类型: {type(node).__name__}"
    raise ValueError(msg)


@register_tool
def calculate(expression: str) -> str:
    """计算算术表达式，支持加减乘除、取余、幂运算。例如: '3 + 5 * 2', '2 ** 10', '17 % 3'"""
    logger.info("calculate 被调用，表达式: %s", expression)
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree)
        # 整数结果去掉小数点
        if isinstance(result, float) and result == int(result):
            result = int(result)
        output = f"{expression} = {result}"
        logger.info("calculate 计算成功: %s", output)
        return output
    except (ValueError, SyntaxError, ZeroDivisionError) as e:
        logger.warning("calculate 计算失败: %s, 错误: %s", expression, e)
        return f"计算失败: {e}"
