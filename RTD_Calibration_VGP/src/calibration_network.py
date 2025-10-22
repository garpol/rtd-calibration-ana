import pandas as pd
import numpy as np
import logging
import yaml
from typing import Dict, Tuple, List, Optional, Any, Union
from .utils import load_config, DEFAULT_CONFIG

# Attempt to import networkx and provide a clear instruction if it is missing.
try:
    import networkx as nx
except ImportError as exc:
    logging.error(
        "The 'networkx' library is not available; install it with: pip install networkx"
    )
    raise ImportError(
        "Missing dependency 'networkx'. Install it with: pip install networkx"
    ) from exc

# ----------------------------------------------------------------------
# Configuration of logging
# -----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Main class: CalibrationNetwork
# -----------------------------------------------------------------------

class CalibrationNetwork:
    """
    Class that manages global calibration by connecting multiple 'sets'
    through 'raised' sensors that serve as bridges between rounds.
    
    Capabilities:
        - Build the connection graph between sets.
        - Calculate global offsets between sensors in different sets.
        - Propagate uncertainties (errors) along paths in the tree.
    """

    def __init__(self, sets_dict: Dict[float, Any], config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None) -> None:
        """
        Initialize CalibrationNetwork with sets and configuration.
        
        Args:
            sets_dict (dict): Dictionary {CalibSetNumber: SetObject}.
                              Each SetObject must have:
                                  - calibration_constants (DataFrame)
                                  - calibration_errors (DataFrame)
            config (dict, optional): Configuration dictionary. If provided, overrides config_path.
            config_path (str, optional): Path to the YAML file with tree definition
                               (relationships between sets, raised sensors, etc.)
        """
        self.sets = sets_dict
        self.graph = nx.Graph()
        
        # Load configuration using the same pattern as Set and Run classes
        try:
            if config is not None:
                self.config = config
            elif config_path:
                self.config = load_config(config_path)
            else:
                self.config = DEFAULT_CONFIG.copy()
        except Exception as e:
            logger.warning(f"Could not load configuration: {e}. Using defaults.")
            self.config = DEFAULT_CONFIG.copy()
        
        # Validate sets_dict
        if not isinstance(sets_dict, dict):
            raise TypeError("sets_dict must be a dictionary")
        
        if not sets_dict:
            logger.warning("No sets provided in sets_dict")
        
        # Build graph from configuration
        self._build_graph_from_config()

    # ------------------------------------------------------------------
    # BUILDING THE CONNECTION GRAPH BETWEEN SETS
    # ------------------------------------------------------------------
    def _build_graph_from_config(self) -> None:
        """
        Builds the connection graph between sets using the configuration.
        Each node is a CalibSetNumber.
        Each edge connects two consecutive sets through one or more 'raised' sensors.
        """
        logger.info("Building calibration graph from configuration...")

        sets_config = self._extract_sets_configuration()
        edges_added = self._build_graph_edges(sets_config)
        
        logger.info(f"Graph built with {len(self.graph.nodes)} sets and {edges_added} connections.")

    def _extract_sets_configuration(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract sets configuration from the loaded config.
        
        Returns:
            Dict[str, Dict[str, Any]]: Sets configuration dictionary
        """
        try:
            # Get sensor configuration from the loaded config
            sensors_config = self.config.get("sensors", {})
            
            # Try to get sets configuration (unified structure)
            sets_config = sensors_config.get("sets", {})
            if not sets_config:
                # Fallback to individual dictionaries
                raised_sensors = sensors_config.get("sensors_raised_by_set", {})
                set_rounds = sensors_config.get("set_rounds", {})
                
                # Convert to sets format for processing
                sets_config = {}
                for set_id in raised_sensors.keys():
                    sets_config[str(set_id)] = {
                        "raised": raised_sensors.get(set_id, []),
                        "round": set_rounds.get(set_id, 1)
                    }
            return sets_config
        except Exception as e:
            logger.error(f"Error processing sensor configuration: {e}")
            return {}

    def _build_graph_edges(self, sets_config: Dict[str, Dict[str, Any]]) -> int:
        """
        Build graph edges from sets configuration.
        
        Args:
            sets_config (Dict[str, Dict[str, Any]]): Sets configuration
            
        Returns:
            int: Number of edges added
        """
        edges_added = 0
        for set_id_str, data in sets_config.items():
            try:
                set_id = float(set_id_str)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid set ID '{set_id_str}': {e}")
                continue

            round_id = data.get("round", 1)
            raised_sensors = data.get("raised", [])

            # Search for sets in the next level that contain any of these sensors
            edges_added += self._connect_to_next_round(
                set_id, round_id, raised_sensors, sets_config
            )

        return edges_added

    def _connect_to_next_round(
        self, 
        set_id: float, 
        round_id: int, 
        raised_sensors: List[int], 
        sets_config: Dict[str, Dict[str, Any]]
    ) -> int:
        """
        Connect a set to sets in the next round.
        
        Args:
            set_id (float): Current set ID
            round_id (int): Current round number
            raised_sensors (List[int]): Raised sensors for current set
            sets_config (Dict[str, Dict[str, Any]]): All sets configuration
            
        Returns:
            int: Number of edges added
        """
        edges_added = 0
        for other_id_str, other_data in sets_config.items():
            try:
                other_id = float(other_id_str)
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid other set ID '{other_id_str}': {e}")
                continue
                
            if other_data.get("round", 1) != round_id + 1:
                continue

            bridge_sensors = self._find_bridge_sensors(raised_sensors, other_data)
            
            for sensor in bridge_sensors:
                try:
                    self.graph.add_edge(set_id, other_id, sensor=sensor)
                    edges_added += 1
                except Exception as e:
                    logger.warning(f"Failed to add edge between {set_id} and {other_id}: {e}")

        return edges_added

    def _find_bridge_sensors(
        self, 
        raised_sensors: List[int], 
        other_data: Dict[str, Any]
    ) -> List[int]:
        """
        Find bridge sensors between two sets.
        
        Args:
            raised_sensors (List[int]): Raised sensors from current set
            other_data (Dict[str, Any]): Other set configuration
            
        Returns:
            List[int]: Bridge sensors found
        """
        return [
            s for s in raised_sensors
            if s in other_data.get("raised", []) or s in other_data.get("discarded", [])
        ]

    def _get_set_round(self, set_id: float) -> int:
        """
        Get the round number for a given set ID from configuration.
        
        Args:
            set_id (float): Set identifier
            
        Returns:
            int: Round number (defaults to 1 if not found)
        """
        sensors_config = self.config.get("sensors", {})
        
        # Try unified sets structure first
        sets_config = sensors_config.get("sets", {})
        if sets_config:
            set_data = sets_config.get(str(set_id), {})
            return set_data.get("round", 1)
        
        # Fallback to set_rounds dictionary
        set_rounds = sensors_config.get("set_rounds", {})
        return set_rounds.get(set_id, 1)

    def _get_reference_sensor(self, set_id: float) -> Optional[int]:
        """
        Get the reference sensor for a given set ID from configuration.
        
        Args:
            set_id (float): Set identifier
            
        Returns:
            int or None: Reference sensor ID (first raised sensor)
        """
        sensors_config = self.config.get("sensors", {})
        
        # Try unified sets structure first
        sets_config = sensors_config.get("sets", {})
        if sets_config:
            set_data = sets_config.get(str(set_id), {})
            raised_sensors = set_data.get("raised", [])
        else:
            # Fallback to sensors_raised_by_set dictionary
            raised_sensors = sensors_config.get("sensors_raised_by_set", {}).get(set_id, [])
        
        return raised_sensors[0] if raised_sensors else None

    def get_sets_by_round(self, round_number: int) -> List[float]:
        """
        Get all sets that belong to a specific round.
        
        Args:
            round_number (int): Round number to filter by
            
        Returns:
            List[float]: List of set IDs in the specified round
        """
        sets_in_round = []
        for set_id in self.sets.keys():
            if self._get_set_round(set_id) == round_number:
                sets_in_round.append(set_id)
        return sorted(sets_in_round)

    def get_reference_set(self) -> Optional[float]:
        """
        Get the reference set (typically the highest round set).
        
        Returns:
            float or None: Reference set ID, or None if not found
        """
        if not self.sets:
            return None
        
        # Find the set with the highest round number
        max_round = 0
        reference_set = None
        
        for set_id in self.sets.keys():
            round_num = self._get_set_round(set_id)
            if round_num > max_round:
                max_round = round_num
                reference_set = set_id
        
        return reference_set

    def validate_sets_structure(self) -> Dict[str, List[str]]:
        """
        Validate that all sets have the required structure.
        
        Returns:
            Dict[str, List[str]]: Validation results with issues found
        """
        issues = {
            "missing_constants": [],
            "missing_errors": [],
            "missing_sets": []
        }
        
        for set_id, set_obj in self.sets.items():
            if not hasattr(set_obj, 'calibration_constants') or set_obj.calibration_constants is None:
                issues["missing_constants"].append(str(set_id))
            if not hasattr(set_obj, 'calibration_errors') or set_obj.calibration_errors is None:
                issues["missing_errors"].append(str(set_id))
        
        return issues

    @classmethod
    def from_sets(cls, sets_list: List[Any], config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None) -> 'CalibrationNetwork':
        """
        Create a CalibrationNetwork from a list of Set objects.
        
        Args:
            sets_list (List): List of Set objects
            config (dict, optional): Configuration dictionary
            config_path (str, optional): Path to configuration file
            
        Returns:
            CalibrationNetwork: New network instance
        """
        sets_dict = {}
        for set_obj in sets_list:
            # Extract set ID from the set object
            if hasattr(set_obj, 'runs_by_set') and set_obj.runs_by_set:
                # Get the first set ID from runs_by_set
                set_id = list(set_obj.runs_by_set.keys())[0]
                sets_dict[set_id] = set_obj
            else:
                logger.warning(f"Set object has no runs_by_set, skipping")
        
        return cls(sets_dict, config=config, config_path=config_path)

    # ------------------------------------------------------------------
    # INSPECTION AND DEBUGGING
    # ------------------------------------------------------------------
    def show_graph_summary(self):
        logger.info("Summary of calibration graph:")
        for edge in self.graph.edges(data=True):
            logger.info(f"  {edge[0]} ↔ {edge[1]}  (bridge sensor: {edge[2]['sensor']})")

    # ------------------------------------------------------------------
    # FUNCTIONS FOR FINDING CONNECTIONS
    # ------------------------------------------------------------------
    def find_path_between_sets(self, set_a: float, set_b: float) -> List[float]:
        """
        Finds the shortest path (in number of connections) between two sets.
        """
        try:
            path = nx.shortest_path(self.graph, source=set_a, target=set_b)
            logger.info(f"Path found between {set_a} and {set_b}: {path}")
            return path
        except nx.NetworkXNoPath:
            logger.warning(f"No path exists between {set_a} and {set_b}")
            return []

    def find_sensor_set(self, sensor_id: int) -> Optional[float]:
        """
        Locates which set a sensor belongs to.
        """
        for set_num, set_obj in self.sets.items():
            constants = getattr(set_obj, "calibration_constants", None)
            if constants is not None and sensor_id in constants.index:
                return set_num
        return None

    # ------------------------------------------------------------------
    # CALCULATIONS OF OFFSETS BETWEEN SENSORS IN DIFFERENT SETS
    # ------------------------------------------------------------------
    def compute_offset_between(self, sensor_i: int, sensor_j: int) -> Tuple[float, float]:
        """
        Calculates the global offset between two sensors (i, j) which can be in different sets.
        Uses 'raised' sensors as bridges to connect both sets.
        """
        set_i = self.find_sensor_set(sensor_i)
        set_j = self.find_sensor_set(sensor_j)

        if set_i is None or set_j is None:
            raise ValueError(f"One of the sensors ({sensor_i}, {sensor_j}) was not found in any set.")

        if set_i == set_j:
            set_obj = self.sets[set_i]
            d = set_obj.calibration_constants.loc[sensor_i, sensor_j]
            e = set_obj.calibration_errors.loc[sensor_i, sensor_j]
            return d, e

        # Find path of sets
        path = self.find_path_between_sets(set_i, set_j)
        if not path:
            raise RuntimeError(f"Cannot connect {sensor_i} (Set {set_i}) with {sensor_j} (Set {set_j}).")

        total_offset = 0.0
        total_error2 = 0.0

        for a, b in zip(path[:-1], path[1:]):
            sensor_bridge = self.graph[a][b]['sensor']
            setA = self.sets[a]
            setB = self.sets[b]

            # offset A→bridge
            dA = setA.calibration_constants.loc[sensor_i, sensor_bridge] if sensor_i in setA.calibration_constants.index and sensor_bridge in setA.calibration_constants.columns else 0
            eA = setA.calibration_errors.loc[sensor_i, sensor_bridge] if sensor_i in setA.calibration_errors.index and sensor_bridge in setA.calibration_errors.columns else 0

            # offset bridge→B
            dB = setB.calibration_constants.loc[sensor_bridge, sensor_j] if sensor_j in setB.calibration_constants.columns and sensor_bridge in setB.calibration_constants.index else 0
            eB = setB.calibration_errors.loc[sensor_bridge, sensor_j] if sensor_j in setB.calibration_errors.columns and sensor_bridge in setB.calibration_errors.index else 0

            total_offset += dA + dB
            total_error2 += eA**2 + eB**2

        return total_offset, np.sqrt(total_error2)

    # ------------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------------
    def export_graph(self, filename="calibration_graph.png"):
        """
        Exports the graph as an image.
        """
        import matplotlib.pyplot as plt

        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(self.graph, seed=42)
        nx.draw(
            self.graph, pos,
            with_labels=True,
            node_color="skyblue",
            node_size=1200,
            font_size=10,
            edge_color="gray"
        )
        edge_labels = nx.get_edge_attributes(self.graph, "sensor")
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels)
        plt.title("Calibration Set Network")
        plt.tight_layout()
        plt.savefig(filename, dpi=150)
        plt.close()
        logger.info(f"Graph exported to {filename}")

            # ------------------------------------------------------------------
    # CALCULO DE OFFSET ABSOLUTO HACIA SENSOR DE REFERENCIA DEL SET 57
    # ------------------------------------------------------------------
    def compute_offset_to_top_reference(self, sensor_id: int):
        """
        Calcula el offset entre cualquier sensor (de ronda 1 o 2) y el sensor de referencia
        absoluto del set de ronda 3 (set 57). Sube el árbol acumulando offsets.
        """
        # --- 1. Definir la jerarquía ---
        round_by_set = {}
        for s, set_obj in self.sets.items():
            if hasattr(set_obj, "set_rounds") and s in set_obj.set_rounds:
                round_by_set[s] = set_obj.set_rounds[s]
            else:
                # Use configuration-based round detection
                round_by_set[s] = self._get_set_round(s)

        # --- 2. Definir sensor de referencia absoluto ---
        ref_set = 57.0
        ref_sensor = self._get_reference_sensor(ref_set)
        if ref_sensor is None:
            # Fallback to set object attributes
            ref_sensors = getattr(self.sets[ref_set], "sensors_raised_by_set", {}).get(ref_set, [])
            if not ref_sensors:
                raise RuntimeError(f"Set {ref_set} no tiene sensores raised definidos.")
            ref_sensor = ref_sensors[0]

        # Guardamos el sensor de referencia para usos futuros
        self.reference_sensor = ref_sensor
        logger.info(f"Usando sensor de referencia absoluta {ref_sensor} del set {ref_set}")

        # --- 3. Encontrar el set del sensor de entrada ---
        set_i = self.find_sensor_set(sensor_id)
        if set_i is None:
            raise ValueError(f"No se encontró el set que contiene el sensor {sensor_id}")
        if set_i == ref_set:
            return 0.0, 0.0, [{"info": "sensor ya está en el set de referencia"}]

        current_round = round_by_set.get(set_i, 1)
        current_set = set_i
        current_sensor = sensor_id
        total_offset = 0.0
        total_error2 = 0.0
        pasos = []

        # --- 4. Función auxiliar para obtener offset seguro ---
        def safe_get(df, i, j):
            try:
                return df.loc[str(i), str(j)]
            except KeyError:
                try:
                    return -df.loc[str(j), str(i)]
                except KeyError:
                    return 0.0

        # --- 5. Ir subiendo ronda a ronda hasta llegar al set 57 ---
        while current_round < 3:
            raised = getattr(self.sets[current_set], "sensors_raised_by_set", {}).get(current_set, [])
            if not raised:
                raise RuntimeError(f"Set {current_set} no tiene sensores raised definidos")

            bridge = raised[0]  # puente hacia siguiente ronda
            next_set = None

            # Buscar el set superior que contenga este bridge
            for s, obj in self.sets.items():
                if s == current_set:
                    continue
                if bridge in getattr(obj, "sensors_raised_by_set", {}).get(s, []):
                    if round_by_set.get(s, 0) == current_round + 1:
                        next_set = s
                        break

            if next_set is None:
                raise RuntimeError(f"No se encontró set de ronda superior para {current_set} (ronda {current_round})")

            df_c = getattr(self.sets[current_set], "calibration_constants", None)
            df_e = getattr(self.sets[current_set], "calibration_errors", None)
            off = safe_get(df_c, current_sensor, bridge)
            err = safe_get(df_e, current_sensor, bridge) if df_e is not None else 0.0

            pasos.append({
                "from_set": current_set,
                "to_set": next_set,
                "from_sensor": current_sensor,
                "bridge_sensor": bridge,
                "offset": float(off),
                "error": float(err),
            })

            total_offset += float(off)
            total_error2 += float(err) ** 2

            current_sensor = bridge
            current_set = next_set
            current_round += 1

        # --- 6. Último paso: dentro del set 57 ---
        df_c_ref = getattr(self.sets[ref_set], "calibration_constants", None)
        df_e_ref = getattr(self.sets[ref_set], "calibration_errors", None)
        off_final = safe_get(df_c_ref, current_sensor, ref_sensor)
        err_final = safe_get(df_e_ref, current_sensor, ref_sensor) if df_e_ref is not None else 0.0

        pasos.append({
            "from_set": ref_set,
            "from_sensor": current_sensor,
            "to_sensor": ref_sensor,
            "offset": float(off_final),
            "error": float(err_final),
        })

        total_offset += float(off_final)
        total_error2 += float(err_final) ** 2

        return total_offset, np.sqrt(total_error2), pasos
    
    # ------------------------------------------------------------------
    # RECORRIDO DE CAMINOS EN EL ÁRBOL Y PROMEDIO DE OFFSET
    # ------------------------------------------------------------------
    def compute_average_offset_to_reference(self, sensor_id: int):
        """
        Recorre todas las rutas posibles desde un sensor dado (de ronda 1 o 2)
        hasta el sensor de referencia del set 57 y devuelve:
          - offset medio acumulado
          - error medio (propagado cuadráticamente)
          - detalle de cada camino
        """
        if not hasattr(self, "reference_sensor"):
            raise RuntimeError("Primero ejecuta compute_offset_to_top_reference() para definir sensor de referencia.")

        ref_sensor = self.reference_sensor
        ref_set = 57.0

        set_i = self.find_sensor_set(sensor_id)
        if set_i is None:
            raise ValueError(f"No se encontró el set que contiene el sensor {sensor_id}")

        # --- 1. Convertimos el grafo en direccional (flechas de subida) ---
        G_up = nx.DiGraph()
        for u, v, data in self.graph.edges(data=True):
            round_u = self._get_set_round(u)
            round_v = self._get_set_round(v)
            if round_v == round_u + 1:
                G_up.add_edge(u, v, **data)  # dirección hacia arriba
            elif round_u == round_v + 1:
                G_up.add_edge(v, u, **data)

        # --- 2. Encontrar todos los caminos posibles hacia la referencia ---
        all_paths = list(nx.all_simple_paths(G_up, source=set_i, target=ref_set))
        if not all_paths:
            raise RuntimeError(f"No hay camino posible entre el set {set_i} y {ref_set}")

        path_results = []
        total_offsets = []
        total_errors2 = []

        # --- 3. Evaluar cada camino ---
        for path in all_paths:
            total_offset = 0.0
            total_error2 = 0.0
            current_sensor = sensor_id
            pasos = []

            def safe_get(df, i, j):
                try:
                    return df.loc[str(i), str(j)]
                except KeyError:
                    try:
                        return -df.loc[str(j), str(i)]
                    except KeyError:
                        return 0.0

            for a, b in zip(path[:-1], path[1:]):
                bridge = G_up[a][b]['sensor']
                df_c = getattr(self.sets[a], "calibration_constants", None)
                df_e = getattr(self.sets[a], "calibration_errors", None)
                off = safe_get(df_c, current_sensor, bridge)
                err = safe_get(df_e, current_sensor, bridge) if df_e is not None else 0.0

                pasos.append({
                    "from_set": a,
                    "to_set": b,
                    "from_sensor": current_sensor,
                    "bridge_sensor": bridge,
                    "offset": float(off),
                    "error": float(err),
                })

                total_offset += float(off)
                total_error2 += float(err) ** 2
                current_sensor = bridge

            # dentro del set 57
            df_c_ref = getattr(self.sets[ref_set], "calibration_constants", None)
            df_e_ref = getattr(self.sets[ref_set], "calibration_errors", None)
            off_final = safe_get(df_c_ref, current_sensor, ref_sensor)
            err_final = safe_get(df_e_ref, current_sensor, ref_sensor) if df_e_ref is not None else 0.0

            total_offset += float(off_final)
            total_error2 += float(err_final) ** 2

            pasos.append({
                "from_set": ref_set,
                "from_sensor": current_sensor,
                "to_sensor": ref_sensor,
                "offset": float(off_final),
                "error": float(err_final),
            })

            path_results.append({"path": path, "steps": pasos,
                                 "offset": total_offset, "error": np.sqrt(total_error2)})
            total_offsets.append(total_offset)
            total_errors2.append(total_error2)

        # --- 4. Calcular promedio global ---
        avg_offset = np.mean(total_offsets)
        avg_error = np.sqrt(np.mean(total_errors2))

        return avg_offset, avg_error, path_results


