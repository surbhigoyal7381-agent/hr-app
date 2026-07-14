import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { api } from '../services/api'

const navItems = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/orders', label: 'Orders' },
  { to: '/new-order', label: 'New Order' },
  { to: '/ratings', label: 'Ratings' },
  { to: '/account', label: 'Account' },
]

export default function Navbar({ user, onLogout }) {
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  const handleLogout = async () => {
    try { await api.logout() } catch {}
    onLogout()
  }

  return (
    <nav className="bg-grace-700 text-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="font-bold text-lg tracking-tight">Grace Vendor Portal</span>
        </div>
        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-6">
          {navItems.map(item => (
            <Link key={item.to} to={item.to}
              className={`text-sm font-medium hover:text-grace-50 transition-colors ${location.pathname.startsWith(item.to) ? 'underline underline-offset-4' : ''}`}>
              {item.label}
            </Link>
          ))}
          <button onClick={handleLogout} className="ml-4 text-sm bg-white text-grace-700 px-3 py-1 rounded hover:bg-grace-50">Logout</button>
        </div>
        {/* Mobile hamburger */}
        <button className="md:hidden" onClick={() => setMenuOpen(m => !m)}>
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={menuOpen ? "M6 18L18 6M6 6l12 12" : "M4 6h16M4 12h16M4 18h16"} />
          </svg>
        </button>
      </div>
      {menuOpen && (
        <div className="md:hidden bg-grace-900 px-4 pb-4 flex flex-col gap-3">
          {navItems.map(item => (
            <Link key={item.to} to={item.to} onClick={() => setMenuOpen(false)}
              className="text-sm font-medium py-2 border-b border-grace-700">{item.label}</Link>
          ))}
          <button onClick={handleLogout} className="text-left text-sm py-2">Logout</button>
        </div>
      )}
    </nav>
  )
}
