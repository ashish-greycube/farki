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
ALLOWED_PATHS = ["/api/method/farki.petpooja_endpoint.order_created"]

@frappe.whitelist()
def validate_request():
	if frappe.request and frappe.request.path and frappe.request.path in ALLOWED_PATHS:
		if frappe.request.data:
			request_data = json.loads(frappe.request.data)
	else:
		return
	    # it is not use..so what to do 
		# raise frappe.PermissionError
	farki_settings = frappe.get_doc('Farki Settings', 'Farki Settings')
	farki_settings_secret=farki_settings.secret.encode("utf8")
	payload_token=request_data.get('token').encode("utf8")
	if payload_token and farki_settings_secret==payload_token:
		frappe.set_user(farki_settings.creation_user)
	else:
		raise frappe.AuthenticationError
		

@frappe.whitelist(allow_guest=False, methods=["POST"])
def order_created(*args, **kwargs):
	if frappe.request and frappe.request.data:
		request_data = json.loads(frappe.request.data)
		frappe.enqueue(create_petpooja_log, queue="long",job_name="petpooja_log",request_data=request_data)
		return Response(status=HTTPStatus.OK)
	else:
		return Response(response=_("Event not supported"), status=HTTPStatus.BAD_REQUEST)


@frappe.whitelist()
def create_petpooja_log(request_data):
	try:
		if request_data and not isinstance(request_data, str):
			request_data = json.dumps(request_data, sort_keys=True, indent=4)
		log = frappe.new_doc('Pet Pooja Log')
		log.data = request_data
		log.log_status = "Success"
		log.insert(ignore_permissions=True)
		frappe.db.commit()
		return
	except Exception as e:
			frappe.log_error(_("PetPooja log creation error"),str(e)+"\n"+"Raw request data: "+"\n"+request_data)			