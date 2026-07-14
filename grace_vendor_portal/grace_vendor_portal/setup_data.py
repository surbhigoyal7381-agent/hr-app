import frappe

def create_delivery_hubs():
    hubs = [
        {
            'hub_name': 'Chandigarh Hub',
            'hub_code': 'CHD-HUB',
            'city': 'Chandigarh',
            'state': 'Chandigarh',
            'pin_code': '160001',
            'contact_phone': '+91-172-0000001',
            'contact_email': 'chandigarh.hub@gracedrinks.in',
            'max_vehicle_capacity': 22,
            'max_daily_orders': 220,
            'is_active': 1,
        },
        {
            'hub_name': 'Panchkula Hub',
            'hub_code': 'PKL-HUB',
            'city': 'Panchkula',
            'state': 'Haryana',
            'pin_code': '134109',
            'contact_phone': '+91-172-0000002',
            'contact_email': 'panchkula.hub@gracedrinks.in',
            'max_vehicle_capacity': 12,
            'max_daily_orders': 120,
            'is_active': 1,
        },
        {
            'hub_name': 'Himachal Hub',
            'hub_code': 'HP-HUB',
            'city': 'Shimla',
            'state': 'Himachal Pradesh',
            'pin_code': '171001',
            'contact_phone': '+91-177-0000003',
            'contact_email': 'himachal.hub@gracedrinks.in',
            'max_vehicle_capacity': 6,
            'max_daily_orders': 60,
            'is_active': 1,
        },
    ]
    results = []
    for d in hubs:
        existing = frappe.db.get_value('Delivery Hub', {'hub_code': d['hub_code']}, 'name')
        if not existing:
            doc = frappe.get_doc({'doctype': 'Delivery Hub', **d})
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            results.append(f'Created: {doc.name} - {d["hub_name"]}')
        else:
            results.append(f'Already exists: {existing} - {d["hub_name"]}')
    return results
