frappe.ui.form.on('Order Rating', {
    order_quality_rating: function(frm) { frm.trigger('calculate_average'); },
    delivery_timeliness_rating: function(frm) { frm.trigger('calculate_average'); },
    driver_professionalism_rating: function(frm) { frm.trigger('calculate_average'); },

    calculate_average: function(frm) {
        let q = frm.doc.order_quality_rating || 0;
        let t = frm.doc.delivery_timeliness_rating || 0;
        let p = frm.doc.driver_professionalism_rating || 0;
        if (q && t && p) {
            frm.set_value('average_rating', (q + t + p) / 3);
        }
    }
});
