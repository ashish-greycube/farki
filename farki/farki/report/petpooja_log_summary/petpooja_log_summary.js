// Copyright (c) 2025, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.query_reports["PetPooja Log Summary"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label":__("From Date"),
			"fieldtype": "Date",
            "default": frappe.datetime.add_days(frappe.datetime.nowdate(), -30),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label":__("To Date"),
			"fieldtype": "Date",
            "default": frappe.datetime.nowdate(),
			"reqd": 1
		},
		{
			"fieldname": "branch",
			"label":__("Branch"),
			"fieldtype": "Link",
			"options": "Cost Center",
			get_query: function () {
				return {
					filters: {
						"is_group": 0,
						"custom_petpooja_restaurant_id": ["not in", ["", undefined]]
					}
				};
			},
		},
	]
};
