import React from 'react'

export default function Account({ user }) {
  return (
    <div className="max-w-lg mx-auto space-y-5">
      <h2 className="text-xl font-semibold text-gray-800">My Account</h2>
      <div className="bg-white rounded-lg shadow p-6 space-y-3">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-grace-100 flex items-center justify-center text-grace-700 text-2xl font-bold">
            {(user.email || '?')[0].toUpperCase()}
          </div>
          <div>
            <div className="font-semibold text-gray-800">{user.email}</div>
            <div className="text-sm text-gray-500">Vendor ID: {user.vendor}</div>
          </div>
        </div>
        <div className="border-t pt-3 text-sm text-gray-600 space-y-2">
          <div className="flex justify-between"><span>Email</span><span className="font-medium">{user.email}</span></div>
          <div className="flex justify-between"><span>Portal Access</span><span className="text-green-600 font-medium">Active</span></div>
          <div className="flex justify-between"><span>2FA</span><span className="text-green-600 font-medium">Enabled</span></div>
        </div>
      </div>
      <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-500 text-center">
        To update your profile or address, contact Grace Group operations at <a href="mailto:ops@gracedrinks.in" className="text-grace-700 underline">ops@gracedrinks.in</a>
      </div>
    </div>
  )
}
