import React from 'react'
const colors = {
  'Draft': 'bg-gray-100 text-gray-700',
  'Under Review': 'bg-yellow-100 text-yellow-700',
  'Approved': 'bg-blue-100 text-blue-700',
  'Packing': 'bg-purple-100 text-purple-700',
  'Ready for Dispatch': 'bg-orange-100 text-orange-700',
  'Dispatched': 'bg-indigo-100 text-indigo-700',
  'In Transit': 'bg-cyan-100 text-cyan-700',
  'Delivered': 'bg-green-100 text-green-700',
  'Cancelled': 'bg-red-100 text-red-700',
}
export default function StatusBadge({ status }) {
  return <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-700'}`}>{status}</span>
}
