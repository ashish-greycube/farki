# Copyright (c) 2025, GreyCube Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from itertools import groupby
from frappe.utils import flt, date_diff, getdate, cstr, cint
import datetime

def execute(filters=None):
	columns, data = [], []

	columns = get_columns(filters)
	data = get_data(filters, columns)
	if not data:
		# msgprint(_("No records found"))
		return columns, data
		
	return columns, data

def get_columns(filters):
	columns = [
		{
			"fieldname": "branch",
			"fieldtype": "Link",
			"label": _("Branch"),
			"options": "Cost Center",
			"width": 200
		},
		{
			"fieldname": "invoice_status",
			"fieldtype": "Data",
			"label": _("Invoice Status"),
			"width": 200
		},
		# {
		# 	"fieldname": "amount_total",
		# 	"fieldtype": "Float",
		# 	"label": _("Amount Total"),
		# 	"width": 110
		# }
	]

	return columns

def get_conditions(filters):
	conditions =""

	if filters.get("from_date") and filters.get("to_date"):
		if filters.get("to_date") >= filters.get("from_date"):
			conditions += "DATE(ppl.business_date) between {0} and {1}".format(
				frappe.db.escape(filters.get("from_date")),
				frappe.db.escape(filters.get("to_date")))		
		else:
			frappe.throw(_("To Date should be greater then From Date"))

	if filters.branch:
		conditions += " and ppl.branch = '{0}'".format(filters.branch)
	
	return conditions

def get_data(filters, columns):
	data = []

	conditions = get_conditions(filters)
	data = frappe.db.sql(
		"""SELECT
		ppl.branch as branch, ppl.business_date as business_date, ppl.invoice_status as invoice_status, 1 as count_log
		From `tabPet Pooja Log` as ppl
		Where {0}""".format(conditions),filters,as_dict=1,debug=1)

	result = make_report(data, filters, columns)
	# print(result)

	return result



def make_report(data, filters, columns):

	result = []

	from_date, to_date = filters.get("from_date"), filters.get("to_date")
	numdays = date_diff(to_date, from_date)

	dates = [
		(getdate(to_date) - datetime.timedelta(days=x)).strftime("%Y-%m-%d")
		for x in range(numdays)
	]

	for dt in dates:
		columns.append(
				{
					"fieldname": dt,
					"label": dt,
					"fieldtype": "Data",
					"width": 150,
				}
			)
		
	columns.append({
		"fieldname": "amount_total",
		"fieldtype": "Int",
		"label": _("Amount Total"),
		"width": 110,
	}),

	grouping_key = lambda o: (o["branch"], o["invoice_status"])
	for (branch, invoice_status), rows in groupby(
		sorted(data, key=grouping_key), key=grouping_key
	):
		_rows = list(rows)

		row = {
			"branch": branch,
			"invoice_status": invoice_status,
		}

		total_amount = 0
		for dt in dates:
			row[dt] = sum(
				flt(r["count_log"]) for r in _rows if cstr(r["business_date"]).startswith(dt)
			)
			total_amount = total_amount + row[dt]
			row["amount_total"] = total_amount

		result.append(row)
			
	return result