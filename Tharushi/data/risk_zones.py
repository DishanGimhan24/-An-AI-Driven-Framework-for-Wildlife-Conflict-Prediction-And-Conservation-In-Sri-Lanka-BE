"""
Risk zone definitions for Sri Lanka
Based on known HEC hotspots and geographic analysis
"""

# High-risk zones - Known conflict areas
HIGH_RISK_ZONES = [
    {
        'name': 'Anuradhapura Rural',
        'bounds': {'lat': (7.8, 8.6), 'lon': (80.0, 80.8)},
        'reason': 'Major elephant corridor, frequent crop raids'
    },
    {
        'name': 'Polonnaruwa District',
        'bounds': {'lat': (7.7, 8.2), 'lon': (80.8, 81.3)},
        'reason': 'High elephant population, agricultural conflict'
    },
    {
        'name': 'Ampara Rural',
        'bounds': {'lat': (7.0, 7.6), 'lon': (81.4, 81.9)},
        'reason': 'Elephant migration routes'
    },
    {
        'name': 'Hambantota Inland',
        'bounds': {'lat': (6.0, 6.4), 'lon': (80.9, 81.4)},
        'reason': 'Near Yala, Lunugamvehera reserves'
    },
    {
        'name': 'Kurunegala East',
        'bounds': {'lat': (7.3, 7.8), 'lon': (80.2, 80.6)},
        'reason': 'Forest border conflicts'
    },
    {
        'name': 'Trincomalee Interior',
        'bounds': {'lat': (8.3, 8.8), 'lon': (80.8, 81.3)},
        'reason': 'Elephant habitat overlap'
    }
]

# Medium-risk zones - Buffer areas, occasional conflicts
MEDIUM_RISK_ZONES = [
    {
        'name': 'Anuradhapura Town Buffer',
        'bounds': {'lat': (8.2, 8.5), 'lon': (80.3, 80.5)},
        'reason': 'Urban fringe'
    },
    {
        'name': 'Kurunegala West',
        'bounds': {'lat': (7.3, 7.6), 'lon': (79.9, 80.2)},
        'reason': 'Agricultural border'
    },
    {
        'name': 'Ratnapura District',
        'bounds': {'lat': (6.6, 6.9), 'lon': (80.3, 80.7)},
        'reason': 'Hill country buffer'
    },
    {
        'name': 'Badulla Rural',
        'bounds': {'lat': (6.9, 7.1), 'lon': (81.0, 81.2)},
        'reason': 'Tea estate boundaries'
    },
    {
        'name': 'Monaragala',
        'bounds': {'lat': (6.7, 7.0), 'lon': (81.2, 81.6)},
        'reason': 'Buffer zone'
    },
    {
        'name': 'Puttalam Interior',
        'bounds': {'lat': (7.9, 8.2), 'lon': (79.8, 80.1)},
        'reason': 'Occasional sightings'
    },
    {
        'name': 'Matale Rural',
        'bounds': {'lat': (7.4, 7.6), 'lon': (80.5, 80.8)},
        'reason': 'Agricultural areas'
    }
]

# Low-risk zones - Urban centers, coastal areas
LOW_RISK_ZONES = [
    {
        'name': 'Colombo Metro',
        'bounds': {'lat': (6.85, 6.98), 'lon': (79.82, 79.92)},
        'reason': 'Dense urban, no elephants'
    },
    {
        'name': 'Gampaha Urban',
        'bounds': {'lat': (7.05, 7.15), 'lon': (79.95, 80.05)},
        'reason': 'Urban area'
    },
    {
        'name': 'Galle City',
        'bounds': {'lat': (6.02, 6.08), 'lon': (80.19, 80.25)},
        'reason': 'Coastal urban'
    },
    {
        'name': 'Kandy City',
        'bounds': {'lat': (7.26, 7.32), 'lon': (80.60, 80.66)},
        'reason': 'Urban center'
    },
    {
        'name': 'Jaffna Peninsula',
        'bounds': {'lat': (9.60, 9.72), 'lon': (79.98, 80.10)},
        'reason': 'Northern urban, no elephants'
    },
    {
        'name': 'Negombo Coastal',
        'bounds': {'lat': (7.19, 7.24), 'lon': (79.83, 79.88)},
        'reason': 'Coastal city'
    },
    {
        'name': 'Matara Coastal',
        'bounds': {'lat': (5.93, 5.97), 'lon': (80.53, 80.57)},
        'reason': 'Coastal urban'
    },
    {
        'name': 'Batticaloa Town',
        'bounds': {'lat': (7.71, 7.75), 'lon': (81.68, 81.72)},
        'reason': 'Eastern coastal'
    }
]


def get_risk_level_for_location(latitude, longitude):
    """
    Determine risk level based on geographic location

    Args:
        latitude: Location latitude
        longitude: Location longitude

    Returns:
        dict with risk_level, risk_score, zone_name, reason
    """

    # Check HIGH risk zones first
    for zone in HIGH_RISK_ZONES:
        bounds = zone['bounds']
        if (bounds['lat'][0] <= latitude <= bounds['lat'][1] and
                bounds['lon'][0] <= longitude <= bounds['lon'][1]):
            return {
                'risk_level': 'HIGH',
                'risk_score': 0.80,  # 80% base for high zones
                'zone_name': zone['name'],
                'reason': zone['reason']
            }

    # Check LOW risk zones
    for zone in LOW_RISK_ZONES:
        bounds = zone['bounds']
        if (bounds['lat'][0] <= latitude <= bounds['lat'][1] and
                bounds['lon'][0] <= longitude <= bounds['lon'][1]):
            return {
                'risk_level': 'LOW',
                'risk_score': 0.20,  # 20% base for low zones
                'zone_name': zone['name'],
                'reason': zone['reason']
            }

    # Check MEDIUM risk zones
    for zone in MEDIUM_RISK_ZONES:
        bounds = zone['bounds']
        if (bounds['lat'][0] <= latitude <= bounds['lat'][1] and
                bounds['lon'][0] <= longitude <= bounds['lon'][1]):
            return {
                'risk_level': 'MEDIUM',
                'risk_score': 0.55,  # 55% base for medium zones
                'zone_name': zone['name'],
                'reason': zone['reason']
            }

    # Default: Areas not explicitly classified
    # Central hills, tea country - medium risk
    if 6.8 <= latitude <= 7.3 and 80.5 <= longitude <= 81.0:
        return {
            'risk_level': 'MEDIUM',
            'risk_score': 0.50,
            'zone_name': 'Central Highlands',
            'reason': 'Hill country, moderate risk'
        }

    # Southern coastal - low risk
    if latitude < 6.5 and longitude > 80.0:
        return {
            'risk_level': 'LOW',
            'risk_score': 0.25,
            'zone_name': 'Southern Coast',
            'reason': 'Coastal area'
        }

    # Default medium for unclassified
    return {
        'risk_level': 'MEDIUM',
        'risk_score': 0.50,
        'zone_name': 'Unclassified Area',
        'reason': 'Default classification'
    }