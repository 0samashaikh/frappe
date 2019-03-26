# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import json
from frappe.model.document import Document
from frappe.utils import cint

class EnergyPointLog(Document):
	def validate(self):
		if self.type in ['Appreciation', 'Criticism'] and self.user == self.owner:
			frappe.throw(_('You cannot give review points to yourself'))

	def after_insert(self):
		message = ''
		if self.type == 'Auto':
			message=_('You gained <b>{}</b> points').format(self.points)
		elif self.type == 'Appreciation':
			message = _('{} appreciated your work on {} with {} points'.format(
				self.owner,
				self.reference_name,
				self.points
			))
		elif self.type == 'Criticism':
			message = _('{} criticized your work on {} with {} points'.format(
				self.owner,
				self.reference_name,
				self.points
			))
		if message:
			frappe.publish_realtime('energy_point_alert', message=message , user=self.user)

		frappe.cache().hdel('energy_points', self.user)

def create_energy_points_log(ref_doctype, ref_name, doc):
	doc = frappe._dict(doc)
	log_exists = frappe.db.exists('Energy Point Log', {
		'user': doc.user,
		'rule': doc.rule,
		'reference_doctype': ref_doctype,
		'reference_name': ref_name
	})
	if log_exists:
		return

	_doc = frappe.new_doc('Energy Point Log')
	_doc.reference_doctype = ref_doctype
	_doc.reference_name = ref_name
	_doc.update(doc)
	_doc.insert(ignore_permissions=True)
	return _doc

def create_review_points_log(user, points, reason=None):
	return frappe.get_doc({
		'doctype': 'Energy Point Log',
		'points': points,
		'type': 'Review',
		'user': user,
		'reason': reason
	}).insert(ignore_permissions=True)

@frappe.whitelist()
def get_energy_points(user):
	points = frappe.cache().hget('energy_points', user,
		lambda: get_user_energy_and_review_points(user))
	return frappe._dict(points.get(user, {}))

@frappe.whitelist()
def get_user_energy_and_review_points(user=None):
	if user:
		where_user = 'WHERE `user` = %s'
	else:
		where_user = ''

	points_list =  frappe.db.sql("""
		SELECT
			SUM(CASE WHEN `type`!= 'Review' THEN `points` ELSE 0 END) as energy_points,
			SUM(CASE WHEN `type`='Review' THEN `points` ELSE 0 END) as review_points,
			SUM(CASE WHEN `type`='Review' and `points` < 0 THEN ABS(`points`) ELSE 0 END) as given_points,
			`user`
		FROM `tabEnergy Point Log`
		{where_user}
		GROUP BY `user`
	""".format(where_user=where_user), values=[user] if user else (), debug=1, as_dict=1)

	dict_to_return = frappe._dict()
	for d in points_list:
		dict_to_return[d.pop('user')] = d
	return dict_to_return


@frappe.whitelist()
def review(doc, points, to_user, reason, review_type='Appreciation'):
	current_review_points = get_energy_points(frappe.session.user).review_points
	doc = frappe._dict(json.loads(doc))
	points = abs(cint(points))
	if current_review_points < points:
		frappe.msgprint(_('You do not have enough review points'))
		return

	# deduct review points from reviewer
	create_review_points_log(
		user=frappe.session.user,
		points=-points,
		reason=reason
	)

	create_energy_points_log(doc.doctype, doc.name, {
		'type': review_type,
		'reason': reason,
		'points': points if review_type == 'Appreciation' else -points,
		'user': to_user
	})

@frappe.whitelist()
def get_reviews(doctype, docname):
	return frappe.get_all('Energy Point Log', filters={
		'reference_doctype': doctype,
		'reference_name': docname,
		'type': ['in', ('Appreciation', 'Criticism')],
	}, fields=['points', 'owner', 'type', 'user', 'reason', 'creation'])