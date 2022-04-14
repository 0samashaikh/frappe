# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
import os
import re
import unittest
from typing import TYPE_CHECKING

import frappe

if TYPE_CHECKING:
	from frappe.printing.doctype.print_format.print_format import PrintFormat

test_records = frappe.get_test_records("Print Format")


class TestPrintFormat(unittest.TestCase):
	def test_print_user(self, style=None):
		print_html = frappe.get_print("User", "Administrator", style=style)
		self.assertTrue("<label>First Name: </label>" in print_html)
		self.assertTrue(
			re.findall(r'<div class="col-xs-[^"]*">[\s]*administrator[\s]*</div>', print_html)
		)
		return print_html

	def test_print_user_standard(self):
		print_html = self.test_print_user("Standard")
		self.assertTrue(re.findall(r"\.print-format {[\s]*font-size: 9pt;", print_html))
		self.assertFalse(re.findall(r"th {[\s]*background-color: #eee;[\s]*}", print_html))
		self.assertFalse("font-family: serif;" in print_html)

	def test_print_user_modern(self):
		print_html = self.test_print_user("Modern")
		self.assertTrue("/* modern format: for-test */" in print_html)

	def test_print_user_classic(self):
		print_html = self.test_print_user("Classic")
		self.assertTrue("/* classic format: for-test */" in print_html)

	def test_export_doc(self):
		doc: "PrintFormat" = frappe.get_doc("Print Format", test_records[0]["name"])
		doc.standard = "Yes"  # this is only to make export_doc happy
		export_path = doc.export_doc()
		exported_doc_path = f"{export_path}.json"
		doc.reload()
		doc_dict = doc.as_dict(no_nulls=True, convert_dates_to_str=True)

		self.assertTrue(os.path.exists(exported_doc_path))

		with open(exported_doc_path, "r") as f:
			exported_doc = frappe.parse_json(f.read())

		for key, value in exported_doc.items():
			if key in doc_dict:
				self.assertEqual(value, doc_dict[key])
