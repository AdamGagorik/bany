"""
Methods for loading input into a DataFrame.
"""
import logging
import os
import re
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from bany.cmd.solve.network.attrs import INPUT_VALUE
from bany.cmd.solve.network.attrs import node_attrs


def load(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """
    Load the configuration.
    """
    ext = os.path.splitext(path)[-1].lower()
    if ext in [".yaml", ".yml"]:
        return load_yml(path, **kwargs)
    elif ext in [".xlxs", ".xlsx"]:
        return load_xls(path, **kwargs)
    elif ext in [".csv"]:
        return load_csv(path, **kwargs)
    else:
        raise ValueError(f"unknown input extension! {ext}")


def load_yml(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """
    Load the configuration from YAML.
    """
    with open(path) as stream:
        data: list = yaml.load(stream, yaml.SafeLoader)
        return _reformat_input(data)


def load_csv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """
    Load the configuration.
    """
    with open(path) as stream:
        data: pd.DataFrame = pd.read_csv(stream)
        return _reformat_input(data)


def load_xls(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """
    Load the configuration from excel file.
    """
    return _reformat_input(pd.read_excel(path, **kwargs))


def _reformat_input(data: list | pd.DataFrame) -> pd.DataFrame:
    """
    Transform the input so that it is a DataFrame with the correct data types.
    """
    if isinstance(data, list):
        data: pd.DataFrame = pd.DataFrame(data)

    valid = True
    for col in data.columns:
        if col not in ["children"] and col not in node_attrs.columns(filters=INPUT_VALUE):
            logging.warning("unknown column in input! %s", col)

    if not valid:
        raise ValueError("unknown column in input!")

    data["children"] = data["children"].apply(_tokenize_children)
    # noinspection PyTypeChecker
    data["children"] = data.apply(_expand_regex_patterns, frame=data, axis=1)
    data = data.astype(node_attrs.dtypes(filters=INPUT_VALUE))

    return data


def _expand_regex_patterns(row: pd.Series, frame: pd.DataFrame) -> tuple[str]:
    """
    Look for regular expressions in child node lists and expand them.
    """

    def it() -> Generator[str, None, None]:
        excluded = [row[node_attrs.label.column]]
        values = row["children"]
        for value in values:
            if value.startswith("regex::"):
                pattern = re.compile(value[len("regex::") :])
                for node in frame[node_attrs.label.column]:
                    if node not in excluded and pattern.match(node):
                        yield node
            else:
                yield value

    return tuple(it())


def _tokenize_children(value: str | tuple) -> tuple:
    """
    Turn the string A;B;C into the list [A, B, C] instead.
    """
    if isinstance(value, list):
        return tuple(value)

    if isinstance(value, tuple):
        return value

    if value is None or pd.isna(value):
        return ()

    value = value.strip()
    if value:
        return tuple(t.strip() for t in value.split(";"))
    else:
        return ()
