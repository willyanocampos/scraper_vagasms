import json
from typing import List, Tuple, Dict
class AccurateMSMapData:
    def __init__(self):
        self.ms_precise_boundary = [
            (-17.86, -57.85), (-17.92, -57.62), (-18.15, -57.38), 
            (-18.28, -57.15), (-18.45, -56.92), (-18.62, -56.68),
            (-18.78, -56.45), (-18.95, -56.22), (-19.12, -55.98),
            (-19.28, -55.75), (-19.45, -55.52), (-19.62, -55.28),
            (-19.78, -55.05), (-19.95, -54.82), (-20.12, -54.58),
            (-20.28, -54.35), (-20.45, -54.12), (-20.62, -53.88),
            (-20.78, -53.65), (-20.95, -53.42), (-21.12, -53.18),
            (-21.28, -52.95), (-21.45, -52.72), (-21.62, -52.48),
            (-21.78, -52.25), (-21.95, -52.02), (-22.12, -51.78),
            (-22.28, -51.55), (-22.45, -51.32), (-22.62, -51.08),
            (-22.78, -50.85), (-22.95, -50.62), (-23.12, -50.38),
            (-23.28, -50.55), (-23.45, -50.78), (-23.62, -51.02),
            (-23.78, -51.25), (-23.95, -51.48), (-24.12, -51.72),
            (-24.28, -51.95), (-24.45, -52.18), (-24.62, -52.42),
            (-24.78, -52.65), (-24.95, -52.88), (-25.12, -53.12),
            (-25.28, -53.35), (-25.45, -53.58), (-25.62, -53.82),
            (-25.78, -54.05), (-25.95, -54.28), (-26.12, -54.52),
            (-26.28, -54.75), (-26.45, -54.98), (-26.62, -55.22),
            (-26.78, -55.45), (-26.95, -55.68), (-27.12, -55.92),
            (-27.28, -56.15), (-27.45, -56.38), (-27.62, -56.62),
            (-27.78, -56.85), (-27.95, -57.08), (-28.12, -57.32),
            (-28.28, -57.55), (-28.45, -57.78), (-28.62, -58.02),
            (-28.78, -58.25), (-28.95, -58.48), (-29.12, -58.72),
            (-19.45, -58.15), (-18.85, -57.95), (-18.25, -57.88),
            (-17.86, -57.85)
        ]
        self.accurate_cities = {
            'Campo Grande': (-20.4697, -54.6201),
            'Dourados': (-22.2211, -54.8056),
            'Três Lagoas': (-20.7844, -51.6781),
            'Corumbá': (-19.0078, -57.6528),
            'Ponta Porã': (-22.5355, -55.7255),
            'Naviraí': (-23.0644, -54.1897),
            'Nova Andradina': (-22.2323, -53.3424),
            'Aquidauana': (-20.4719, -55.7875),
            'Sidrolândia': (-20.9306, -54.9606),
            'Maracaju': (-21.6131, -55.1689),
            'Coxim': (-18.5067, -54.7606),
            'Miranda': (-20.2425, -56.3781),
            'Bonito': (-21.1269, -56.4789),
            'Jardim': (-21.4831, -56.1403),
            'Anastácio': (-20.4889, -55.8094),
            'Caarapó': (-22.6431, -54.8231),
            'Cassilândia': (-19.1144, -51.7361),
            'Paranaíba': (-19.6778, -51.1906),
            'Ribas do Rio Pardo': (-20.4444, -53.7619),
            'São Gabriel do Oeste': (-19.3906, -54.5656),
            'Amambai': (-23.1047, -55.2256),
            'Aparecida do Taboado': (-20.0878, -51.0969),
            'Bela Vista': (-22.1081, -56.5178),
            'Bodoquena': (-20.5381, -56.7189),
            'Brasilândia': (-21.2636, -52.0381),
            'Chapadão do Sul': (-18.7906, -52.6236),
            'Costa Rica': (-18.5331, -53.1331),
            'Coxim': (-18.5067, -54.7606),
            'Eldorado': (-23.7831, -54.2831),
            'Glória de Dourados': (-22.3831, -54.2189),
            'Inocência': (-19.7406, -51.8406),
            'Ivinhema': (-22.3031, -53.8189),
            'Mundo Novo': (-23.9331, -54.2831),
            'Nioaque': (-21.1381, -56.0189),
            'Nova Alvorada do Sul': (-21.4831, -54.3831),
            'Palmeiras': (-21.0906, -55.2856),
            'Paranaíba': (-19.6778, -51.1906),
            'Rio Brilhante': (-21.8031, -54.5431),
            'Sonora': (-17.5756, -54.7506),
            'Terenos': (-20.4431, -54.8631)
        }
        self.accurate_bounds = {
            'lat_min': -24.0694,
            'lat_max': -17.9164,
            'lon_min': -58.1647,
            'lon_max': -50.3469
        }
        self.geographical_features = {
            'rivers': {
                'Rio Paraguai': [
                    (-19.0, -57.7), (-19.5, -57.5), (-20.0, -57.3),
                    (-20.5, -57.1), (-21.0, -56.9), (-21.5, -56.7)
                ],
                'Rio Paraná': [
                    (-22.5, -53.2), (-22.8, -52.8), (-23.1, -52.4),
                    (-23.4, -52.0), (-23.7, -51.6), (-24.0, -51.2)
                ],
                'Rio Taquari': [
                    (-18.8, -54.2), (-19.2, -54.6), (-19.6, -55.0),
                    (-20.0, -55.4), (-20.4, -55.8)
                ]
            },
            'highlands': {
                'Serra da Bodoquena': (-20.7, -56.8),
                'Serra de Maracaju': (-21.2, -55.2),
                'Planalto da Bodoquena': (-20.5, -56.5)
            },
            'pantanal_region': [
                (-18.0, -57.5), (-18.5, -57.0), (-19.0, -56.5),
                (-19.5, -56.0), (-20.0, -55.5), (-20.5, -55.0)
            ]
        }
        self.regions = {
            'Norte': {
                'cities': ['Coxim', 'Sonora', 'Costa Rica', 'Chapadão do Sul'],
                'center': (-18.5, -53.5)
            },
            'Nordeste': {
                'cities': ['Três Lagoas', 'Aparecida do Taboado', 'Paranaíba', 'Inocência'],
                'center': (-20.0, -51.5)
            },
            'Leste': {
                'cities': ['Nova Andradina', 'Ribas do Rio Pardo', 'Brasilândia'],
                'center': (-21.5, -53.0)
            },
            'Centro': {
                'cities': ['Campo Grande', 'Sidrolândia', 'Terenos', 'Rochedo'],
                'center': (-20.5, -54.5)
            },
            'Sul': {
                'cities': ['Dourados', 'Maracaju', 'Rio Brilhante', 'Nova Alvorada do Sul'],
                'center': (-22.0, -54.8)
            },
            'Sudoeste': {
                'cities': ['Ponta Porã', 'Amambai', 'Naviraí', 'Eldorado'],
                'center': (-23.5, -55.0)
            },
            'Oeste': {
                'cities': ['Corumbá', 'Ladário', 'Miranda', 'Aquidauana'],
                'center': (-19.5, -57.0)
            },
            'Pantanal': {
                'cities': ['Corumbá', 'Ladário', 'Coxim', 'Miranda'],
                'center': (-19.0, -56.5)
            }
        }
    def get_state_boundary(self) -> List[Tuple[float, float]]:
        return self.ms_precise_boundary
    def get_city_coordinates(self, city_name: str) -> Tuple[float, float]:
        city_clean = city_name.strip().title()
        if city_clean in self.accurate_cities:
            return self.accurate_cities[city_clean]
        for city, coords in self.accurate_cities.items():
            if (city.lower() in city_clean.lower() or 
                city_clean.lower() in city.lower()):
                return coords
        return self.accurate_cities['Campo Grande']
    def get_all_cities(self) -> Dict[str, Tuple[float, float]]:
        return self.accurate_cities.copy()
    def get_bounds(self) -> Dict[str, float]:
        return self.accurate_bounds.copy()
    def get_region_info(self, city_name: str) -> Dict:
        city_clean = city_name.strip().title()
        for region_name, region_data in self.regions.items():
            if city_clean in region_data['cities']:
                return {
                    'region': region_name,
                    'center': region_data['center'],
                    'cities': region_data['cities']
                }
        return {
            'region': 'Centro',
            'center': self.regions['Centro']['center'],
            'cities': self.regions['Centro']['cities']
        }
    def is_in_pantanal(self, lat: float, lon: float) -> bool:
        pantanal_bounds = {
            'lat_min': -20.5, 'lat_max': -17.5,
            'lon_min': -58.0, 'lon_max': -55.0
        }
        return (pantanal_bounds['lat_min'] <= lat <= pantanal_bounds['lat_max'] and
                pantanal_bounds['lon_min'] <= lon <= pantanal_bounds['lon_max'])
    def get_nearest_city(self, lat: float, lon: float) -> str:
        min_distance = float('inf')
        nearest_city = 'Campo Grande'
        for city, (city_lat, city_lon) in self.accurate_cities.items():
            distance = ((lat - city_lat) ** 2 + (lon - city_lon) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                nearest_city = city
        return nearest_city
    def export_geojson(self) -> Dict:
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "name": "Mato Grosso do Sul",
                        "state_code": "MS",
                        "country": "Brazil"
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [[lon, lat] for lat, lon in self.ms_precise_boundary]
                        ]
                    }
                }
            ]
        }
        for city, (lat, lon) in self.accurate_cities.items():
            geojson["features"].append({
                "type": "Feature",
                "properties": {
                    "name": city,
                    "type": "city",
                    "region": self.get_region_info(city)['region']
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [lon, lat]
                }
            })
        return geojson
def test_accurate_map_data():
    ms_data = AccurateMSMapData()
    print("🗺️ Testing Accurate MS Map Data")
    print("="*50)
    test_cities = ['Campo Grande', 'Dourados', 'Três Lagoas', 'Corumbá']
    for city in test_cities:
        lat, lon = ms_data.get_city_coordinates(city)
        region_info = ms_data.get_region_info(city)
        print(f"📍 {city}: ({lat:.4f}, {lon:.4f}) - Região: {region_info['region']}")
    print(f"\n🎯 Total cities: {len(ms_data.get_all_cities())}")
    print(f"📏 State bounds: {ms_data.get_bounds()}")
    print(f"🗺️ Boundary points: {len(ms_data.get_state_boundary())}")
    geojson = ms_data.export_geojson()
    print(f"📄 GeoJSON features: {len(geojson['features'])}")
if __name__ == "__main__":
    test_accurate_map_data()