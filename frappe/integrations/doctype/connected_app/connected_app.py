# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import requests
import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime, timedelta
from urllib.parse import urlencode
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient

if frappe.conf.developer_mode:
	# Disable mandatory TLS in developer mode
	import os
	os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

class ConnectedApp(Document):

	def autoname(self):
		self.callback = frappe.scrub(self.provider_name)

	def validate(self):
		callback_path = 'api/method/frappe.integrations.doctype.connected_app.connected_app.callback/'
		self.redirect_uri = frappe.request.host_url + callback_path + self.callback

	def get_oauth2_session(self):
		return OAuth2Session(
			self.client_id,
			redirect_uri=self.redirect_uri,
			scope=self.get_scopes()
		)

	def initiate_web_application_flow(self, user=None, success_uri=None):
		"""Return an authorization URL for the user. Save state in Token Cache."""
		success_uri = success_uri or '/desk'
		user = user or frappe.session.user
		oauth = self.get_oauth2_session()
		authorization_url, state = oauth.authorization_url(self.authorization_endpoint)

		try:
			token = self.get_stored_user_token(user)
		except frappe.exceptions.DoesNotExistError:
			token = frappe.new_doc('Token Cache')
			token.user = user
			token.connected_app = self.name

		token.success_uri = success_uri
		token.state = state
		token.save()

		return authorization_url

	def initiate_backend_application_flow(self):
		"""Retrieve token without user interaction. Token is not user specific."""
		client = BackendApplicationClient(client_id=self.client_id, scope=self.get_scopes())
		oauth = OAuth2Session(client=client)
		token = oauth.fetch_token(
			token_url=self.token_endpoint,
			client_secret=self.get_password('client_secret'),
			include_client_id=True
		)

		try:
			stored_token = self.get_stored_client_token()
		except frappe.exceptions.DoesNotExistError:
			stored_token = frappe.new_doc('Token Cache')

		return stored_token.update_data(token)

	def get_user_token(self, user=None, success_uri=None):
		"""Return an existing user token or initiate a Web Application Flow."""
		user = user or frappe.session.user

		try:
			token = self.get_stored_user_token(user)
			token = token.check_validity()
		except frappe.exceptions.DoesNotExistError:
			redirect = self.initiate_web_application_flow(user, success_uri)
			frappe.local.response["type"] = "redirect"
			frappe.local.response["location"] = redirect
			return redirect

		return token

	def get_client_token(self):
		"""Return an existing client token or initiate a Backend Application Flow."""
		try:
			token = self.get_stored_client_token()
		except frappe.exceptions.DoesNotExistError:
			token = self.initiate_backend_application_flow()

		return token.check_validity()

	def get_stored_client_token(self):
		return frappe.get_doc('Token Cache', self.name + '-user')

	def get_stored_user_token(self, user):
		return frappe.get_doc('Token Cache', self.name + '-' + user)
	
	def get_scopes(self):
		return [row.scope for row in self.scopes]

@frappe.whitelist(allow_guest=True)
def callback(code=None, state=None):
	"""Handle client's code."""
	if frappe.request.method != 'GET':
		frappe.throw(_('Invalid Method'))

	if frappe.session.user == 'Guest':
		frappe.throw(_("Log in to access this page."), frappe.PermissionError)

	path = frappe.request.path[1:].split("/")
	if len(path) != 4 or not path[3]:
		frappe.throw(_('Invalid Parameter(s)'))

	connected_app = path[3]
	token_cache = frappe.get_doc('Token Cache', connected_app + '-' + frappe.session.user)
	if not token_cache:
		frappe.throw(_('State Not Found'))

	if state != token_cache.state:
		frappe.throw(_('Invalid State'))

	try:
		app = frappe.get_doc('Connected App', connected_app)
	except frappe.exceptions.DoesNotExistError:
		frappe.throw(_('Invalid App'))

	oauth = app.get_oauth2_session()
	token = oauth.fetch_token(app.token_endpoint,
		code=code,
		client_secret=app.get_password('client_secret'),
		include_client_id=True
	)
	token_cache.update_data(token)

	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = token_cache.get('success_uri') or '/desk'
