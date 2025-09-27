import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def reverse_geocode(lat, lng):
    """
    Convert coordinates to address using OpenStreetMap Nominatim
    """
    try:
        # Using OpenStreetMap Nominatim (free service)
        url = f"https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': lat,
            'lon': lng,
            'format': 'json',
            'addressdetails': 1,
            'zoom': 18
        }
        
        headers = {
            'User-Agent': 'AttendanceApp/1.0'  # Required by Nominatim
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Try to get a meaningful address
            address_parts = []
            address = data.get('address', {})
            
            # Add building/house number and road
            if address.get('house_number'):
                address_parts.append(address['house_number'])
            if address.get('road'):
                address_parts.append(address['road'])
            
            # Add locality/neighborhood
            locality = (address.get('neighbourhood') or 
                       address.get('suburb') or 
                       address.get('village') or 
                       address.get('town'))
            if locality:
                address_parts.append(locality)
            
            # Add city
            city = (address.get('city') or 
                   address.get('municipality'))
            if city:
                address_parts.append(city)
            
            # Add state/region
            state = (address.get('state') or 
                    address.get('region'))
            if state:
                address_parts.append(state)
            
            if address_parts:
                return ', '.join(address_parts)
            else:
                return data.get('display_name', f"Location: {lat}, {lng}")
        else:
            logger.warning(f"Geocoding failed with status {response.status_code}")
            return f"Location: {lat}, {lng}"
            
    except requests.exceptions.Timeout:
        logger.warning("Geocoding request timed out")
        return f"Location: {lat}, {lng}"
    except requests.exceptions.RequestException as e:
        logger.error(f"Geocoding error: {e}")
        return f"Location: {lat}, {lng}"
    except Exception as e:
        logger.error(f"Unexpected geocoding error: {e}")
        return f"Location: {lat}, {lng}"
