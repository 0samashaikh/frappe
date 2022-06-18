# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE

from functools import cached_property

try:
	from types import NoneType
except ImportError:
	NoneType = type(None)
from typing import Dict, List, Tuple, Union

import frappe
from frappe.query_builder.builder import MariaDB, Postgres

Query = Union[str, MariaDB, Postgres]
QueryValues = Union[Tuple, List, Dict, NoneType]


def is_query_type(query: str, query_type: Union[str, Tuple[str]]) -> bool:
	return query.lstrip().split(maxsplit=1)[0].lower().startswith(query_type)


class LazyString:
	def _setup(self) -> None:
		raise NotImplementedError

	@cached_property
	def value(self) -> str:
		return self._setup()

	def __str__(self) -> str:
		return self.value

	def __repr__(self) -> str:
		return f"'{self.value}'"


class LazyDecode(LazyString):
	__slots__ = ()

	def __init__(self, value: str) -> None:
		self._value = value

	def _setup(self) -> None:
		return self._value.decode()


class LazyMogrify(LazyString):
	__slots__ = ()

	def __init__(self, query, values) -> None:
		self.query = query
		self.values = values

	def _setup(self) -> str:
		return frappe.db.mogrify(self.query, self.values)
