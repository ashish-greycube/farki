# Copyright (c) 2024, GreyCube Technologies and contributors
# For license information, please see license.txt

import frappe
import erpnext
from frappe import _
from frappe.utils import getdate, cstr, add_to_date, get_time, flt, cint, get_link_to_form, get_url_to_form
from frappe.model.document import Document
from erpnext import get_company_currency, get_default_company
from frappe.model.meta import get_field_precision
from erpnext.stock.get_item_details import get_price_list_rate_for

class PetPoojaSICreatinoError(frappe.ValidationError):
	pass

class PetPoojaLog(Document):
	def after_insert(self):
		pass
		# frappe.enqueue(create_sales_invoice, docname=self.name, queue="long",job_name="petpooja_si")
	
@frappe.whitelist()
def create_sales_invoice(docname):
	try:
		ppl_doc = frappe.get_doc("Pet Pooja Log",docname)
		data = frappe.parse_json(ppl_doc.data)
		properties = data.get('properties')
		restaurant = properties.get('Restaurant')
		rest_id = restaurant.get('restID')
		
		cost_center = frappe.db.get_all('Cost Center', filters={'custom_petpooja_restaurant_id':rest_id }, fields=['name'])
		if not cost_center:
			frappe.throw(_("No Cost Center found for Restaurant ID {0}".format(frappe.bold(rest_id))), exc=PetPoojaSICreatinoError)
		cost_center_doc = frappe.get_cached_doc('Cost Center', cost_center[0].name)
		farki_settings_doc = frappe.get_cached_doc('Farki Settings')
		zomato_customer = farki_settings_doc.default_zomato_customer
		swiggy_customer = farki_settings_doc.default_swiggy_customer		
		order_details = properties.get('Order')
		create_date_time = frappe.utils.get_datetime(order_details.get('created_on'))

		default_currency_precision = cint(frappe.db.get_default("currency_precision")) or 2
		default_float_precision = cint(frappe.db.get_default("float_precision")) or 2

		# create SI
		sales_invoice_doc = frappe.new_doc("Sales Invoice")
		sales_invoice_doc.cost_center = cost_center_doc.name
		sales_invoice_doc.set_posting_time = 1
		sales_invoice_doc.posting_date = create_date_time.date()
		sales_invoice_doc.posting_time = create_date_time.time()
		sales_invoice_doc.due_date = create_date_time.date()
		sales_invoice_doc.custom_pet_pooja_order_id = order_details.get('orderID')

		sales_taxes_and_charges = frappe.db.get_value('Sales Taxes and Charges Template',{"is_default":1}, 'name')
		sales_taxes_and_charges_doc = frappe.get_cached_doc('Sales Taxes and Charges Template', sales_taxes_and_charges)
		for row in sales_taxes_and_charges_doc.taxes:
			sales_invoice_doc.append('taxes', row)

		payment_type = order_details.get('payment_type')
		order_from = order_details.get('order_from')
		custom_payment_type = order_details.get('custom_payment_type')
		mode_of_payment = ''
		payments_row = sales_invoice_doc.append('payments', {})
		mode_of_payment_found = False
		pl_found = False
		si_customer = None
		# order from POS and fill Payments child table
		if order_from == 'POS':
			si_customer = cost_center_doc.custom_default_b2c_customer
			if len(cost_center_doc.custom_customer_wise_price_list)>0:
				for pl in cost_center_doc.custom_customer_wise_price_list:
					if pl.customer == cost_center_doc.custom_default_b2c_customer:
						if pl.price_list:
							pl_found = True
							print(pl.price_list,"Price list")
							sales_invoice_doc.selling_price_list = pl.price_list
							break
						else :	
							frappe.throw(_("Please price list for {0} customer in cost center {1}".format(frappe.bold(cost_center_doc.custom_default_b2c_customer),get_link_to_form("Cost Center",cost_center_doc.name))),exc=PetPoojaSICreatinoError)
					else :
						pl_found = False
				if pl_found == False:
					frappe.throw(_("Please price list for {0} customer in cost center {1}".format(frappe.bold(cost_center_doc.custom_default_b2c_customer),get_link_to_form("Cost Center",cost_center_doc.name))),exc=PetPoojaSICreatinoError)
			else :
				frappe.throw(_("Please set customer and appropriate price list in Cost Center {0}".format(get_link_to_form("Cost Center",cost_center_doc.name))),exc=PetPoojaSICreatinoError)
			sales_invoice_doc.is_pos = 1
		
			if payment_type != "Other":
				if len(cost_center_doc.custom_pp_vs_erpnext_mode_of_payment_mapping) > 0:
					for row in cost_center_doc.custom_pp_vs_erpnext_mode_of_payment_mapping:
						if row.pp_mode_of_payment == payment_type:
							mode_of_payment_found = True
							if row.erpnext_mode_of_payment:
								payments_row.mode_of_payment = row.erpnext_mode_of_payment
								mode_of_payment = row.erpnext_mode_of_payment
								break
							else :
								frappe.throw(_("Please set appropriate Mode of Payment for Payment type {0} in Cost Center {1}".format(frappe.bold(payment_type),get_link_to_form("Cost Center",cost_center_doc.name))),exc=PetPoojaSICreatinoError)
						else :
							mode_of_payment_found = False
					if mode_of_payment_found == False:
						frappe.throw(_("Please set appropriate Mode of Payment for Payment type {0} in Cost Center {1}".format(frappe.bold(payment_type),get_link_to_form("Cost Center",cost_center_doc.name))),exc=PetPoojaSICreatinoError)
				else :
					frappe.throw(_("Please set appropriate Payment type and Mode of Payment in Cost Center {0}".format(get_link_to_form("Cost Center",cost_center_doc.name))),exc=PetPoojaSICreatinoError)
			elif payment_type == "Other":
				if len(farki_settings_doc.pp_vs_erpnext_mode_of_payment_mapping) > 0:
					for mop in farki_settings_doc.pp_vs_erpnext_mode_of_payment_mapping:
						if mop.pp_mode_of_payment == custom_payment_type:
							mode_of_payment_found = True
							if mop.erpnext_mode_of_payment:
								payments_row.mode_of_payment = mop.erpnext_mode_of_payment
								mode_of_payment = mop.erpnext_mode_of_payment
								break
							else :
								frappe.throw(_("Please set appropriate Mode of Payment for Payment type {0} in Farki Settings {1}".format(frappe.bold(custom_payment_type),get_link_to_form("Farki Settings",farki_settings_doc.name))),exc=PetPoojaSICreatinoError)
						else :
							mode_of_payment_found = False
					if mode_of_payment_found == False:
						frappe.throw(_("Please set appropriate Mode of Payment for Payment type {0} in Farki Settings {1}".format(frappe.bold(custom_payment_type),get_link_to_form("Farki Settings",farki_settings_doc.name))),exc=PetPoojaSICreatinoError)
				
				elif len(cost_center_doc.custom_pp_vs_erpnext_mode_of_payment_mapping) > 0:
					for row in cost_center_doc.custom_pp_vs_erpnext_mode_of_payment_mapping:
						if row.pp_mode_of_payment == custom_payment_type:
							mode_of_payment_found = True
							if row.erpnext_mode_of_payment:
								payments_row.mode_of_payment = row.erpnext_mode_of_payment
								mode_of_payment = row.erpnext_mode_of_payment
								break
							else :
								frappe.throw(_("Please set appropriate Mode of Payment for Payment type {0} in Farki Settings {1}".format(frappe.bold(custom_payment_type),get_link_to_form("Farki Settings",farki_settings_doc.name))),exc=PetPoojaSICreatinoError)
						else :
							mode_of_payment_found = False
					if mode_of_payment_found == False:
						frappe.throw(_("Please set appropriate Mode of Payment for Payment type {0} in Cost Center {1}".format(frappe.bold(frappe.bold(custom_payment_type)),get_link_to_form("Cost Center",cost_center_doc.name))),exc=PetPoojaSICreatinoError)

				else :
					frappe.throw(_("Please set appropriate Payment type and Mode of Payment in Cost Center {0} or in Farki Settings {1}".format(get_link_to_form("Cost Center",cost_center_doc.name)),get_link_to_form("Farki Settings",farki_settings_doc.name)),exc=PetPoojaSICreatinoError)

			# POS Business date logic
			date_time_limit = frappe.db.get_value('Mode of Payment', mode_of_payment, 'custom_consider_in_previous_business_date_till')
			if date_time_limit:
				if create_date_time.time() < get_time(date_time_limit):
					sales_invoice_doc.posting_date = add_to_date(create_date_time.date(), days=-1)
					sales_invoice_doc.posting_time = get_time("23:59:59")
					sales_invoice_doc.due_date = add_to_date(create_date_time.date(), days=-1)
					sales_invoice_doc.custom_business_date = add_to_date(create_date_time.date(), days=-1)

			payments_row.amount = sales_invoice_doc.rounded_total

		# Zomato Swiggy price list Logic
		elif order_from == 'Zomato':
			si_customer = zomato_customer
			if len(cost_center_doc.custom_customer_wise_price_list)>0:
				for pl in cost_center_doc.custom_customer_wise_price_list:
					if pl.customer == zomato_customer:
						if pl.price_list:
							pl_found = True
							sales_invoice_doc.selling_price_list = pl.price_list
							break
						else :	
							frappe.throw(_("Please price list for {0} customer in cost center {1}".format(frappe.bold(zomato_customer),get_link_to_form("Cost Center",cost_center_doc.name))),exc=PetPoojaSICreatinoError)
					else :
						pl_found = False
				if pl_found == False:
					frappe.throw(_("Please price list for {0} customer in cost center {1}".format(frappe.bold(zomato_customer),get_link_to_form("Cost Center",cost_center_doc.name))),exc=PetPoojaSICreatinoError)
			else :
				frappe.throw(_("Please set customer and appropriate price list in Cost Center {0}".format(get_link_to_form("Cost Center",cost_center_doc.name))),exc=PetPoojaSICreatinoError)

		elif order_from == 'Swiggy':
			si_customer = swiggy_customer
			if len(cost_center_doc.custom_customer_wise_price_list)>0:
				for pl in cost_center_doc.custom_customer_wise_price_list:
					if pl.customer == swiggy_customer:
						if pl.price_list:
							pl_found = True
							sales_invoice_doc.selling_price_list = pl.price_list
							break
						else :	
							frappe.throw(_("Please price list for {0} customer in cost center {1}".format(frappe.bold(swiggy_customer),get_link_to_form("Cost Center",cost_center_doc.name))),exc=PetPoojaSICreatinoError)
					else :
						pl_found = False
				if pl_found == False:
					frappe.throw(_("Please price list for {0} customer in cost center {1}".format(frappe.bold(swiggy_customer),get_link_to_form("Cost Center",cost_center_doc.name))),exc=PetPoojaSICreatinoError)
			else :
				frappe.throw(_("Please set customer and appropriate price list in Cost Center {0}".format(get_link_to_form("Cost Center",cost_center_doc.name))),exc=PetPoojaSICreatinoError)

		# Zomato Swiggy Business Date
		if order_from == 'Swiggy' or order_from == 'Zomato':
			business_date_limit = cost_center_doc.custom_consider_in_previous_business_date_till
			if business_date_limit:
				if create_date_time.time() < get_time(business_date_limit):
					sales_invoice_doc.custom_business_date = add_to_date(create_date_time.date(), days=-1)

		sales_invoice_doc.customer = si_customer
		sales_invoice_doc.custom_pp_mode_of_payment = custom_payment_type if payment_type=="Other" else payment_type
		sales_invoice_doc.territory = cost_center_doc.custom_territory
		sales_invoice_doc.update_stock = 1
		sales_invoice_doc.set_warehouse = cost_center_doc.custom_warehouse
		company_defaut_income_account = frappe.db.get_value('Company', cost_center_doc.company, 'default_income_account')
		place_of_supply = farki_settings_doc.place_of_supply

		# fetch defult precision
		company = get_default_company()
		company_currency = erpnext.get_company_currency(company)
		discount_precision=(
			get_field_precision(
			frappe.get_meta("Sales Invoice Item").get_field("discount_amount"),
			currency=company_currency,
			)
			or default_currency_precision
			or 2
		)
		rate_precision = (
			get_field_precision(
			frappe.get_meta("Sales Invoice Item").get_field("rate"),
			currency=company_currency,
			)
			or default_currency_precision
			or 2
		)
		print(rate_precision,"-----")

		# Fill Items child table
		order_item_details = properties.get('OrderItem')
		print(order_item_details,"=====---------------------",len(order_item_details),type(order_item_details))
		for item in order_item_details:
			item_rate_as_per_selling_price_list=0
			item_code = item.get('sap_code')
			item_row = sales_invoice_doc.append('items', {})
			if item_code == None or item_code == "":
				frappe.throw(_("sap code must have value"),exc=PetPoojaSICreatinoError)
			else :
				item_row.item_code = item_code
			item_row.qty = item.get('quantity')
			# get item price based on customer and price list
			pl_args = frappe._dict({
				'customer':si_customer,
				'price_list':sales_invoice_doc.selling_price_list,
				'qty':1,
				'uom':frappe.db.get_value('Item', item_code, 'stock_uom')
			})
			item_price = get_price_list_rate_for(pl_args,item_code)
			print(item_price,"====item_price",sales_invoice_doc.selling_price_list)
			# Compliementary case
			if order_details.get('status') == 'Complimentary':
				item_row.rate = 0
				item_row.discount_percentage = 100
			else:
				item_rate_as_per_selling_price_list=item_price
				pp_item_discount=flt(item.get('discount'),discount_precision)
				if pp_item_discount>0:
					item_row.discount_amount = pp_item_discount/ item.get('quantity')
					item_row.rate_with_margin=item_rate_as_per_selling_price_list
					item_row.rate = flt(item_rate_as_per_selling_price_list - item_row.discount_amount ,rate_precision)
					item_row.discount_percentage = 100 * flt(item_row.discount_amount,default_float_precision) / flt(item_rate_as_per_selling_price_list)
				else:
					item_row.rate = item_rate_as_per_selling_price_list
			print(item.get('discount'),"====item.get('discount')",type(item.get('discount')),item_row.rate)
			item_row.cost_center = cost_center_doc.name
			item_row.warehouse = cost_center_doc.custom_warehouse
			print(item_row.discount_amount,"amount")
			item_row.income_account = company_defaut_income_account
			item_tax_template = frappe.db.get_value('Item Tax',{"parent":item_code}, 'item_tax_template')
			item_row.item_tax_template = item_tax_template

		sales_invoice_doc.place_of_supply = place_of_supply
		sales_invoice_doc.taxes_and_charges = sales_taxes_and_charges
		print(type(order_details.get('created_on')),"====order_details.get('created_on')")
		print(type(cstr(order_details.get('orderID'))),"====order_details.get('orderID')")
		print(type(rest_id),"====rest_id")
		unique_id = _("{0}_{1}_{2}".format(order_details.get('created_on') ,cstr(order_details.get('orderID')) , rest_id))
		# cancelled order case
		if order_details.get('status') == 'Cancelled':
			exists_si = frappe.db.get_all("Sales Invoice",
									filters={"custom_pp_unique_order_id":unique_id},
									fields=["name"])
			if len(exists_si)>0:
				print(exists_si,"exists")
				exists_si_doc = frappe.get_doc("Sales Invoice",exists_si[0].name)
				if exists_si_doc.docstatus == 1:
					exists_si_doc.cancel()
					invoice_status = "Cancelled"
					frappe.db.set_value("Pet Pooja Log",docname,"invoice_status",invoice_status)
					return
				else:
					frappe.throw(_("Sales Invoice {0} is not submitted".format(exists_si[0].name)),exc=PetPoojaSICreatinoError)
			else :
				frappe.throw(_("There no any Sales Invoice Exists for order ID {0} and Rest ID {1}".format(frappe.bold(cstr(order_details.get('orderID'))),frappe.bold(rest_id))),exc=PetPoojaSICreatinoError)
		
		customer_details = properties.get('Customer')
		sales_invoice_doc.custom_end_customer_name = customer_details.get('name')
		sales_invoice_doc.custom_end_customer_phone = customer_details.get('phone')
		sales_invoice_doc.custom_end_customer_address = customer_details.get('address')
		sales_invoice_doc.company_address = cost_center_doc.custom_address
		sales_invoice_doc.debit_to = frappe.db.get_value('Company', cost_center_doc.company, 'default_receivable_account')
		sales_invoice_doc.custom_pet_pooja_log_id = ppl_doc.name
		sales_invoice_doc.custom_pet_pooja_order_date_time = create_date_time
		sales_invoice_doc.custom_pp_unique_order_id = unique_id

		sales_invoice_doc.run_method("set_missing_values")
		sales_invoice_doc.run_method("set_other_charges")
		sales_invoice_doc.run_method("calculate_taxes_and_totals")

		print(sales_invoice_doc.rounded_total,"====")
		payments_row.amount = sales_invoice_doc.rounded_total
		sales_invoice_doc.save(ignore_permissions=True)
		si_doc_url = get_url_to_form("Sales Invoice",sales_invoice_doc.name)
		frappe.db.set_value("Pet Pooja Log",docname,"invoice_id",si_doc_url)
		sales_invoice_doc.submit()

		invoice_status = "Created"
		frappe.db.set_value("Pet Pooja Log",docname,"invoice_status",invoice_status)
		frappe.db.set_value("Pet Pooja Log",docname,"business_date",sales_invoice_doc.posting_date)
		frappe.db.set_value("Pet Pooja Log",docname,"invoice_error","")
		frappe.db.set_value("Pet Pooja Log",docname,"traceback","")
		return sales_invoice_doc.name
	
	except Exception as e:
		invoice_status="Error"
	
		if isinstance(e, frappe.UniqueValidationError):
			invoice_status="Duplicate"

		frappe.db.rollback()
		traceback = frappe.get_traceback(with_context=True)
		frappe.db.set_value("Pet Pooja Log",docname,"invoice_status",invoice_status)
		frappe.db.set_value("Pet Pooja Log",docname,"invoice_error",str(e))
		frappe.db.set_value("Pet Pooja Log",docname,"traceback",str(traceback))

		