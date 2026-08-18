import React from 'react'
import OrderForm from '../components/OrderForm'

export default function NewOrder() {
  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-xl font-semibold text-gray-800 mb-6">Place New Order</h2>
      <OrderForm />
    </div>
  )
}
