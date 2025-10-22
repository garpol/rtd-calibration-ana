import pandas as pd
import numpy as np
import logging
import yaml
from typing import Dict, Tuple, List, Optional

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

    def __init__(self, sets_dict: Dict[float, object], config_path: Optional[str] = None):
        """
        Args:
            sets_dict (dict): Dictionary {CalibSetNumber: SetObject}.
                              Each SetObject must have:
                                  - calibration_constants (DataFrame)
                                  - calibration_errors (DataFrame)
            config_path (str): Path to the YAML file with tree definition
                               (relationships between sets, raised sensors, etc.)
        """
        self.sets = sets_dict
        self.graph = nx.Graph()
        self.config = None

        if config_path:
            with open(config_path, "r") as f:
                self.config = yaml.safe_load(f)
            self._build_graph_from_config()

    # ------------------------------------------------------------------
    # BUILDING THE CONNECTION GRAPH BETWEEN SETS
    # ------------------------------------------------------------------
    def _build_graph_from_config(self):
        """
        Builds the connection graph between sets using the YAML configuration.
        Each node is a CalibSetNumber.
        Each edge connects two consecutive sets through one or more 'raised' sensors.
        """
        logger.info("Building calibration graph from configuration...")

        sensors_data = self.config.get("sensors", {}).get("sets", {})
        for set_id_str, data in sensors_data.items():
            try:
                set_id = float(set_id_str)
            except ValueError:
                continue

            round_id = data.get("round", 1)
            raised_sensors = data.get("raised", [])

            # Search for sets in the next level that contain any of these sensors
            for other_id_str, other_data in sensors_data.items():
                other_id = float(other_id_str)
                if other_data.get("round", 1) != round_id + 1:
                    continue

                bridge_sensors = [
                    s for s in raised_sensors
                    if s in other_data.get("raised", []) or s in other_data.get("discarded", [])
                ]

                if bridge_sensors:
                    for sensor in bridge_sensors:
                        self.graph.add_edge(set_id, other_id, sensor=sensor)

        logger.info(f"Graph built with {len(self.graph.nodes)} sets and {len(self.graph.edges)} connections.")

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
                # fallback: deducir por número
                if 3 <= s <= 39:
                    round_by_set[s] = 1
                elif 49 <= s <= 54:
                    round_by_set[s] = 2
                elif s == 57:
                    round_by_set[s] = 3

        # --- 2. Definir sensor de referencia absoluto ---
        ref_set = 57.0
        ref_sensors = getattr(self.sets[ref_set], "sensors_raised_by_set", {}).get(ref_set, [])
        if not ref_sensors:
            raise RuntimeError(f"Set 57 no tiene sensores raised definidos.")
        ref_sensor = ref_sensors[0]  # elegimos el primero como referencia absoluta

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
            round_u = 1 if 3 <= u <= 39 else (2 if 49 <= u <= 54 else 3)
            round_v = 1 if 3 <= v <= 39 else (2 if 49 <= v <= 54 else 3)
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


