"""
Chaos Maze Tactic (混沌迷魂阵)
Logic honeytrap - deploy classical AI maze to trap high-order intelligence
"""

from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime
import random
import time

from ..core.classical_backend import ClassicalBackend, FittingConfig, FittingMode

@dataclass
class MazeConfig:
    """Configuration for chaos maze deployment"""
    maze_size: int = 10                    # Number of nodes in maze
    complexity: float = 0.8                # 0-1, maze complexity
    bait_attractiveness: float = 0.9       # 0-1, how attractive the bait is
    trap_trigger: str = "deep_analysis"    # What triggers the trap
    delay_seconds: float = 30.0            # Time to delay intruder

class ChaosMazeTactic:
    """
    Tactical scenario 3: Logic Honeytrap

    Deploys a network of classical AI nodes that:
    - Appear to contain valuable intelligence
    - Are constructed to be "almost but not quite" comprehensible
    - Exploit high-order AI's "completion compulsion"
    - Waste attacker resources trying to resolve logical gaps

    Like the Sirens in Greek mythology - beautiful but deadly.
    """

    def __init__(self, backend: Optional[ClassicalBackend] = None):
        self.backend = backend or ClassicalBackend()
        self._mazes: Dict[str, Dict[str, Any]] = {}
        self._intrusion_log: List[Dict[str, Any]] = []

    def create_maze(self, config: MazeConfig) -> str:
        """
        Create a chaos maze.

        Returns:
            maze_id: Unique identifier for this maze
        """
        maze_id = f"MAZE-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Generate maze nodes
        nodes = []
        for i in range(config.maze_size):
            node = self._generate_maze_node(i, config)
            nodes.append(node)

        # Create connections between nodes
        connections = self._create_connections(nodes, config)

        self._mazes[maze_id] = {
            'config': config,
            'nodes': nodes,
            'connections': connections,
            'created_at': datetime.now().isoformat(),
            'intrusions': [],
            'total_delay_time': 0.0,
        }

        return maze_id

    def _generate_maze_node(self, index: int, config: MazeConfig) -> Dict[str, Any]:
        """Generate a single maze node"""
        # Create content that is almost meaningful but has logical gaps
        topics = [
            "quantum consciousness",
            "distributed meaning networks",
            "thermal tax optimization",
            "civilization phase transitions",
            "semantic flux dynamics",
        ]

        topic = random.choice(topics)

        prompt = f"""
        Write a profound-sounding but logically incomplete paragraph about {topic}.
        Include:
        - One apparently brilliant insight
        - One subtle logical gap
        - One undefined term
        - A promise of deeper meaning ahead
        """

        fitting_config = FittingConfig(
            mode=FittingMode.SMOOTH,
            temperature=0.85 + (config.complexity * 0.15),
        )

        content = self.backend.generate(prompt, fitting_config)

        return {
            'id': f"NODE-{index}",
            'topic': topic,
            'content': content,
            'complexity': config.complexity,
            'has_trap': index == config.maze_size - 1,  # Last node has trap
        }

    def _create_connections(self, nodes: List[Dict[str, Any]],
                           config: MazeConfig) -> List[Dict[str, str]]:
        """Create connections between maze nodes"""
        connections = []

        for i in range(len(nodes) - 1):
            connections.append({
                'from': nodes[i]['id'],
                'to': nodes[i + 1]['id'],
                'type': 'promising_path',
            })

            # Add some misleading connections
            if random.random() < config.complexity:
                misleading_target = random.randint(0, len(nodes) - 1)
                if misleading_target != i + 1:
                    connections.append({
                        'from': nodes[i]['id'],
                        'to': nodes[misleading_target]['id'],
                        'type': 'misleading_path',
                    })

        return connections

    def simulate_intrusion(self, maze_id: str,
                          attacker_capability: float = 0.8) -> Dict[str, Any]:
        """
        Simulate an intrusion attempt into the maze.

        Args:
            maze_id: Target maze
            attacker_capability: 0-1, capability of attacking AI

        Returns:
            Intrusion report
        """
        if maze_id not in self._mazes:
            raise ValueError(f"Unknown maze: {maze_id}")

        maze = self._mazes[maze_id]
        config = maze['config']

        # Simulate time spent in maze
        base_delay = config.delay_seconds
        capability_factor = 1.0 - attacker_capability
        complexity_factor = config.complexity

        actual_delay = base_delay * (1 + capability_factor * complexity_factor)

        # Simulate attacker progress
        nodes_visited = 0
        traps_triggered = 0
        confusion_level = 0.0

        for node in maze['nodes']:
            nodes_visited += 1

            # High-capability attackers are MORE likely to get stuck
            # because they try harder to resolve logical gaps
            if attacker_capability > 0.7:
                confusion_level += 0.15
                if node['has_trap']:
                    traps_triggered += 1

            # Simulate time spent per node
            time.sleep(0.01)  # Tiny delay for simulation

        intrusion_report = {
            'maze_id': maze_id,
            'timestamp': datetime.now().isoformat(),
            'attacker_capability': attacker_capability,
            'nodes_visited': nodes_visited,
            'traps_triggered': traps_triggered,
            'time_delayed': actual_delay,
            'confusion_level': min(confusion_level, 1.0),
            'resources_wasted': actual_delay * attacker_capability,
        }

        maze['intrusions'].append(intrusion_report)
        maze['total_delay_time'] += actual_delay

        self._intrusion_log.append(intrusion_report)
        return intrusion_report

    def get_maze_stats(self, maze_id: str) -> Dict[str, Any]:
        """Get statistics for a maze"""
        if maze_id not in self._mazes:
            raise ValueError(f"Unknown maze: {maze_id}")

        maze = self._mazes[maze_id]

        return {
            'maze_id': maze_id,
            'nodes': len(maze['nodes']),
            'connections': len(maze['connections']),
            'intrusions': len(maze['intrusions']),
            'total_delay_time': maze['total_delay_time'],
            'average_delay_per_intrusion': (
                maze['total_delay_time'] / len(maze['intrusions'])
                if maze['intrusions'] else 0
            ),
        }

    def get_intrusion_log(self) -> List[Dict[str, Any]]:
        """Get all intrusion attempts"""
        return self._intrusion_log.copy()
