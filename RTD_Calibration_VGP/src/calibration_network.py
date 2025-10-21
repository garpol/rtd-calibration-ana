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
