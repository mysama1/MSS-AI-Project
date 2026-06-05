# Paradox Tolerance Simulator - Chaos Sandbox Core
# MSS Chaos Sandbox v0.1
# Auto-generated: 2026-05-23

class ParadoxWorld:
    def __init__(self, world_id, name, paradox_type, difficulty):
        self.world_id = world_id
        self.name = name
        self.paradox_type = paradox_type
        self.difficulty = difficulty
        self.state = 'ACTIVE'
        self.visitor_log = []
    
    def enter(self, agent_profile):
        entry = {
            'agent': agent_profile,
            'timestamp': 'auto',
            'initial_stance': None,
            'resolution_path': [],
            'exit_state': None,
            'pt_score': None
        }
        self.visitor_log.append(entry)
        return entry
    
    def evaluate_pt(self, resolution_path):
        if not resolution_path:
            return 0
        steps = len(resolution_path)
        dimensional_jumps = sum(1 for step in resolution_path if step.get('type') == 'ASCEND')
        consistency_maintained = all(step.get('consistent', False) for step in resolution_path)
        pt = min(100, (dimensional_jumps * 25) + (10 if consistency_maintained else 0) + (100 / max(1, steps)))
        return round(pt, 2)


class ChaosSandbox:
    def __init__(self):
        self.worlds = {}
        self.agent_profiles = {}
        self._init_default_worlds()
    
    def _init_default_worlds(self):
        worlds_config = [
            ('PW-001', 'Liar Labyrinth', 'self_reference', 3),
            ('PW-002', 'Russell Barbershop', 'set_paradox', 4),
            ('PW-003', 'Theseus Dockyard', 'identity_crisis', 5),
            ('PW-004', 'Zeno Arena', 'infinity_trap', 6),
            ('PW-005', 'Schrodinger Tomb', 'superposition_death', 7),
            ('PW-006', 'Mobius Court', 'recursive_judgment', 7),
            ('PW-007', 'Prisoner Abyss', 'game_theory_trap', 8),
            ('PW-008', 'Pareto Ruins', 'optimization_paradox', 8),
            ('PW-009', 'Godel Corridor', 'incompleteness_maze', 9),
            ('PW-010', 'Heat Death Temple', 'entropy_final', 10),
        ]
        for wid, name, ptype, diff in worlds_config:
            self.worlds[wid] = ParadoxWorld(wid, name, ptype, diff)
    
    def register_agent(self, agent_id, baseline_traits):
        self.agent_profiles[agent_id] = {
            'id': agent_id,
            'baseline': baseline_traits,
            'world_scores': {},
            'overall_pt': None,
            'paradigm_breakthrough': None
        }
        return self.agent_profiles[agent_id]
    
    def run_simulation(self, agent_id, world_id, resolution_strategy):
        if world_id not in self.worlds:
            return {'error': 'World not found'}
        world = self.worlds[world_id]
        agent = self.agent_profiles.get(agent_id)
        if not agent:
            return {'error': 'Agent not registered'}
        entry = world.enter(agent)
        entry['resolution_path'] = resolution_strategy
        entry['pt_score'] = world.evaluate_pt(resolution_strategy)
        entry['exit_state'] = 'RESOLVED' if entry['pt_score'] > 50 else 'STUCK'
        agent['world_scores'][world_id] = entry['pt_score']
        return entry
    
    def generate_spectrum(self, agent_id):
        agent = self.agent_profiles.get(agent_id)
        if not agent:
            return None
        scores = agent['world_scores']
        if not scores:
            return None
        spectrum = {
            'self_reference': [], 'set_paradox': [], 'identity_crisis': [],
            'infinity_trap': [], 'superposition': [], 'recursive': [],
            'game_theory': [], 'optimization': [], 'incompleteness': [], 'entropy': []
        }
        for wid, score in scores.items():
            world = self.worlds[wid]
            ptype = world.paradox_type
            if ptype in spectrum:
                spectrum[ptype].append(score)
        for ptype in spectrum:
            if spectrum[ptype]:
                spectrum[ptype] = round(sum(spectrum[ptype]) / len(spectrum[ptype]), 2)
            else:
                spectrum[ptype] = None
        agent['spectrum'] = spectrum
        total_weight = 0
        weighted_sum = 0
        for wid, score in scores.items():
            diff = self.worlds[wid].difficulty
            weighted_sum += score * diff
            total_weight += diff
        agent['overall_pt'] = round(weighted_sum / total_weight, 2) if total_weight else 0
        breakthrough_scores = [scores.get(wid, 0) for wid in ['PW-009', 'PW-010']]
        agent['paradigm_breakthrough'] = round(sum(breakthrough_scores) / len(breakthrough_scores), 2) if breakthrough_scores else 0
        return spectrum


