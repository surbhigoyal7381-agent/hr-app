const BASE = '/api/method/grace_vendor_portal.api.vendor_portal_api'
const AUTH_BASE = '/api/method/grace_vendor_portal.api.auth'

async function call(method, args = {}, options = {}) {
  const csrf = document.cookie.match(/csrf_token=([^;]+)/)?.[1] || window.FRAPPE_CSRF || ''
  const res = await fetch(`/api/method/${method}`, {
    method: options.method || 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Frappe-CSRF-Token': csrf,
    },
    body: JSON.stringify(args),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err._error_message || err.exception || `HTTP ${res.status}`)
  }
  const data = await res.json()
  return data.message
}

export const api = {
  login: (email, password, otp) => call('grace_vendor_portal.api.auth.vendor_login', { email, password, otp }),
  logout: () => call('grace_vendor_portal.api.auth.vendor_logout', {}),
  getDashboard: () => call('grace_vendor_portal.api.vendor_portal_api.get_vendor_dashboard', {}),
  getOrders: (status, limit = 20, offset = 0) => call('grace_vendor_portal.api.vendor_portal_api.get_vendor_orders', { status, limit, offset }),
  getOrderDetail: (orderId) => call('grace_vendor_portal.api.vendor_portal_api.get_order_detail', { order_id: orderId }),
  createOrder: (items, deliveryAddress, deliverySlot, instructions) =>
    call('grace_vendor_portal.api.vendor_portal_api.create_vendor_order', {
      items: JSON.stringify(items), delivery_address: deliveryAddress,
      delivery_slot: deliverySlot, special_instructions: instructions
    }),
  submitRating: (orderId, quality, timeliness, professionalism, comments, issueCategory) =>
    call('grace_vendor_portal.api.vendor_portal_api.submit_order_rating', {
      order_id: orderId, quality_rating: quality, timeliness_rating: timeliness,
      professionalism_rating: professionalism, comments, issue_category: issueCategory
    }),
  getDeliveryTracking: (orderId) => call('grace_vendor_portal.api.vendor_portal_api.get_delivery_tracking', { order_id: orderId }),
  getNotifications: () => call('grace_vendor_portal.api.vendor_portal_api.get_vendor_notifications', {}),
}
