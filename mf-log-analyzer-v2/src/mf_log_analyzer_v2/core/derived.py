from __future__ import annotations

import ast
import operator
from collections.abc import Callable

import numpy as np
import polars as pl

from mf_log_analyzer_v2.core.models import LogTable

_BINARY_OPS: dict[type[ast.operator], Callable[[object, object], object]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def add_formula_channel(log: LogTable, channel_id: str, formula: str) -> LogTable:
    try:
        expression = ast.parse(formula, mode="eval")
    except SyntaxError as error:
        raise ValueError("Unsupported formula expression") from error

    values = _eval_node(expression.body, log)
    series_values = (
        np.full(log.row_count, values, dtype=float)
        if np.isscalar(values)
        else np.asarray(values, dtype=float)
    )
    frame = log.frame.with_columns(pl.Series(channel_id, series_values))
    return LogTable(file_name=log.file_name, frame=frame, time_channel=log.time_channel)


def _eval_node(node: ast.AST, log: LogTable) -> object:
    if isinstance(node, ast.BinOp):
        operation = _BINARY_OPS.get(type(node.op))
        if operation is None:
            raise ValueError("Unsupported formula expression")
        return operation(_eval_node(node.left, log), _eval_node(node.right, log))

    if isinstance(node, ast.Name):
        if node.id not in log.frame.columns:
            raise ValueError(f"Unknown formula token: {node.id}")
        return log.values(node.id)

    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return float(node.value)

    raise ValueError("Unsupported formula expression")