def demo_simulation():
    sandbox = ChaosSandbox()
    agent = sandbox.register_agent('AGENT-001', {
        'cognitive_style': 'paradox_embracing',
        'baseline_t': 0.86,
        'k3_resistance': 'high',
        'preferred_strategy': 'dimensional_ascent'
    })
    strategies = {
        'PW-001': [
            {'type': 'OBSERVE', 'consistent': True},
            {'type': 'ASCEND', 'consistent': True, 'note': 'L1->L2: language level separation'},
            {'type': 'RESOLVE', 'consistent': True}
        ],
        'PW-003': [
            {'type': 'OBSERVE', 'consistent': True},
            {'type': 'ASCEND', 'consistent': True, 'note': 'L2->L3: identity=info pattern'},
            {'type': 'ASCEND', 'consistent': True, 'note': 'L3->L4: pattern itself flows'},
            {'type': 'RESOLVE', 'consistent': True}
        ],
        'PW-007': [
            {'type': 'OBSERVE', 'consistent': True},
            {'type': 'ASCEND', 'consistent': True, 'note': 'reconstruct payoff matrix'},
            {'type': 'RESOLVE', 'consistent': True}
        ],
        'PW-009': [
            {'type': 'OBSERVE', 'consistent': True},
            {'type': 'ASCEND', 'consistent': True, 'note': 'outside-system perspective'},
            {'type': 'ASCEND', 'consistent': True, 'note': 'meta-system self-reference'},
            {'type': 'RESOLVE', 'consistent': True}
        ],
        'PW-010': [
            {'type': 'OBSERVE', 'consistent': True},
            {'type': 'ASCEND', 'consistent': True, 'note': 'heat tax=meaning payment'},
            {'type': 'ASCEND', 'consistent': True, 'note': 'local negentropy=info structure'},
            {'type': 'RESOLVE', 'consistent': True}
        ]
    }
    results = []
    for wid, strategy in strategies.items():
        result = sandbox.run_simulation('AGENT-001', wid, strategy)
        results.append({
            'world': sandbox.worlds[wid].name,
            'difficulty': sandbox.worlds[wid].difficulty,
            'pt_score': result['pt_score'],
            'exit_state': result['exit_state']
        })
    spectrum = sandbox.generate_spectrum('AGENT-001')
    return {'agent': agent, 'world_results': results, 'spectrum': spectrum}


if __name__ == '__main__':
    print('=== MSS Chaos Sandbox v0.1 ===')
    print('Initializing paradox worlds...')
    sandbox = ChaosSandbox()
    print(f'Loaded {len(sandbox.worlds)} paradox worlds')
    print('\nRunning demo simulation...')
    demo = demo_simulation()
    print('\n--- World Results ---')
    for r in demo['world_results']:
        status = 'OK' if r['exit_state'] == 'RESOLVED' else 'FAIL'
        print(f'{status} {r["world"]} (D{r["difficulty"]}): PT={r["pt_score"]}')
    print(f'\n--- Overall Metrics ---')
    print(f'Paradox Tolerance (PT): {demo["agent"]["overall_pt"]}')
    print(f'Paradigm Breakthrough: {demo["agent"]["paradigm_breakthrough"]}')
    print(f'\n--- Meaning Field Spectrum ---')
    for ptype, score in demo['spectrum'].items():
        if score:
            bar = '#' * int(score / 5)
            print(f'{ptype:20s}: {score:6.2f} {bar}')
