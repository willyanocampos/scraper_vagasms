import folium
from folium import plugins
from typing import Dict, List, Any, Optional, Tuple
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

class MapRenderer:
    
    def __init__(self, style_manager=None):
        self.style_manager = style_manager
        self._default_location = [-15.7801, -47.9292]
        self._default_zoom = 4
        self._map_cache = {}
        
    def create_base_map(self, 
                       center: Optional[Tuple[float, float]] = None,
                       zoom: int = None,
                       width: str = "100%",
                       height: str = "600px") -> folium.Map:
        try:
            center = center or self._default_location
            zoom = zoom or self._default_zoom
            
            base_map = folium.Map(
                location=center,
                zoom_start=zoom,
                width=width,
                height=height,
                tiles=None,
                control_scale=True,
                zoom_control=True,
                scrollWheelZoom=True,
                dragging=True,
                prefer_canvas=True
            )
            
            self._add_tile_layers(base_map)
            
            folium.LayerControl(position='topright', collapsed=False).add_to(base_map)
            
            logger.info(f"Created base map centered at {center} with zoom {zoom}")
            return base_map
            
        except Exception as e:
            logger.error(f"Error creating base map: {e}")
            return folium.Map(location=self._default_location, zoom_start=self._default_zoom)
    
    def _add_tile_layers(self, base_map: folium.Map):
        try:
            folium.TileLayer(
                tiles='OpenStreetMap',
                name='OpenStreetMap',
                control=True
            ).add_to(base_map)
            
            folium.TileLayer(
                tiles='CartoDB positron',
                name='Light Theme',
                control=True
            ).add_to(base_map)
            
            folium.TileLayer(
                tiles='CartoDB dark_matter',
                name='Dark Theme',
                control=True
            ).add_to(base_map)
            
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
                name='Satellite',
                control=True
            ).add_to(base_map)
            
        except Exception as e:
            logger.warning(f"Error adding tile layers: {e}")
    
    def add_location_markers(self, 
                           base_map: folium.Map,
                           locations_data: Dict[str, Dict],
                           popup_generator=None) -> folium.Map:
        try:
            if not locations_data:
                logger.warning("No location data provided for markers")
                return base_map
            
            marker_cluster = self._create_marker_cluster()
            
            markers_added = 0
            coordinates_for_bounds = []
            
            for location_name, location_data in locations_data.items():
                try:
                    marker = self._create_location_marker(
                        location_name, 
                        location_data, 
                        popup_generator
                    )
                    
                    if marker:
                        marker_cluster.add_child(marker)
                        markers_added += 1
                        
                        if location_data.get('coordinates'):
                            coordinates_for_bounds.append(location_data['coordinates'])
                            
                except Exception as e:
                    logger.warning(f"Error creating marker for {location_name}: {e}")
                    continue
            
            marker_cluster.add_to(base_map)
            
            if coordinates_for_bounds:
                self._fit_bounds_to_coordinates(base_map, coordinates_for_bounds)
            
            logger.info(f"Added {markers_added} location markers with clustering")
            return base_map
            
        except Exception as e:
            logger.error(f"Error adding location markers: {e}")
            return base_map
    
    def _create_marker_cluster(self) -> plugins.MarkerCluster:
        try:
            return plugins.MarkerCluster(
                name="Job Locations",
                overlay=True,
                control=True,
                show=True,
                maxClusterRadius=40,
                disableClusteringAtZoom=12,
                chunkedLoading=True,
                chunkInterval=200,
                chunkDelay=100,
                showCoverageOnHover=False,
                zoomToBoundsOnClick=True,
                spiderfyOnMaxZoom=True,
                removeOutsideVisibleBounds=True,
                iconCreateFunction="""
                function(cluster) {
                    var count = cluster.getChildCount();
                    var size = count < 10 ? 'small' : count < 100 ? 'medium' : 'large';
                    var color = count < 10 ? '#3b82f6' : count < 100 ? '#10b981' : '#f59e0b';
                    
                    return new L.DivIcon({
                        html: '<div style="background-color:' + color + ';color:white;border-radius:50%;width:40px;height:40px;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:12px;box-shadow:0 2px 4px rgba(0,0,0,0.2);">' + count + '</div>',
                        className: 'custom-cluster-icon',
                        iconSize: new L.Point(40, 40)
                    });
                }
        Create individual location marker
        
        Args:
            location_name: Name of the location
            location_data: Location data dictionary
            popup_generator: PopupGenerator instance
            
        Returns:
            Folium marker or None
        Get marker style based on sector and job count
        
        Args:
            sector: Dominant job sector
            job_count: Number of jobs
            
        Returns:
            Style dictionary for marker
        Convert hex color to folium-compatible color
        
        Args:
            hex_color: Hex color code
            
        Returns:
            Folium color name
        Get appropriate icon based on job count
        
        Args:
            job_count: Number of jobs
            
        Returns:
            Icon name
        Get default coordinates for known Brazilian cities
        
        Args:
            location_name: Name of the location
            
        Returns:
            Tuple of (latitude, longitude) or None
        Create basic popup HTML when PopupGenerator is not available
        
        Args:
            location_data: Location data dictionary
            
        Returns:
            Basic HTML popup content
            
            return html
            
        except Exception as e:
            logger.error(f"Error creating basic popup: {e}")
            return f"<div><h4>{location_data.get('location', 'Localização')}</h4><p>Erro ao carregar informações</p></div>"
    
    def _fit_bounds_to_coordinates(self, base_map: folium.Map, coordinates: List[Tuple[float, float]]):
        try:
            if not coordinates:
                return
            
            lats = [coord[0] for coord in coordinates]
            lons = [coord[1] for coord in coordinates]
            
            sw = [min(lats), min(lons)]
            ne = [max(lats), max(lons)]
            
            lat_padding = (max(lats) - min(lats)) * 0.1
            lon_padding = (max(lons) - min(lons)) * 0.1
            
            sw[0] -= lat_padding
            sw[1] -= lon_padding
            ne[0] += lat_padding
            ne[1] += lon_padding
            
            base_map.fit_bounds([sw, ne])
            
        except Exception as e:
            logger.warning(f"Error fitting bounds: {e}")
    
    def render_to_html(self, base_map: folium.Map, output_path: Optional[str] = None) -> str:
        try:
            if not output_path:
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w', 
                    suffix='.html', 
                    delete=False, 
                    encoding='utf-8'
                )
                output_path = temp_file.name
                temp_file.close()
            
            base_map.save(output_path)
            
            logger.info(f"Map rendered to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error rendering map to HTML: {e}")
            return ""
    
    def add_custom_controls(self, base_map: folium.Map):
        try:
            plugins.Fullscreen(
                position='topright',
                title='Tela cheia',
                title_cancel='Sair da tela cheia',
                force_separate_button=True
            ).add_to(base_map)
            
            plugins.MeasureControl(
                position='topleft',
                primary_length_unit='kilometers',
                secondary_length_unit='meters',
                primary_area_unit='sqkilometers',
                secondary_area_unit='hectares'
            ).add_to(base_map)
            
            plugins.LocateControl(auto_start=False).add_to(base_map)
            
            logger.info("Added custom controls to map")
            
        except Exception as e:
            logger.warning(f"Error adding custom controls: {e}")
    
    def clear_cache(self):
        self._map_cache.clear()
        logger.info("Map renderer cache cleared")
    
    def get_map_bounds(self, locations_data: Dict[str, Dict]) -> Optional[Dict[str, float]]:
        try:
            coordinates = []
            
            for location_data in locations_data.values():
                coords = location_data.get('coordinates')
                if coords:
                    coordinates.append(coords)
            
            if not coordinates:
                return None
            
            lats = [coord[0] for coord in coordinates]
            lons = [coord[1] for coord in coordinates]
            
            return {
                'north': max(lats),
                'south': min(lats),
                'east': max(lons),
                'west': min(lons)
            }
            
        except Exception as e:
            logger.error(f"Error calculating map bounds: {e}")
            return None