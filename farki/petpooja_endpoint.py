import base64
import hashlib
import hmac
import json
from http import HTTPStatus
from typing import Optional, Tuple

import frappe
from frappe import _
from werkzeug.wrappers import Response

# from woocommerce_fusion.tasks.sync_sales_orders import run_sales_order_sync
# from woocommerce_fusion.woocommerce.woocommerce_api import (
# 	WC_RESOURCE_DELIMITER,
# 	parse_domain_from_url,
# )


def validate_request(request_data) -> Tuple[bool, Optional[HTTPStatus], Optional[str]]:
	# Get relevant WooCommerce Server
	try:	
	
		farki_settings = frappe.get_doc('Farki Settings', 'Farki Settings')
		farki_settings_secret=farki_settings.secret.encode("utf8")
		payload_token=request_data.get('token').encode("utf8")
		print(farki_settings_secret==payload_token,farki_settings_secret,payload_token)
		if payload_token and farki_settings_secret==payload_token:
			frappe.set_user(farki_settings.creation_user)
			return True, None, None
		else:
			return False, HTTPStatus.UNAUTHORIZED, _("Unauthorized")
		
	except Exception:
		return False, HTTPStatus.BAD_REQUEST, _("Something went wrong")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def order_created(*args, **kwargs):
	if frappe.request and frappe.request.data:
		try:
			request_data = json.loads(frappe.request.data)
			valid, status, msg = validate_request(request_data)
			if not valid:
				return Response(response=msg, status=status)			
		except ValueError:
			event="failed"
			# woocommerce returns 'webhook_id=value' for the first request which is not JSON
			# request_data = frappe.request.data
		# event = frappe.get_request_header("x-wc-webhook-event")
		event = "created"
	else:
		return Response(response=_("Missing Header"), status=HTTPStatus.BAD_REQUEST)

	if event == "created":
		# webhook_source_url = frappe.get_request_header("Authorization", "")
		# woocommerce_order_name = (
		# 	f"{parse_domain_from_url(webhook_source_url)}{WC_RESOURCE_DELIMITER}{order['id']}"
		# )
		frappe.enqueue(create_log, queue="long",request_data=request_data)
		# create_log(request_data)
		return Response(status=HTTPStatus.OK)
	else:
		return Response(response=_("Event not supported"), status=HTTPStatus.BAD_REQUEST)


@frappe.whitelist()
def create_log(request_data):
	# make_new = make_new or not bool(frappe.flags.request_id)

	# if rollback:
	# 	frappe.db.rollback()

	# if make_new:
	# 	log = frappe.get_doc({"doctype": "Ecommerce Integration Log", "integration": cstr(module_def)})
	# 	log.insert(ignore_permissions=True)
	# else:
	# 	log = frappe.get_doc("Ecommerce Integration Log", frappe.flags.request_id)

	# if response_data and not isinstance(response_data, str):
	# 	response_data = json.dumps(response_data, sort_keys=True, indent=4)

	if request_data and not isinstance(request_data, str):
		request_data = json.dumps(request_data, sort_keys=True, indent=4)
	log = frappe.new_doc('Pet Pooja Log')
	# log.message = message or _get_message(exception)
	# log.method = log.method or method
	# log.response_data = response_data or log.response_data
	log.data = request_data or log.request_data
	# log.traceback = log.traceback or frappe.get_traceback()
	# log.status = status
	log.save(ignore_permissions=True)

	frappe.db.commit()

	return log