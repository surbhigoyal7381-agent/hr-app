import React from 'react'
import { Link } from 'react-router-dom'
import StatusBadge from './StatusBadge'

export default function OrderList({ orders, loading }) {
  if (loading) return <div className="text-center py-8 text-gray-500">Loading orders...</div>
  if (!orders || !orders.length) return <div className="text-center py-8 text-gray-400">No orders found.</div>
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full bg-white rounded-lg shadow overflow-hidden">
        <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wider">
          <tr>
            <th className="px-4 py-3 text-left">Order ID</th>
            <th className="px-4 py-3 text-left">Date</th>
            <th className="px-4 py-3 text-left">Slot</th>
            <th className="px-4 py-3 text-right">Amount</th>
            <th className="px-4 py-3 text-left">Status</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {orders.map(order => (
            <tr key={order.name} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 font-mono text-sm">{order.name}</td>
              <td className="px-4 py-3 text-sm text-gray-600">{order.order_date}</td>
              <td className="px-4 py-3 text-sm text-gray-600">{order.delivery_slot}</td>
              <td className="px-4 py-3 text-sm text-right font-medium">&#8377;{Number(order.total_amount || 0).toLocaleString('en-IN')}</td>
              <td className="px-4 py-3"><StatusBadge status={order.order_status} /></td>
              <td className="px-4 py-3 text-right"><Link to={`/orders/${order.name}`} className="text-grace-700 text-sm font-medium hover:underline">View &rarr;</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
