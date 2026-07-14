import React, { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Orders from './pages/Orders'
import OrderDetail from './pages/OrderDetail'
import NewOrder from './pages/NewOrder'
import Ratings from './pages/Ratings'
import Account from './pages/Account'
import Navbar from './components/Navbar'

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = sessionStorage.getItem('gvp_user')
    if (stored) setUser(JSON.parse(stored))
    setLoading(false)
  }, [])

  const handleLogin = (userData) => {
    setUser(userData)
    sessionStorage.setItem('gvp_user', JSON.stringify(userData))
  }

  const handleLogout = () => {
    setUser(null)
    sessionStorage.removeItem('gvp_user')
  }

  if (loading) return (
    <div className="flex h-screen items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-grace-500"></div>
    </div>
  )

  if (!user) return <Login onLogin={handleLogin} />

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Navbar user={user} onLogout={handleLogout} />
        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/orders/:orderId" element={<OrderDetail />} />
            <Route path="/new-order" element={<NewOrder />} />
            <Route path="/ratings" element={<Ratings />} />
            <Route path="/account" element={<Account user={user} />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
