import 'leaflet/dist/leaflet.css';
import { useEffect, useState } from 'react';
import { GeoJSON, MapContainer, TileLayer } from 'react-leaflet';

export default function RiskHeatmap({ districtData, viewMode = 'district', selectedDistrict = '' }) {
  const [geoJsonData, setGeoJsonData] = useState(null);
  const [selectedArea, setSelectedArea] = useState(null);
  const [loading, setLoading] = useState(true);

  // Load appropriate GeoJSON based on view mode
  useEffect(() => {
    loadGeoJSON();
  }, [viewMode]);

  const loadGeoJSON = async () => {
    setLoading(true);
    try {
      // Load district-level or city-level GeoJSON from public folder
      const fileName = viewMode === 'city' ? 'gadm41_LKA_2.json' : 'gadm41_LKA_1.json';
      const response = await fetch(`/data/${fileName}`);
      const data = await response.json();
      setGeoJsonData(data);
    } catch (error) {
      console.error('Failed to load GeoJSON:', error);
    } finally {
      setLoading(false);
    }
  };

  // Get risk color based on level
  const getRiskColor = (riskLevel) => {
    switch (riskLevel) {
      case 'HIGH':
        return '#EF4444';
      case 'MEDIUM':
        return '#F59E0B';
      case 'LOW':
        return '#10B981';
      default:
        return '#9CA3AF';
    }
  };

  // Get risk data for district or city
  const getAreaRisk = (areaName) => {
    if (!districtData) return null;

    const searchName = areaName.toLowerCase().trim();
    
    // Search in districts array (for district view)
    if (districtData.districts) {
      const district = districtData.districts.find(d => {
        if (!d?.district) return false;
        const dName = d.district.toString().toLowerCase();
        return dName === searchName || searchName.includes(dName) || dName.includes(searchName);
      });
      if (district) return district;
    }

    // Search in cities array (for city view)
    if (districtData.cities) {
      const city = districtData.cities.find(c => {
        if (!c?.name) return false;
        const cName = c.name.toString().toLowerCase();
        return cName === searchName || searchName.includes(cName) || cName.includes(searchName);
      });
      if (city) return city;
    }

    return null;
  };

  // Style each area based on risk level
  const getAreaStyle = (feature) => {
    // Get area name based on view mode
    const areaName = viewMode === 'city' 
      ? feature.properties.NAME_2  // City name from GADM level 2
      : feature.properties.NAME_1; // District name from GADM level 1
    
    const areaRisk = getAreaRisk(areaName);
    const riskLevel = areaRisk?.risk_level || 'LOW';
    const color = getRiskColor(riskLevel);
    
    return {
      fillColor: color,
      fillOpacity: 0.6,
      color: '#333',
      weight: 1.5,
      opacity: 0.8
    };
  };

  // Handle area interactions
  const onEachArea = (feature, layer) => {
    const areaName = viewMode === 'city' 
      ? feature.properties.NAME_2 
      : feature.properties.NAME_1;
    
    const areaRisk = getAreaRisk(areaName);
    
    // Popup content
    const popupContent = `
      <div style="padding: 8px;">
        <h3 style="margin: 0 0 8px 0; font-weight: 600; font-size: 14px;">${areaName}</h3>
        ${areaRisk ? `
          <div style="margin-bottom: 4px;">
            <span style="font-size: 12px; color: #666;">Risk Level:</span>
            <span style="font-weight: 600; margin-left: 4px; color: ${getRiskColor(areaRisk.risk_level)};">
              ${areaRisk.risk_level}
            </span>
          </div>
          <div style="margin-bottom: 4px;">
            <span style="font-size: 12px; color: #666;">Risk Score:</span>
            <span style="font-weight: 600; margin-left: 4px;">
              ${Math.round(areaRisk.risk_score * 100)}%
            </span>
          </div>
        ` : '<div style="font-size: 12px; color: #999;">No data available</div>'}
      </div>
    `;
    
    layer.bindPopup(popupContent);
    
    // Hover effects
    layer.on({
      mouseover: (e) => {
        const layer = e.target;
        layer.setStyle({
          weight: 3,
          fillOpacity: 0.8
        });
        setSelectedArea(areaName);
      },
      mouseout: (e) => {
        const layer = e.target;
        layer.setStyle({
          weight: 1.5,
          fillOpacity: 0.6
        });
        setSelectedArea(null);
      }
    });
  };

  // Filter GeoJSON features for city view (only show selected district's cities)
  const getFilteredGeoJSON = () => {
    if (!geoJsonData) return null;
    
    // For city view, filter by selected district
    if (viewMode === 'city' && selectedDistrict) {
      return {
        ...geoJsonData,
        features: geoJsonData.features.filter(
          feature => feature.properties.NAME_1 === selectedDistrict
        )
      };
    }
    
    return geoJsonData;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-125">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto mb-4 border-4 border-t-4 border-gray-200 rounded-full animate-spin border-t-primary"></div>
          <p className="text-gray-600">Loading map...</p>
        </div>
      </div>
    );
  }

  const filteredData = getFilteredGeoJSON();

  return (
    <div className="relative overflow-hidden rounded-lg shadow-md h-125">
      <MapContainer 
        center={[7.8731, 80.7718]} 
        zoom={viewMode === 'city' ? 10 : 8}
        className="w-full h-full"
        scrollWheelZoom={true}
        key={viewMode}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {filteredData && (
          <GeoJSON 
            key={`${viewMode}-${selectedDistrict}-${JSON.stringify(districtData?.summary)}`}
            data={filteredData} 
            style={getAreaStyle}
            onEachFeature={onEachArea}
          />
        )}
      </MapContainer>

      {/* Legend */}
      <div className="absolute bottom-4 right-4 bg-white p-3 rounded-lg shadow-lg z-[1000]">
        <h4 className="mb-2 text-sm font-semibold">Risk Level</h4>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#EF4444' }} />
            <span className="text-xs">High Risk</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#F59E0B' }} />
            <span className="text-xs">Medium Risk</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#10B981' }} />
            <span className="text-xs">Low Risk</span>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      {districtData?.summary && (
        <div className="absolute top-4 right-4 bg-white p-3 rounded-lg shadow-lg z-[1000] max-w-[200px]">
          <h4 className="mb-2 text-xs font-semibold text-gray-700">
            {viewMode === 'city' ? 'City Summary' : 'District Summary'}
          </h4>
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-red-600">High Risk:</span>
              <span className="font-semibold">
                {districtData.summary.high_risk_cities || districtData.summary.high_risk_districts || 0}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-yellow-600">Medium Risk:</span>
              <span className="font-semibold">
                {districtData.summary.medium_risk_cities || districtData.summary.medium_risk_districts || 0}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-green-600">Low Risk:</span>
              <span className="font-semibold">
                {districtData.summary.low_risk_cities || districtData.summary.low_risk_districts || 0}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Hover tooltip */}
      {selectedArea && (
        <div className="absolute top-4 left-4 bg-white px-3 py-2 rounded-lg shadow-lg z-[1000]">
          <p className="text-sm font-semibold text-gray-800">{selectedArea}</p>
        </div>
      )}
    </div>
  );
}