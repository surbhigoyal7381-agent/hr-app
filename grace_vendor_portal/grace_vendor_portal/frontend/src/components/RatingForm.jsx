import React, { useState } from 'react'
import { api } from '../services/api'

function StarRating({ value, onChange, label }) {
  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <div className="flex gap-2">
        {[1,2,3,4,5].map(star => (
          <button key={star} type="button" onClick={() => onChange(star)}
            className={`text-2xl transition-colors ${star <= value ? 'text-yellow-400' : 'text-gray-300'} hover:text-yellow-400`}>&#9733;</button>
        ))}
        <span className="text-sm text-gray-500 ml-2 self-center">{value > 0 ? `${value}/5` : 'Not rated'}</span>
      </div>
    </div>
  )
}

export default function RatingForm({ orderId, onSuccess }) {
  const [quality, setQuality] = useState(0)
  const [timeliness, setTimeliness] = useState(0)
  const [professionalism, setProfessionalism] = useState(0)
  const [comments, setComments] = useState('')
  const [issue, setIssue] = useState('None')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!quality || !timeliness || !professionalism) { setError('Please rate all three categories'); return }
    setSubmitting(true); setError('')
    try {
      await api.submitRating(orderId, quality, timeliness, professionalism, comments, issue)
      onSuccess && onSuccess()
    } catch (err) {
      setError(err.message)
    } finally { setSubmitting(false) }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6">
      <h3 className="text-lg font-semibold mb-4">Rate Your Experience</h3>
      <StarRating value={quality} onChange={setQuality} label="Order Quality" />
      <StarRating value={timeliness} onChange={setTimeliness} label="Delivery Timeliness" />
      <StarRating value={professionalism} onChange={setProfessionalism} label="Driver Professionalism" />
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">Issue (if any)</label>
        <select value={issue} onChange={e => setIssue(e.target.value)} className="w-full border rounded-md px-3 py-2 text-sm">
          {['None','Damaged Goods','Late Delivery','Unprofessional Driver','Wrong Items','Other'].map(opt => <option key={opt}>{opt}</option>)}
        </select>
      </div>
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">Comments (optional)</label>
        <textarea value={comments} onChange={e => setComments(e.target.value)} rows={3}
          className="w-full border rounded-md px-3 py-2 text-sm resize-none" placeholder="Share your feedback..." />
      </div>
      {error && <p className="text-red-500 text-sm mb-3">{error}</p>}
      <button type="submit" disabled={submitting}
        className="w-full bg-grace-700 text-white py-2 rounded-md font-medium hover:bg-grace-900 disabled:opacity-50 transition-colors">
        {submitting ? 'Submitting...' : 'Submit Rating'}
      </button>
    </form>
  )
}
