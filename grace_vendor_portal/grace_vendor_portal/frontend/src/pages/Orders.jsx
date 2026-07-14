import React, { useState, useEffect } from 'react'
import { api } from '../services/api'
import OrderList from '../components/OrderList'

const STATUSES = ['All','Draft','Under Review','Approved','Packing','Ready for Dispatch','Dispatched','In Transit','Delivered','Cancelled']

export default function Orders() {
  const [orders, setOrders] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState('All')
  const [page, setPage] = useState(0)
  const PER_PAGE = 20

  useEffect(() => {
    setLoading(true)
    api.getOrders(status === 'All' ? null : status, PER_PAGE, page * PER_PAGE)
      .then(data => { setOrders(data.orders || []); setTotal(data.total || 0) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [status, page])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-800">My Orders</h2>
        <span className="text-gray-500 text-sm">{total} total</span>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-2">
        {STATUSES.map(s => (
          <button key={s} onClick={() => { setStatus(s); setPage(0) }}
            className={`whitespace-nowrap px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${status === s ? 'bg-grace-700 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
            {s}
          </button>
        ))}
      </div>
      <OrderList orders={orders} loading={loading} />
      {total > PER_PAGE && (
        <div className="flex justify-center gap-3">
          <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="px-4 py-2 rounded bg-gray-100 disabled:opacity-40 hover:bg-gray-200 text-sm">&larr; Prev</button>
          <span className="py-2 text-sm text-gray-500">Page {page + 1} of {Math.ceil(total / PER_PAGE)}</span>
          <button disabled={(page + 1) * PER_PAGE >= total} onClick={() => setPage(p => p + 1)} className="px-4 py-2 rounded bg-gray-100 disabled:opacity-40 hover:bg-gray-200 text-sm">Next &rarr;</button>
        </div>
      )}
    </div>
  )
}
