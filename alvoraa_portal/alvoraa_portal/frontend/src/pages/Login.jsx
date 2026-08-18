import React, { useState } from 'react'
import { api } from '../services/api'

export default function Login({ onLogin }) {
  const [step, setStep] = useState('credentials') // 'credentials' | 'otp'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleCredentials = async (e) => {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      const res = await api.login(email, password)
      if (res.status === 'otp_required') { setStep('otp') }
      else if (res.status === 'success') { onLogin({ vendor: res.vendor, email }) }
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  const handleOtp = async (e) => {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      const res = await api.login(email, password, otp)
      if (res.status === 'success') { onLogin({ vendor: res.vendor, email }) }
      else { setError('Invalid OTP') }
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-grace-700 to-grace-900 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">&#127865;</div>
          <h1 className="text-2xl font-bold text-gray-900">Grace Vendor Portal</h1>
          <p className="text-gray-500 text-sm mt-1">Sign in to manage your orders</p>
        </div>
        {step === 'credentials' ? (
          <form onSubmit={handleCredentials} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
                className="w-full border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-grace-500 focus:border-transparent outline-none"
                placeholder="vendor@company.com" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
                className="w-full border rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-grace-500 focus:border-transparent outline-none"
                placeholder="&bull;&bull;&bull;&bull;&bull;&bull;&bull;&bull;" />
            </div>
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <button type="submit" disabled={loading}
              className="w-full bg-grace-700 text-white py-2.5 rounded-lg font-medium hover:bg-grace-900 disabled:opacity-50 transition-colors">
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleOtp} className="space-y-4">
            <p className="text-sm text-gray-600 text-center">Enter the OTP sent to your registered mobile number.</p>
            <input type="text" value={otp} onChange={e => setOtp(e.target.value)} required maxLength={6}
              className="w-full border rounded-lg px-4 py-3 text-center text-2xl tracking-widest focus:ring-2 focus:ring-grace-500 outline-none"
              placeholder="000000" />
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <button type="submit" disabled={loading}
              className="w-full bg-grace-700 text-white py-2.5 rounded-lg font-medium hover:bg-grace-900 disabled:opacity-50 transition-colors">
              {loading ? 'Verifying...' : 'Verify OTP'}
            </button>
            <button type="button" onClick={() => setStep('credentials')} className="w-full text-sm text-gray-500 hover:underline">&larr; Back</button>
          </form>
        )}
      </div>
    </div>
  )
}
