// Copyright (c) 2024, GreyCube Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pet Pooja Log", {
	refresh(frm) {
        console.log(frm.doc.invoice_status)
        if (!frm.is_new() && (frm.doc.invoice_status == "Not processed" | frm.doc.invoice_status == "Error")) {
            console.log("---")
            frm.add_custom_button(__('Create SI'), () => create_sales_invoice_from_pet_pooja_log(frm));
        }
	},
});

let create_sales_invoice_from_pet_pooja_log = function (frm) {

    frappe.call({
        method: "farki.farki.doctype.pet_pooja_log.pet_pooja_log.create_sales_invoice",
        args: {
            docname: frm.doc.name
        },
        callback: function (r) {
            console.log(r.message);
            frappe.open_in_new_tab = true;
            frappe.set_route('Form', 'Sales Invoice', r.message);
        }
    })
}