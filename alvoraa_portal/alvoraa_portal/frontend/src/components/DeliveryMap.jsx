import React, { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'

// Fix default marker icons (Leaflet webpack issue)
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

function RecenterMap({ lat, lng }) {
  const map = useMap()
  useEffect(() => { if (lat && lng) map.setView([lat, lng], 15) }, [lat, lng])
  return null
}

export default function DeliveryMap({ tracking, driverName, eta }) {
  if (!tracking || !tracking.current_lat) {
    return (
      <div className="h-64 bg-gray-100 rounded-lg flex items-center justify-center text-gray-400">
        <div className="text-center">
          <div className="text-3xl mb-2">&#128205;</div>
          <p>Location not yet available</p>
        </div>
      </div>
    )
  }
  return (
    <div className="rounded-lg overflow-hidden shadow">
      <div className="bg-grace-700 text-white px-4 py-2 flex justify-between items-center text-sm">
        <span>&#128666; {driverName || 'Driver'} is on the way</span>
        {eta && <span className="font-medium">ETA: ~{eta} min</span>}
      </div>
      <MapContainer center={[tracking.current_lat, tracking.current_long]} zoom={15} style={{ height: '300px' }}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />
        <Marker position={[tracking.current_lat, tracking.current_long]}>
          <Popup>{driverName || 'Driver'}{eta ? ` • ETA: ${eta} min` : ''}</Popup>
        </Marker>
        <RecenterMap lat={tracking.current_lat} lng={tracking.current_long} />
      </MapContainer>
    </div>
  )
}
