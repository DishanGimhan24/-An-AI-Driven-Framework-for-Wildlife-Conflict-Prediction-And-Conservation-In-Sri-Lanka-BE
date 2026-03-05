import 'leaflet/dist/leaflet.css';
import { useEffect, useRef, useState } from 'react';
import { GeoJSON, MapContainer, TileLayer } from 'react-leaflet';

export default function CityRiskMap({ district, city, riskLevel, riskScore }) {
  const [geoJsonData, setGeoJsonData] = useState(null);
  const [cityFeature, setCityFeature] = useState(null);
  const [loading, setLoading] = useState(false);
  const mapRef = useRef(null);

  useEffect(() => {
    if (district && city) {
      loadCityGeoJSON();
    }
  }, [district, city]);

  // Fit map to city bounds whenever cityFeature changes
  useEffect(() => {
    if (cityFeature && mapRef.current) {
      const bounds = calculateBounds(cityFeature);
      if (bounds) {
        mapRef.current.fitBounds(bounds, { padding: [40, 40], animate: true, duration: 0.8 });
      }
    }
  }, [cityFeature]);

  const calculateBounds = (feature) => {
    if (!feature?.geometry) return null;
    try {
      const { type, coordinates } = feature.geometry;
      let allCoords = [];

      if (type === 'MultiPolygon') {
        coordinates.forEach(polygon => polygon.forEach(ring => allCoords.push(...ring)));
      } else if (type === 'Polygon') {
        coordinates.forEach(ring => allCoords.push(...ring));
      }

      if (allCoords.length > 0) {
        const lats = allCoords.map(c => c[1]);
        const lngs = allCoords.map(c => c[0]);
        return [
          [Math.min(...lats), Math.min(...lngs)],
          [Math.max(...lats), Math.max(...lngs)]
        ];
      }
    } catch (error) {
      console.error('Error calculating bounds:', error);
    }
    return null;
  };

  const loadCityGeoJSON = async () => {
    setLoading(true);
    try {
      const response = await fetch('/data/gadm41_LKA_2.json');
      const data = await response.json();

      const districtFeatures = data.features.filter(
        feature => feature.properties.NAME_1 === district
      );

      const selectedCity = districtFeatures.find(
        feature => feature.properties.NAME_2 === city
      );

      if (selectedCity) {
        setGeoJsonData({
          type: 'FeatureCollection',
          features: districtFeatures
        });
        setCityFeature(selectedCity); // triggers the fitBounds effect
      }
    } catch (error) {
      console.error('Failed to load city GeoJSON:', error);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (level) => {
    switch (level) {
      case 'HIGH': return '#EF4444';
      case 'MEDIUM': return '#F59E0B';
      case 'LOW': return '#10B981';
      default: return '#9CA3AF';
    }
  };

  const getCityStyle = (feature) => {
    if (feature.properties.NAME_2 === city) {
      return {
        fillColor: getRiskColor(riskLevel),
        fillOpacity: 0.8,
        color: '#1F2937',
        weight: 3,
        opacity: 1
      };
    }
    return {
      fillColor: '#E5E7EB',
      fillOpacity: 0.3,
      color: '#9CA3AF',
      weight: 1,
      opacity: 0.5
    };
  };

  const onEachCity = (feature, layer) => {
    if (feature.properties.NAME_2 === city) {
      const popupContent = `
        <div style="padding: 8px;">
          <h3 style="margin: 0 0 8px 0; font-weight: 600; font-size: 14px;">${feature.properties.NAME_2}</h3>
          <div style="margin-bottom: 4px;">
            <span style="font-size: 12px; color: #666;">Risk Level:</span>
            <span style="font-weight: 600; margin-left: 4px; color: ${getRiskColor(riskLevel)};">
              ${riskLevel}
            </span>
          </div>
          <div>
            <span style="font-size: 12px; color: #666;">Risk Score:</span>
            <span style="font-weight: 600; margin-left: 4px;">
              ${Math.round(riskScore * 100)}%
            </span>
          </div>
        </div>
      `;
      layer.bindPopup(popupContent);
      layer.openPopup();
    }
  };

  return (
    <div className="relative overflow-hidden rounded-lg shadow-md h-96">
      {/* Loading overlay — MapContainer stays mounted */}
      {loading && (
        <div className="absolute inset-0 z-[1001] flex items-center justify-center bg-white/70 rounded-lg">
          <div className="text-center">
            <div className="w-12 h-12 mx-auto mb-4 border-4 border-t-4 border-gray-200 rounded-full animate-spin border-t-primary"></div>
            <p className="text-gray-600">Loading map...</p>
          </div>
        </div>
      )}

      <MapContainer
        ref={mapRef}
        center={[7.8731, 80.7718]}
        zoom={7}
        className="w-full h-full"
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {geoJsonData && (
          <GeoJSON
            key={city}
            data={geoJsonData}
            style={getCityStyle}
            onEachFeature={onEachCity}
          />
        )}
      </MapContainer>

      {/* Legend */}
      {!loading && cityFeature && (
        <div className="absolute bottom-4 right-4 bg-white p-3 rounded-lg shadow-lg z-[1000]">
          <h4 className="mb-2 text-sm font-semibold">{city}</h4>
          <div className="flex items-center gap-2">
            <div
              className="w-4 h-4 rounded"
              style={{ backgroundColor: getRiskColor(riskLevel) }}
            />
            <span className="text-xs font-medium">{riskLevel} Risk</span>
          </div>
          <p className="mt-1 text-xs text-gray-600">
            Score: {Math.round(riskScore * 100)}%
          </p>
        </div>
      )}
    </div>
  );
}
