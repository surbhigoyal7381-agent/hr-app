import React, { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import DeliveryMap from '../components/DeliveryMap'
import RatingForm from '../components/RatingForm'

export default function OrderDetail() {
  const { orderId } = useParams()
  const [order, setOrder] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showRating, setShowRating] = useState(false)

  const loadOrder = useCallback(() => {
    api.getOrderDetail(orderId).then(setOrder).catch(console.error).finally(() => setLoading(false))
  }, [orderId])

  useEffect(() => { loadOrder() }, [loadOrder])

  // Poll every 30s if in transit
  useEffect(() => {
    if (!order) return
    if (!['Dispatched','In Transit'].includes(order.order_status)) return
    const timer = setInterval(loadOrder, 30000)
    return () => clearInterval(timer)
  }, [order, loadOrder])

  if (loading) return <div className="text-center py-12 text-gray-400">Loading order...</div>
  if (!order) return <div className="text-center py-12 text-red-400">Order not found.</div>

  const showMap = ['Dispatched','In Transit'].includes(order.order_status) && order.delivery
  const canRate = order.order_status === 'Delivered' && !order.rating_submitted && !order.rating

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <div className="flex items-center gap-3">
        <Link to="/orders" className="text-grace-700 hover:underline text-sm">&larr; Orders</Link>
        <h2 className="text-lg font-semibold text-gray-800 flex-1">{order.name}</h2>
        <StatusBadge status={order.order_status} />
      </div>
      {/* Order Summary */}
      <div className="bg-white rounded-lg shadow p-5">
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div><span className="text-gray-500">Date:</span> <span className="font-medium">{order.order_date}</span></div>
          <div><span className="text-gray-500">Slot:</span> <span className="font-medium">{order.delivery_slot}</span></div>
          <div className="col-span-2"><span className="text-gray-500">Address:</span> <span className="font-medium">{order.delivery_address}</span></div>
          {order.special_instructions && <div className="col-span-2"><span className="text-gray-500">Instructions:</span> <span>{order.special_instructions}</span></div>}
        </div>
        <div className="mt-4 border-t pt-4">
          <table className="w-full text-sm">
            <thead><tr className="text-gray-500 text-xs"><th className="text-left">Item</th><th className="text-center">Qty</th><th className="text-right">Total</th></tr></thead>
            <tbody>{(order.items || []).map((item, i) => (
              <tr key={i} className="border-t"><td className="py-1">{item.sku}</td><td className="text-center">{item.quantity}</td><td className="text-right">&#8377;{Number(item.line_total || 0).toLocaleString('en-IN')}</td></tr>
            ))}</tbody>
            <tfoot><tr className="font-semibold border-t"><td colSpan={2}>Total</td><td className="text-right">&#8377;{Number(order.total_amount || 0).toLocaleString('en-IN')}</td></tr></tfoot>
          </table>
        </div>
      </div>
      {/* Delivery info */}
      {order.delivery && (
        <div className="bg-white rounded-lg shadow p-5">
          <h3 className="font-semibold text-gray-700 mb-3">Delivery Details</h3>
          <div className="grid grid-cols-2 gap-2 text-sm mb-4">
            <div><span className="text-gray-500">Driver:</span> <span className="font-medium">{order.delivery.driver_name}</span></div>
            <div><span className="text-gray-500">Phone:</span> <a href={`tel:${order.delivery.driver_phone}`} className="text-grace-700 font-medium">{order.delivery.driver_phone}</a></div>
            <div><span className="text-gray-500">Vehicle:</span> <span className="font-medium">{order.delivery.vehicle_reg}</span></div>
            <div><span className="text-gray-500">Status:</span> <span className="font-medium">{order.delivery.status}</span></div>
          </div>
          {showMap && <DeliveryMap tracking={order.delivery.current_location} driverName={order.delivery.driver_name} eta={order.delivery.current_location?.eta_minutes} />}
        </div>
      )}
      {/* Existing rating */}
      {order.rating && (
        <div className="bg-white rounded-lg shadow p-5">
          <h3 className="font-semibold text-gray-700 mb-2">Your Rating</h3>
          <div className="text-sm space-y-1">
            <div>Order Quality: {'★'.repeat(order.rating.order_quality_rating)}{'☆'.repeat(5 - order.rating.order_quality_rating)}</div>
            <div>Timeliness: {'★'.repeat(order.rating.delivery_timeliness_rating)}{'☆'.repeat(5 - order.rating.delivery_timeliness_rating)}</div>
            <div>Driver: {'★'.repeat(order.rating.driver_professionalism_rating)}{'☆'.repeat(5 - order.rating.driver_professionalism_rating)}</div>
            {order.rating.comments && <div className="text-gray-600 mt-2 italic">"{order.rating.comments}"</div>}
          </div>
        </div>
      )}
      {/* Rating prompt */}
      {canRate && !showRating && (
        <div className="bg-grace-50 border border-grace-200 rounded-lg p-5 text-center">
          <p className="text-gray-700 mb-3">Your order has been delivered! How was your experience?</p>
          <button onClick={() => setShowRating(true)} className="bg-grace-700 text-white px-5 py-2 rounded-lg font-medium hover:bg-grace-900">Rate Now</button>
        </div>
      )}
      {showRating && <RatingForm orderId={orderId} onSuccess={loadOrder} />}
    </div>
  )
}
