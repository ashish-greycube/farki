// Copyright (c) 2024, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pet Pooja Log", {
	refresh(frm) {
        if (frm.is_new() == undefined) {
            frm.add_custom_button(__('Create SI'), () => create_sales_invoice_from_pet_pooja_log(frm));
        }
	},
});

let create_sales_invoice_from_pet_pooja_log = function (frm) {
    frm.call("create_sales_invoice").then((r) => {
        console.log(r.message);
        frappe.open_in_new_tab = true;
        frappe.set_route('Form', 'Sales Invoice', r.message);
    });
}