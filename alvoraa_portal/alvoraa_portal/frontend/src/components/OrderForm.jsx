import React, { useState } from 'react'
import { api } from '../services/api'
import { useNavigate } from 'react-router-dom'

const SAMPLE_SKUS = [
  { sku: 'LAYS-OG-26G', name: "Lay's Original 26g", price: 20 },
  { sku: 'LAYS-MX-26G', name: "Lay's Magic Masala 26g", price: 20 },
  { sku: 'KURKURE-50G', name: 'Kurkure Masala Munch 50g', price: 20 },
  { sku: 'PEPSI-250ML', name: 'Pepsi 250ml', price: 30 },
  { sku: 'MIRINDA-250ML', name: 'Mirinda Orange 250ml', price: 30 },
  { sku: '7UP-250ML', name: '7Up 250ml', price: 30 },
]

export default function OrderForm() {
  const [items, setItems] = useState([])
  const [address, setAddress] = useState('')
  const [slot, setSlot] = useState('Tomorrow')
  const [instructions, setInstructions] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const addSku = (sku) => {
    const existing = items.find(i => i.sku === sku.sku)
    if (existing) {
      setItems(items.map(i => i.sku === sku.sku ? { ...i, quantity: i.quantity + 1 } : i))
    } else {
      setItems([...items, { sku: sku.sku, name: sku.name, quantity: 1, unit_price: sku.price }])
    }
  }

  const updateQty = (sku, qty) => {
    if (qty <= 0) { setItems(items.filter(i => i.sku !== sku)); return }
    setItems(items.map(i => i.sku === sku ? { ...i, quantity: qty } : i))
  }

  const total = items.reduce((sum, i) => sum + i.quantity * i.unit_price, 0)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!items.length) { setError('Add at least one item'); return }
    if (!address.trim()) { setError('Delivery address is required'); return }
    setSubmitting(true); setError('')
    try {
      const result = await api.createOrder(items, address, slot, instructions)
      navigate(`/orders/${result.order_id}`)
    } catch (err) {
      setError(err.message); setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="font-semibold text-gray-800 mb-4">Select Products</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
          {SAMPLE_SKUS.map(sku => (
            <button type="button" key={sku.sku} onClick={() => addSku(sku)}
              className="border rounded-lg p-3 text-left hover:border-grace-500 hover:bg-grace-50 transition-colors">
              <div className="text-sm font-medium text-gray-800">{sku.name}</div>
              <div className="text-xs text-gray-500 mt-1">&#8377;{sku.price} / unit</div>
            </button>
          ))}
        </div>
        {items.length > 0 && (
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50"><tr><th className="px-3 py-2 text-left">Item</th><th className="px-3 py-2">Qty</th><th className="px-3 py-2 text-right">Total</th></tr></thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.sku} className="border-t">
                    <td className="px-3 py-2">{item.name}</td>
                    <td className="px-3 py-2 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <button type="button" onClick={() => updateQty(item.sku, item.quantity - 1)} className="w-7 h-7 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center font-bold">&minus;</button>
                        <span className="w-8 text-center">{item.quantity}</span>
                        <button type="button" onClick={() => updateQty(item.sku, item.quantity + 1)} className="w-7 h-7 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center font-bold">+</button>
                      </div>
                    </td>
                    <td className="px-3 py-2 text-right">&#8377;{(item.quantity * item.unit_price).toLocaleString('en-IN')}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-gray-50 font-semibold">
                <tr><td className="px-3 py-2" colSpan={2}>Total</td><td className="px-3 py-2 text-right">&#8377;{total.toLocaleString('en-IN')}</td></tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <h3 className="font-semibold text-gray-800">Delivery Details</h3>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Delivery Address *</label>
          <textarea value={address} onChange={e => setAddress(e.target.value)} rows={2}
            className="w-full border rounded-md px-3 py-2 text-sm resize-none" placeholder="Full delivery address..." />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Delivery Slot *</label>
          <select value={slot} onChange={e => setSlot(e.target.value)} className="w-full border rounded-md px-3 py-2 text-sm">
            {['Today','Tomorrow','Next 2 Days','Next 3 Days'].map(s => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Special Instructions</label>
          <textarea value={instructions} onChange={e => setInstructions(e.target.value)} rows={2}
            className="w-full border rounded-md px-3 py-2 text-sm resize-none" placeholder="Any special handling instructions..." />
        </div>
      </div>
      {error && <p className="text-red-500 text-sm">{error}</p>}
      <button type="submit" disabled={submitting}
        className="w-full bg-grace-700 text-white py-3 rounded-lg font-medium hover:bg-grace-900 disabled:opacity-50 transition-colors text-base">
        {submitting ? 'Placing Order...' : `Place Order — ₹${total.toLocaleString('en-IN')}`}
      </button>
    </form>
  )
}
