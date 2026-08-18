import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import OrderList from '../components/OrderList'

function StatCard({ label, value, color, to }) {
  const content = (
    <div className={`bg-white rounded-xl shadow p-5 border-l-4 ${color} hover:shadow-md transition-shadow`}>
      <div className="text-2xl font-bold text-gray-800">{value}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  )
  return to ? <Link to={to}>{content}</Link> : content
}

export default function Dashboard() {
  const [data, setData] = useState(null)
  const [recentOrders, setRecentOrders] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.getDashboard(), api.getOrders(null, 5, 0)])
      .then(([dash, ordersData]) => { setData(dash); setRecentOrders(ordersData.orders || []) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center py-12 text-gray-400">Loading dashboard...</div>
  if (!data) return null

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-800">Welcome, {data.company_name}</h2>
        <p className="text-gray-500 text-sm">Here's your summary for today</p>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Pending Orders" value={data.pending_orders} color="border-yellow-400" to="/orders" />
        <StatCard label="In Transit" value={data.in_transit_orders} color="border-blue-400" to="/orders" />
        <StatCard label="Delivered This Month" value={data.delivered_this_month} color="border-green-400" />
        <StatCard label="Account Balance" value={`₹${Number(data.account_balance || 0).toLocaleString('en-IN')}`} color="border-grace-500" />
      </div>
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-700">Recent Orders</h3>
        <Link to="/orders" className="text-grace-700 text-sm font-medium hover:underline">View all &rarr;</Link>
      </div>
      <OrderList orders={recentOrders} loading={false} />
      <div className="text-center">
        <Link to="/new-order" className="inline-block bg-grace-700 text-white px-6 py-3 rounded-lg font-medium hover:bg-grace-900 transition-colors">+ Place New Order</Link>
      </div>
    </div>
  )
}
