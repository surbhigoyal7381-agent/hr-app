import React, { useState, useEffect } from 'react'
import { api } from '../services/api'

function StarDisplay({ value }) {
  return <span className="text-yellow-400">{'★'.repeat(value)}{'☆'.repeat(5 - value)}</span>
}

export default function Ratings() {
  const [ratings, setRatings] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Reuse getOrders to find delivered orders and load their ratings
    api.getOrders('Delivered', 50, 0).then(async data => {
      const ratedOrders = (data.orders || []).filter(o => o.rating_submitted)
      const detailed = await Promise.all(ratedOrders.map(o => api.getOrderDetail(o.name)))
      setRatings(detailed.filter(o => o.rating).map(o => ({ ...o.rating, order_name: o.name, order_date: o.order_date })))
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-center py-12 text-gray-400">Loading ratings...</div>

  const avg = field => ratings.length ? (ratings.reduce((s, r) => s + (r[field] || 0), 0) / ratings.length).toFixed(1) : '—'

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-semibold text-gray-800">My Ratings</h2>
      {ratings.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          {[['Order Quality','order_quality_rating'],['Timeliness','delivery_timeliness_rating'],['Driver','driver_professionalism_rating']].map(([label, field]) => (
            <div key={field} className="bg-white rounded-lg shadow p-4 text-center">
              <div className="text-2xl font-bold text-gray-800">{avg(field)}</div>
              <div className="text-xs text-gray-500 mt-1">{label}</div>
              <div className="text-yellow-400 text-sm mt-1">{'★'.repeat(Math.round(avg(field)))}{'☆'.repeat(5 - Math.round(avg(field)))}</div>
            </div>
          ))}
        </div>
      )}
      <div className="space-y-3">
        {ratings.length === 0 && <div className="text-center py-8 text-gray-400">No ratings submitted yet.</div>}
        {ratings.map((r, i) => (
          <div key={i} className="bg-white rounded-lg shadow p-4">
            <div className="flex justify-between items-start mb-2">
              <span className="font-mono text-sm text-gray-600">{r.order_name}</span>
              <span className="text-xs text-gray-400">{r.order_date}</span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs text-gray-500">
              <div>Quality: <StarDisplay value={r.order_quality_rating || 0} /></div>
              <div>Timeliness: <StarDisplay value={r.delivery_timeliness_rating || 0} /></div>
              <div>Driver: <StarDisplay value={r.driver_professionalism_rating || 0} /></div>
            </div>
            {r.comments && <p className="text-sm text-gray-600 italic mt-2">"{r.comments}"</p>}
            {r.issue_category && r.issue_category !== 'None' && (
              <span className="mt-2 inline-block text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">Issue: {r.issue_category}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
